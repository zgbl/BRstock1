# Options Chain Realtime Integration Plan

Date: 2026-05-02  
Project: `StockAnalysis2026` & `BRStock1` Integration

## Goal

Build a Python workflow that can refresh the options workbook near market open, pull option-chain data for TSLA, QQQ, MCD, and HIMS, update the workbook input cells, and leave the formulas/dashboard ready for decision-making. Integrate this into the BRStock platform to provide a real-time options analysis dashboard.

The first version should focus on **read-only market data**. Order placement should be a separate later phase after the data pipeline is reliable.

## Short Answer

Yes, this is technically feasible.

The best MVP path is:

1. Use a real options data provider or broker API to pull chains.
2. Normalize all providers into one internal schema.
3. Match contracts to the workbook rows by ticker, expiration, option type, target delta, and strike.
4. Update only the yellow input cells in Excel, or directly render the analysis on BRStock UI.
5. Let Excel/UI recalculate the LEAPS model and dashboard.

## Broker and Data Source Feasibility

| Source | Feasibility | Notes |
|---|---:|---|
| Moomoo OpenAPI | High | Good candidate because it has Python SDK + local OpenD gateway. |
| Charles Schwab Trader API | Medium | Likely feasible if developer app/OAuth access is approved. |
| Merrill Edge | Low | Treat as manual CSV fallback. |
| Tradier | High | Very good for an API prototype. |
| CSV/manual export | High | Useful fallback when APIs fail. |

## Integration into BRStock

The UI will replicate the LEAPS decision models and Next-Week strategy matrices natively inside the BRStock web platform. 

We will:
1. Provide a `page-options` view in the Web UI.
2. Add a Python-based backend endpoint in `main.py` to route option chains data via OpenD or Tradier.
3. Keep the frontend read-only to show dynamic quotes (bid, ask, delta) and score option strategies based on criteria.

## Configuration

We use an `options_data.example.toml` template to store credentials safely without committing them.

## MVP Development Plan
Phase 1: CSV-based safe read-only UI inside BRStock.
Phase 2: Live data feed using Moomoo OpenD Python SDK.
Phase 3: Integration of strategy formulas natively in BRStock UI.
Phase 4: Order execution guardrails.
