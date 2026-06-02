# LedgerAgent

> Autonomous finance operations agent for small e-commerce businesses. Catches the problems your bookkeeper misses.

![Status](https://img.shields.io/badge/status-in_development-yellow)
![License](https://img.shields.io/badge/license-MIT-blue)
![Hackathon](https://img.shields.io/badge/Google_Cloud_Rapid_Agent_Hackathon-2026-4285F4)

## The Problem

Small e-commerce founders run their entire financial life across Shopify, Stripe, banks, and a spreadsheet that's always three weeks out of date. Bookkeepers help, but they miss things — duplicate vendor charges, customer concentration risk, silent subscription creep — because they're not looking at the patterns, they're just categorising rows.

These miss-able problems cost real money. A duplicate £892 charge billed for 3 months is £2,676 quietly gone. A customer that grew to 38% of revenue is a runway-killer waiting to happen.

A bookkeeper costs £40,000 a year. A CFO costs £150,000. Most small businesses can afford neither.

## The Solution

LedgerAgent is an autonomous agent that watches a small business's financial data and surfaces issues before they compound. It does what a vigilant CFO would do — except for £40 a month instead of £150,000 a year.

Ask it *"are there any problems in my finances I should know about?"* and it doesn't just answer. It plans, queries multiple data sources, runs analyses, reasons over the results, and tells you what it found — with concrete numbers and a suggested action.

## How It Works

- **Fivetran** moves data from every source the business uses into a single warehouse, and exposes pipeline operations to the agent through its [MCP server](https://github.com/fivetran/fivetran-mcp).
- **BigQuery** stores the unified financial picture.
- **Gemini 3** is the reasoning engine — it plans multi-step investigations, calls tools, and reacts to results.
- **Google Cloud Agent Platform** orchestrates the agent loop and hosts it on Cloud Run.

Without Fivetran, the agent has no data. Without Gemini, it can't reason. Without MCP, the agent can't reach Fivetran's operational layer. The integration is the product.

## Demo

Coming soon — video and live URL by submission deadline.

## Tech Stack

- **LLM**: Gemini 3 (via Google Cloud Agent Platform)
- **Data movement**: Fivetran + Fivetran MCP Server
- **Warehouse**: Google BigQuery
- **Hosting**: Google Cloud Run
- **Frontend**: TBD (React or Next.js)

## Status

Built for the [Google Cloud Rapid Agent Hackathon](https://rapid-agent.devpost.com/) (Fivetran track). Submission deadline: June 11, 2026.

| Milestone | Status |
|---|---|
| GCP + Agent Platform setup | ✅ Done |
| Fivetran ↔ BigQuery pipeline | ✅ Done |
| Demo dataset with planted stories | ✅ Done |
| Agent core capabilities | 🚧 In progress |
| Frontend with visible reasoning | ⏳ Planned |
| Deployment + video | ⏳ Planned |

## Why This Matters

There are 5.5 million small businesses in the UK alone. Most are run by founders who never wanted to think about finance and can't afford the humans who do. The financial vigilance that protects large companies — pattern detection, anomaly surfacing, proactive alerts — has historically required an army of accountants and analysts. Agents change that.

This isn't a chatbot wearing an agent costume. It plans, executes multi-step investigations, calls tools that depend on previous tool results, and produces actions. That distinction is the whole point.

## Author

Built solo by [Ali Qureshi](https://github.com/ali-qureshi07) — first-year CS student at City University of London, currently building toward fintech and quant-developer roles.

## License

MIT — see [LICENSE](./LICENSE).
