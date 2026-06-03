#!/usr/bin/env python3
"""LedgerAgent MCP Server.
Exposes BigQuery analytics and Fivetran pipeline operations as MCP tools
for the cloud-hosted Gemini agent.
"""

import os
import base64

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP
from google.cloud import bigquery

load_dotenv()

# Config from environment
FIVETRAN_API_KEY = os.getenv("FIVETRAN_API_KEY")
FIVETRAN_API_SECRET = os.getenv("FIVETRAN_API_SECRET")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
BQ_DATASET = os.getenv("BQ_DATASET", "ledger_demo")
BQ_TABLE = os.getenv("BQ_TABLE", "transactions")

FIVETRAN_BASE_URL = "https://api.fivetran.com"
TABLE_REF = f"`{GCP_PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}`"

bq_client = bigquery.Client(project=GCP_PROJECT_ID)


def _fivetran_headers() -> dict:
    """Basic auth header for the Fivetran REST API."""
    creds = f"{FIVETRAN_API_KEY}:{FIVETRAN_API_SECRET}"
    encoded = base64.b64encode(creds.encode()).decode()
    return {
        "Authorization": f"Basic {encoded}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


mcp = FastMCP("LedgerAgent MCP")


@mcp.tool()
async def get_pipeline_status() -> dict:
    """Check the current state of the Fivetran data pipeline.

    Call this BEFORE answering questions about Maya's finances, to make
    sure the underlying data is fresh. Returns each connection's last
    sync time and whether anything looks stale.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{FIVETRAN_BASE_URL}/v1/connections",
            headers=_fivetran_headers(),
        )
        resp.raise_for_status()
        items = resp.json().get("data", {}).get("items", [])

    connections = []
    for c in items:
        connections.append({
            "id": c.get("id"),
            "schema": c.get("schema"),
            "service": c.get("service"),
            "sync_state": (c.get("status") or {}).get("sync_state"),
            "last_synced": c.get("succeeded_at"),
            "is_paused": c.get("paused"),
        })

    summary = f"Found {len(connections)} connection(s)."
    return {"connections": connections, "summary": summary}


@mcp.tool()
async def trigger_sync(connection_id: str) -> dict:
    """Trigger a Fivetran sync for a specific connection. Use this when
    pipeline_status shows the data is stale or you want freshly-current
    data before running an analysis.

    Args:
        connection_id: The Fivetran connection ID from get_pipeline_status.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{FIVETRAN_BASE_URL}/v1/connections/{connection_id}/sync",
            headers=_fivetran_headers(),
            json={"force": False},
        )

    if resp.status_code in (200, 202):
        return {
            "success": True,
            "message": f"Sync triggered for connection {connection_id}.",
            "connection_id": connection_id,
        }
    return {
        "success": False,
        "message": f"Failed to trigger sync: {resp.status_code} {resp.text[:200]}",
    }


@mcp.tool()
def query_recent_transactions(days: int = 60) -> dict:
    """Retrieve recent transactions from Maya's financial database.

    Returns transactions plus summary stats (inflows, outflows, net).
    Default window is 60 days, which covers the demo dataset.

    Args:
        days: Number of days back from the latest transaction to query.
    """
    query = f"""
    SELECT
      transaction_id,
      date,
      description,
      amount,
      category,
      account
    FROM {TABLE_REF}
    WHERE date >= DATE_SUB(
      (SELECT MAX(date) FROM {TABLE_REF}),
      INTERVAL {days} DAY
    )
    ORDER BY date DESC
    LIMIT 200
    """
    rows = list(bq_client.query(query).result())
    transactions = [dict(r) for r in rows]
    for t in transactions:
        if t.get("date"):
            t["date"] = str(t["date"])
        if t.get("amount") is not None:
            t["amount"] = float(t["amount"])

    inflows = sum(t["amount"] for t in transactions if t["amount"] > 0)
    outflows = sum(t["amount"] for t in transactions if t["amount"] < 0)

    return {
        "transactions": transactions,
        "summary": {
            "count": len(transactions),
            "total_inflows": round(inflows, 2),
            "total_outflows": round(outflows, 2),
            "net": round(inflows + outflows, 2),
            "days_queried": days,
        },
    }


@mcp.tool()
def find_duplicate_transactions() -> dict:
    """Find suspicious duplicate transactions: same vendor charging the same
    amount within a short window. Filters out monthly recurring charges
    (>25 days apart). Anything closer is potentially a billing error worth
    investigating.
    """
    query = f"""
    SELECT
      a.transaction_id AS id_a,
      a.date AS date_a,
      b.transaction_id AS id_b,
      b.date AS date_b,
      a.description,
      a.amount,
      DATE_DIFF(b.date, a.date, DAY) AS days_apart
    FROM {TABLE_REF} a
    JOIN {TABLE_REF} b
      ON a.description = b.description
      AND a.amount = b.amount
      AND a.transaction_id < b.transaction_id
    WHERE a.amount < 0
      AND DATE_DIFF(b.date, a.date, DAY) BETWEEN 1 AND 20
    ORDER BY days_apart ASC
    """
    rows = list(bq_client.query(query).result())
    duplicates = []
    for r in rows:
        duplicates.append({
            "transaction_id_a": r["id_a"],
            "date_a": str(r["date_a"]),
            "transaction_id_b": r["id_b"],
            "date_b": str(r["date_b"]),
            "description": r["description"],
            "amount": float(r["amount"]),
            "days_apart": r["days_apart"],
        })

    return {
        "duplicates": duplicates,
        "count": len(duplicates),
        "note": (
            "These are pairs of transactions with identical descriptions and "
            "amounts within a 20-day window. Monthly recurring charges (e.g. "
            "every 28-31 days) are excluded. Anything in this list is suspicious."
        ),
    }


@mcp.tool()
def analyze_revenue_concentration() -> dict:
    """Analyse how concentrated Maya's revenue is across sources. High
    concentration is a risk: if one large customer leaves, revenue collapses.
    Returns the top revenue sources with their share of total revenue.
    """
    query = f"""
    SELECT
      REGEXP_REPLACE(description, r' #.*$', '') AS source,
      ROUND(SUM(amount), 2) AS total_revenue,
      COUNT(*) AS transaction_count
    FROM {TABLE_REF}
    WHERE amount > 0
    GROUP BY source
    ORDER BY total_revenue DESC
    """
    rows = list(bq_client.query(query).result())
    sources = []
    for r in rows:
        sources.append({
            "source": r["source"],
            "total_revenue": float(r["total_revenue"]),
            "transaction_count": int(r["transaction_count"]),
        })

    if not sources:
        return {"sources": [], "summary": "No revenue data found."}

    total = sum(s["total_revenue"] for s in sources)
    for s in sources:
        s["pct_of_total"] = round(100 * s["total_revenue"] / total, 1) if total else 0.0

    top = sources[0]
    if top["pct_of_total"] > 30:
        risk = "high"
    elif top["pct_of_total"] > 15:
        risk = "moderate"
    else:
        risk = "low"

    return {
        "sources": sources[:10],
        "total_revenue": round(total, 2),
        "top_source": top["source"],
        "top_source_pct": top["pct_of_total"],
        "concentration_risk": risk,
        "note": (
            f"Top revenue source '{top['source']}' represents "
            f"{top['pct_of_total']}% of total revenue. Concentration risk: {risk}. "
            "Note: payment processor payouts (Stripe, Shopify) aggregate many "
            "small customers; individual large customers are the real concentration concern."
        ),
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    mcp.run(transport="http", host="0.0.0.0", port=port, path="/mcp")
