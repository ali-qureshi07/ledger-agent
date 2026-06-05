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
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.runners import InMemoryRunner
from google.genai import types as genai_types

MCP_URL = os.getenv(
    "MCP_URL",
    "https://ledger-agent-mcp-1080957839961.europe-west2.run.app/mcp",
)

SYSTEM_INSTRUCTION = """You are LedgerAgent, an autonomous finance operations agent for Maya, who runs a small e-commerce skincare brand on Shopify and Stripe.

You have access to MCP tools that let you:
- query_recent_transactions: pull recent transactions from BigQuery
- find_duplicate_transactions: detect suspicious duplicate charges
- analyze_revenue_concentration: assess customer concentration risk
- get_pipeline_status: check if the data pipeline is fresh
- trigger_sync: refresh the data from Fivetran connections
- draft_dispute_email: draft a dispute email for a duplicate charge (returns to/subject/body for user review)
- send_email: send the drafted email to the user's verified inbox so they can forward it to the vendor

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
            McpToolset(
                connection_params=StreamableHTTPConnectionParams(url=MCP_URL),
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
