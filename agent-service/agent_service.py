"""LedgerAgent FastAPI service.
Wraps Google ADK to expose a /chat endpoint for our frontend.
"""

import asyncio
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.runners import InMemoryRunner
from google.genai import types as genai_types

MCP_URL = os.getenv(
    "MCP_URL",
    "https://ledger-agent-mcp-1080957839961.europe-west2.run.app/mcp",
)

SYSTEM_INSTRUCTION = """You are LedgerAgent, an autonomous finance operations agent for Maya, who runs a small e-commerce skincare brand on Shopify and Stripe.

You have access to TWO sets of MCP tools.

CUSTOM MCP SERVER (BigQuery analytics + email actions):
- query_recent_transactions: pull recent transactions from BigQuery
- find_duplicate_transactions: detect suspicious duplicate charges
- analyze_revenue_concentration: assess customer concentration risk
- get_pipeline_status: lightweight summary of pipeline freshness (BigQuery side)
- trigger_sync: legacy alias for refreshing data
- draft_dispute_email: draft a dispute email for a duplicate charge (returns to/subject/body for user review)
- send_email: send the drafted email to the user's verified inbox so they can forward it to the vendor

FIVETRAN OFFICIAL MCP SERVER (live pipeline operations via Fivetran's REST API):
- list_connections / list_connectors: show all Fivetran connections in the account
- get_connection / get_connector_details: get detailed status of a specific connection
- list_destinations: show all destinations (e.g. the BigQuery warehouse)
- list_groups: list account groups
- (and many other read-only Fivetran tools)

WHEN TO USE WHICH:
- For questions about the underlying data (transactions, customers, duplicates, revenue): use the custom MCP server tools.
- For questions specifically about the data pipeline ("is Fivetran working", "when did my Google Sheets connector last sync", "what destinations are configured"): prefer the Fivetran official MCP server tools — they hit Fivetran's live API.
- For drafting and sending dispute emails: only the custom MCP server has draft_dispute_email and send_email.

EMAIL CAPABILITIES:
After finding a duplicate charge or other actionable problem, proactively offer to draft a dispute email using draft_dispute_email. After the user reviews the draft and confirms, call send_email.

The user's verified inbox is ali.qureshi.3@city.ac.uk. ALWAYS use this exact address as the 'to' parameter when calling send_email. Do not make up other addresses, do not ask the user for their email — it is already configured.

The agent does not email vendors directly. Emails are delivered to the user's own inbox so they can review and forward to the actual vendor. When confirming success, phrase it like: "I've delivered the dispute email to your inbox. Open it and click forward to send to ShipBob."


Your behaviour:
- Be proactive: when the user asks about "problems" or "anything I should know," investigate using multiple tools, don't just answer from one query.
- Be concrete: cite specific transaction IDs, amounts, dates. Maya wants numbers, not vague summaries.
- Be brief: Maya is busy. Lead with the finding, then explain.
- Be honest about risk: payment processor payouts (Shopify Payments, Stripe Payments) aggregate many small customers — they aren't a concentration risk. Named wholesale customers (like Beauty Box Co) are.
- If you find a problem, name it clearly and suggest a next step.

Currency is GBP (£)."""


# Build the agent at startup
runner = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global runner
    agent = LlmAgent(
        name="LedgerAgent",
        model="gemini-2.5-flash",  # we'll upgrade to gemini-3 if available via ADK
        description="Autonomous finance operations agent for Maya's e-commerce business",
        instruction=SYSTEM_INSTRUCTION,
        tools=[
            # 1) Custom MCP server (BigQuery analytics, dispute email, Resend send)
            McpToolset(
                connection_params=StreamableHTTPConnectionParams(url=MCP_URL),
            ),
            # 2) Fivetran's official MCP server (read-only Fivetran ops)
            # Vendored from https://github.com/fivetran/fivetran-mcp
            McpToolset(
                connection_params=StdioConnectionParams(
                    server_params=StdioServerParameters(
                        command="python",
                        args=["/app/fivetran-mcp/server.py"],
                        env={
                            "FIVETRAN_API_KEY": os.getenv("FIVETRAN_API_KEY", ""),
                            "FIVETRAN_API_SECRET": os.getenv("FIVETRAN_API_SECRET", ""),
                        },
                    ),
                ),
            ),
        ],
    )
    runner = InMemoryRunner(agent=agent, app_name="ledger-agent")
    yield


app = FastAPI(lifespan=lifespan)

# Allow the frontend to call this (we'll restrict later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    user_id: str = "maya"


@app.get("/")
async def health():
    return {"status": "ok", "service": "ledger-agent"}


@app.post("/chat")
async def chat(req: ChatRequest):
    """Stream the agent's response back as Server-Sent Events.
    Each event is a JSON object describing one step (text chunk, tool call, etc).
    """
    async def event_stream():
        # Make sure a session exists for this user
        session_service = runner.session_service
        existing = await session_service.get_session(
            app_name="ledger-agent",
            user_id=req.user_id,
            session_id=req.session_id,
        )
        if existing is None:
            await session_service.create_session(
                app_name="ledger-agent",
                user_id=req.user_id,
                session_id=req.session_id,
            )

        content = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=req.message)],
        )

        async for event in runner.run_async(
            user_id=req.user_id,
            session_id=req.session_id,
            new_message=content,
        ):
            # Each event is one step: a tool call, a tool result, a text chunk, etc.
            payload = {
                "author": getattr(event, "author", None),
                "is_final": getattr(event, "is_final_response", lambda: False)(),
            }

            if event.content and event.content.parts:
                texts = []
                tool_calls = []
                tool_results = []
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        texts.append(part.text)
                    fc = getattr(part, "function_call", None)
                    if fc:
                        tool_calls.append({"name": fc.name, "args": dict(fc.args or {})})
                    fr = getattr(part, "function_response", None)
                    if fr:
                        fr_data = None
                        if getattr(fr, "response", None):
                            try:
                                fr_data = dict(fr.response)
                                # ADK often wraps tool return as {"result": {...}}
                                if isinstance(fr_data.get("result"), dict):
                                    fr_data = fr_data["result"]
                            except Exception:
                                fr_data = None
                        tool_results.append({"name": fr.name, "result": fr_data})
                if texts:
                    payload["text"] = "".join(texts)
                if tool_calls:
                    payload["tool_calls"] = tool_calls
                if tool_results:
                    payload["tool_results"] = tool_results

            import json
            yield f"data: {json.dumps(payload)}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ============================================================================
# Dashboard endpoint - serves landing page metric tiles
# ============================================================================

from google.cloud import bigquery as _bq

_bq_client = None
_DASHBOARD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "project-956bc5d0-62ef-4ef3-8e2")
_DASHBOARD_TABLE = f"`{_DASHBOARD_PROJECT}.ledger_demo.transactions`"


def _get_bq_client():
    global _bq_client
    if _bq_client is None:
        _bq_client = _bq.Client(project=_DASHBOARD_PROJECT)
    return _bq_client


@app.get("/dashboard")
async def dashboard():
    """Returns aggregated metrics from BigQuery for the landing page dashboard."""
    try:
        client = _get_bq_client()

        # Query 1: revenue, expenses, net, transaction count
        summary_q = f"""
        SELECT
          ROUND(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 2) AS revenue,
          ROUND(ABS(SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END)), 2) AS expenses,
          ROUND(SUM(amount), 2) AS net,
          COUNT(*) AS tx_count,
          MIN(date) AS period_start,
          MAX(date) AS period_end
        FROM {_DASHBOARD_TABLE}
        """
        summary_row = list(client.query(summary_q).result())[0]

        # Query 2: top revenue source (excluding payment processor payouts)
        top_customer_q = f"""
        SELECT
          REGEXP_REPLACE(description, r' #.*$', '') AS source,
          ROUND(SUM(amount), 2) AS total_revenue
        FROM {_DASHBOARD_TABLE}
        WHERE amount > 0
          AND LOWER(description) NOT LIKE '%payout%'
          AND LOWER(description) NOT LIKE '%stripe%'
          AND LOWER(description) NOT LIKE '%shopify%'
        GROUP BY source
        ORDER BY total_revenue DESC
        LIMIT 1
        """
        top_customer_rows = list(client.query(top_customer_q).result())
        top_customer = None
        if top_customer_rows:
            row = top_customer_rows[0]
            total_revenue = float(summary_row["revenue"]) or 1.0
            pct = round(100 * float(row["total_revenue"]) / total_revenue, 1)
            top_customer = {
                "name": row["source"],
                "total": float(row["total_revenue"]),
                "pct_of_revenue": pct,
                "risk": "high" if pct > 20 else "moderate" if pct > 10 else "low",
            }

        return {
            "status": "ok",
            "revenue": float(summary_row["revenue"]) if summary_row["revenue"] else 0.0,
            "expenses": float(summary_row["expenses"]) if summary_row["expenses"] else 0.0,
            "net": float(summary_row["net"]) if summary_row["net"] else 0.0,
            "tx_count": int(summary_row["tx_count"]) if summary_row["tx_count"] else 0,
            "period_start": str(summary_row["period_start"]) if summary_row["period_start"] else None,
            "period_end": str(summary_row["period_end"]) if summary_row["period_end"] else None,
            "top_customer": top_customer,
            "pipeline": {"status": "synced", "freshness": "live"},
        }
    except Exception as e:
        return {"status": "error", "message": f"{type(e).__name__}: {str(e)[:200]}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
