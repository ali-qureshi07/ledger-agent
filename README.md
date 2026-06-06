# LedgerAgent

> Autonomous finance operations agent for small e-commerce businesses. Catches the problems your bookkeeper misses.

![Status](https://img.shields.io/badge/status-live-success)
![License](https://img.shields.io/badge/license-MIT-blue)
![Hackathon](https://img.shields.io/badge/Google_Cloud_Rapid_Agent_Hackathon-2026-4285F4)

**Live demo →** [ledger-agent-five.vercel.app](https://ledger-agent-five.vercel.app)

LedgerAgent system architecture <img width="1472" height="692" alt="image" src="https://github.com/user-attachments/assets/c5202689-aefc-4a51-a379-d4d5959500c3" />


## The Problem

Small e-commerce founders run their financial life across Shopify, Stripe, banks, and a spreadsheet that is always three weeks out of date. Bookkeepers help, but they miss things. Duplicate vendor charges, customer concentration risk, silent subscription creep. Patterns that take vigilance to catch, not just categorisation.

These missable problems cost real money. A duplicate £892 ShipBob charge billed for three months is £2,676 quietly gone. A wholesale customer that grew to 22% of revenue is a runway-killer hiding in the data.

A bookkeeper costs around £40,000 a year. A part-time CFO is £80,000+. Most small businesses can afford neither.

## The Solution

LedgerAgent watches a business financial data and surfaces issues before they compound. Think of it as the vigilant CFO they can not afford, running for £40 a month instead of £80,000 a year.

Ask it "are there any problems in my finances I should know about?" and it does not just answer. It plans a multi-step investigation, queries the data, runs analyses on the results, and tells you what it found, with numbers and a suggested action.

It does not stop at finding problems. Ask it to draft a dispute email and it produces one. Tell it to send, and a real email lands in your inbox through Resend, ready to forward to the vendor.

## How It Works

- **Fivetran** moves data from every source the business uses into a single warehouse on a scheduled sync.
- **BigQuery** stores the unified financial picture (currently `ledger_demo.transactions`).
- **A custom MCP server** exposes seven tools to the agent: query, duplicate detection, concentration analysis, pipeline status, sync triggering, email drafting, and email sending. Two of those are write operations. Deployed on Cloud Run.
- **A live dashboard** at the top of the landing page pulls real-time aggregates from BigQuery (revenue, expenses, net, top customer, pipeline status). The agent and the dashboard share the same data.
- **Email delivery via Resend**, with a hardcoded recipient allowlist so the agent cannot autonomously email anywhere it likes. The agent drafts; the human reviews; the email goes to a verified inbox to forward.
- **Gemini 3** is the reasoning engine. Wrapped in Google Agent Development Kit, it plans multi-step investigations, calls tools, reacts to results, and decides whether to act.
- **The agent service** (also Cloud Run) streams reasoning and tool calls back to the browser via Server-Sent Events.
- **The landing page** (Vercel) wraps it all in a custom chat UI that makes the agent reasoning visible to the user, not hidden behind a black-box response.

The architecture diagram above shows the full request flow.

## Demo

- **Live site**: [ledger-agent-five.vercel.app](https://ledger-agent-five.vercel.app)
- **Video walkthrough**: coming before submission deadline

Try clicking "Find problems" on the live site. Cold start takes ~15 seconds on first request; subsequent requests are fast.

## Tech Stack

- **LLM**: Gemini 3 (Vertex AI)
- **Agent framework**: Google ADK (Agent Development Kit) with MCP
- **Data movement**: Fivetran (Google Sheets to BigQuery, scheduled)
- **Warehouse**: Google BigQuery
- **Custom MCP server**: Python, FastMCP, deployed on Cloud Run
- **Agent service**: Python, FastAPI, deployed on Cloud Run
- **Frontend**: Static HTML/CSS/JavaScript, hand-written (no framework), deployed on Vercel
- **Secrets**: Google Secret Manager

## Status

Built solo for the [Google Cloud Rapid Agent Hackathon](https://rapid-agent.devpost.com/), Fivetran track. Submission June 11, 2026.

All infrastructure is live and publicly accessible. Final polish in progress: demo video, Devpost write-up, end-to-end testing.

## Why This Matters

There are 5.5 million small businesses in the UK alone. Most are run by founders who never wanted to think about finance and can not afford the humans who do. The financial vigilance that protects large companies — pattern detection, anomaly surfacing, proactive alerts — has historically required an army of accountants and analysts. Agents change that.

## Repository Structure

    landing/                Landing page + architecture diagram
      index.html            Static page with live chat UI
      architecture.svg      System architecture diagram
    agent-service/          FastAPI service wrapping ADK
      agent_service.py      Streams agent responses via SSE
      Dockerfile            For Cloud Run deploy
      requirements.txt
    ledger-mcp/             Custom MCP server (7 tools)
      server.py             FastMCP, talks to BigQuery + Fivetran
      Dockerfile
      requirements.txt
    README.md

## Author

Built solo by [Ali Qureshi](https://github.com/ali-qureshi07) — first-year CS student at City University of London.

## License

MIT — see [LICENSE](./LICENSE).
