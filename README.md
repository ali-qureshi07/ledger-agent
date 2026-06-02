# LedgerAgent

> Autonomous finance operations agent for small e-commerce businesses. Catches the problems your bookkeeper misses.

![Status](https://img.shields.io/badge/status-in_development-yellow)
![License](https://img.shields.io/badge/license-MIT-blue)
![Hackathon](https://img.shields.io/badge/Google_Cloud_Rapid_Agent_Hackathon-2026-4285F4)

## The Problem

Small e-commerce founders run their financial life across Shopify, Stripe, banks, and a spreadsheet that's always three weeks out of date. Bookkeepers help, but they miss things. Duplicate vendor charges, customer concentration risk, silent subscription creep. Patterns that take vigilance to catch, not just categorisation.

These missable problems cost real money. A duplicate £892 ShipBob charge billed for three months is £2,676 quietly gone. A wholesale customer that grew to 22% of revenue is a runway-killer hiding in the data.

A bookkeeper costs around £40,000 a year. A part-time CFO is £80,000+. Most small businesses can afford neither.
## The Solution

LedgerAgent watches a business's financial data and surfaces issues before they compound. Think of it as the vigilant CFO they can't afford, running for £40 a month instead of £80,000 a year.

Ask it "are there any problems in my finances I should know about?" and it doesn't just answer. It plans a multi-step investigation, queries the data, runs analyses on the results, and tells you what it found, with numbers and a suggested action.

That distinction is the point. A chatbot can't do that. An agent can.

## How It Works

- **Fivetran** moves data from every source the business uses into a single warehouse, and exposes pipeline operations to the agent through its [MCP server](https://github.com/fivetran/fivetran-mcp).
- **BigQuery** stores the unified financial picture.
- **Gemini 3** is the reasoning engine. It plans multi-step investigations, calls tools, and reacts to results.
- **Google Cloud Agent Platform** orchestrates the agent loop and hosts it on Cloud Run.

When the agent finds something worth acting on, it doesn't stop at a recommendation. It can draft and send dispute emails, flag transactions, and trigger pipeline operations on your behalf.

## Demo

Coming soon — video and live URL by submission deadline.

## Tech Stack

- **LLM**: Gemini 3 (via Google Cloud Agent Platform)
- **Data movement**: Fivetran + Fivetran MCP Server
- **Warehouse**: Google BigQuery
- **Hosting**: Google Cloud Run
- **Frontend**: TBD (React or Next.js)

## Status

Built for the [Google Cloud Rapid Agent Hackathon](https://rapid-agent.devpost.com/), Fivetran track. Submission June 11, 2026.

Done: GCP + Agent Platform setup, Fivetran ↔ BigQuery pipeline, demo dataset with three planted stories the agent should find.

In progress: agent core capabilities, frontend with visible reasoning, Cloud Run deployment, demo video.

## Why This Matters

There are 5.5 million small businesses in the UK alone. Most are run by founders who never wanted to think about finance and can't afford the humans who do. The financial vigilance that protects large companies - pattern detection, anomaly surfacing, proactive alerts — has historically required an army of accountants and analysts. Agents change that.


## Author

Built solo by [Ali Qureshi](https://github.com/ali-qureshi07) — first-year CS student at City University of London.

## License

MIT — see [LICENSE](./LICENSE).
