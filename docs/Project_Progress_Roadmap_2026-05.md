# BRStock AI Project Progress & Roadmap

Date: 2026-05-10  
Status: active product prototype moving toward a credible trading research workbench

## 1. Product Positioning

BRStock AI is a bilingual stock and options research platform for individual traders. The product direction is not a marketing site or a lightweight quote viewer. It should become a dense decision workbench that helps users answer:

- What is happening in this stock or ETF?
- Which indicators and market assumptions support the signal?
- How did this strategy behave historically?
- Which part of the result came from ETF exposure, options exposure, cash, or execution assumptions?
- Can the user iterate a strategy with evidence instead of guessing?

The strongest current product theme is **strategy validation**: combine chart analysis, technical indicators, AI commentary, synthetic options chains, and backtesting into a clear research loop.

## 2. Current System Snapshot

### Backend

The backend is a FastAPI service with modular route files:

- `routes/auth.py`: registration, login, password reset, current-user profile, password change.
- `routes/stocks.py`: watchlist, ticker search, historical OHLCV, summary, indicators, data fetch, AI stock analysis.
- `routes/options.py`: synthetic option chain, Moomoo status/chain helpers, option backtests.
- `routes/strategies.py`: system strategies, user strategies, stock strategy backtests, option strategy backtests, portfolio backtests.
- `options_synth.py`: synthetic options engine using Black-Scholes, RSI/HV-based IV estimation, Greeks, WHEELS/LEAPS/spread backtesting.
- `internal/db_client/database.py`: SQLite fallback or online DB via `DATABASE_URL`.

### Frontend

The frontend is a static web UI under `services/web_ui/` with these working product areas:

- Dashboard
- Chart Analysis
- AI Insights
- Strategy
- Backtesting
- Options Analysis
- Synthetic Chain Inspector
- Bilingual English/Chinese UI switch
- Watchlist with account-based persistence

The UI already has the right product shape: practical, dense, and focused on trading workflows. Some sections still mix prototype/mock data with live API data, so user trust should be improved before adding many new features.

### Data And Analysis

Current data sources and methods:

- Yahoo Finance via `yfinance` for stock history and backtest data refresh.
- Local SQLite fallback for development.
- Neon/PostgreSQL-compatible online database via environment configuration.
- Moomoo OpenD integration path for real option-chain data.
- Synthetic option-chain fallback through `OptionSynth`.
- Gemini, OpenRouter, and local AI fallback paths for analysis text.

## 3. Recently Fixed API Alignment Issues

The following gaps were identified and patched:

- Frontend AI analysis now calls `/api/stocks/{symbol}/analysis` with `language=...`, matching the backend route.
- Frontend password change now calls `/api/auth/change-password`.
- Backend now supports `PUT /api/auth/change-password`.
- Backend now supports `GET /api/options/moomoo/chain/{ticker}` for the existing frontend Moomoo options page.
- Backend now supports `POST /api/options/moomoo/command` for allowed OpenD verification commands.
- Frontend strategy create/delete calls now use the correct `apiFetch(endpoint, options)` shape.
- Moomoo status now returns a proper `connected` boolean instead of treating any status dictionary as connected.

## 4. Known Product And Technical Gaps

These gaps are important because they affect trust more than visual polish:

- Some dashboard and news content is still mock/demo data.
- Backtest reports need clearer assumptions: slippage, fill price, bid/ask/mid, capital utilization, and data source.
- AI analysis is currently based mostly on technical indicators, not yet full market context.
- Portfolio backtest exists, but the report should better explain attribution: core ETF, options sleeve, idle cash, rebalance effect.
- There is no single page that connects signal, evidence, risk, and strategy iteration.
- Test coverage is light for API/frontend contract drift.
- Moomoo OpenD is inherently session-sensitive, so the product needs graceful fallback to synthetic data.

## 5. Recommended Product North Star

### Strategy Evidence Lab

The next major product milestone should be **Strategy Evidence Lab**.

This is not a separate product. It is a unifying workflow that connects existing modules into a credible decision system:

1. Select ticker and strategy.
2. Show current signal and why it exists.
3. Run historical backtest.
4. Compare against benchmarks.
5. Expose assumptions.
6. Generate a bilingual strategy report.
7. Save the experiment for future comparison.

The goal is to turn BRStock from "many useful screens" into "one coherent strategy research loop."

## 6. Development Roadmap

The roadmap intentionally limits each step to one or two concrete features. This keeps each development session small, testable, and easy for future contributors to understand.

### Phase 0: Stabilize The Current Prototype

Goal: make the current app reliable enough for demos and internal iteration.

Feature 1: API contract cleanup

- Keep frontend route names aligned with backend route names.
- Add compatibility shims only when needed.
- Add a small API smoke-test checklist.

Feature 2: Demo data labeling

- Clearly mark mock/demo news and mock dashboard signals.
- Prefer "Demo" or "Synthetic" labels over implying live data.

Acceptance criteria:

- Login, watchlist, chart loading, AI analysis, strategy creation, and one backtest path work without obvious route errors.
- Users can tell which data is real, cached, synthetic, or demo.

### Phase 1: Backtest Report Credibility

Goal: make strategy results explainable and investor-demo ready.

Feature 1: Assumption panel

- Show data source.
- Show strategy parameters.
- Show fill model: bid, ask, mid, slippage.
- Show capital utilization basis.
- Show synthetic-vs-real chain source.

Feature 2: Benchmark comparison

- Compare tested strategy against buy-and-hold of the same ticker.
- For portfolio tests, compare against QQQ, VOO, and QQQ/VOO 50/50.

Acceptance criteria:

- A user can look at a backtest and understand how the numbers were produced.
- Backtest output includes strategy return, benchmark return, and key assumptions.

### Phase 2: Strategy Evidence Lab MVP

Goal: create one unified research page.

Feature 1: Evidence snapshot endpoint

Proposed endpoint:

```text
GET /api/strategy-lab/{ticker}/snapshot
```

Returned sections:

- latest price summary
- RSI/MACD/SMA/EMA
- current signal explanation
- available strategies
- data freshness

Feature 2: Evidence Lab page

Frontend layout:

- left rail: ticker, strategy, dates, capital, key parameters
- center: price chart, equity curve, benchmark comparison
- right rail: signal explanation, assumptions, risk summary
- bottom: trade log and saved experiment notes

Acceptance criteria:

- One page can explain "what signal exists, what strategy was tested, how it performed, and under which assumptions."

### Phase 3: AI Strategy Report

Goal: make AI useful as an analyst, not just a text generator.

Feature 1: Structured AI input

- Feed the AI a compact JSON summary:
  - price trend
  - indicators
  - backtest metrics
  - benchmark comparison
  - assumptions
  - risk flags

Feature 2: Bilingual report generation

Proposed endpoint:

```text
POST /api/strategy-lab/report
```

Report sections:

- setup
- signal interpretation
- historical evidence
- risk notes
- next experiment suggestions

Acceptance criteria:

- AI output references actual metrics from the run.
- English and Chinese reports are available.
- The report avoids pretending synthetic or demo data is live market truth.

### Phase 4: Experiment History

Goal: let users iterate instead of running isolated tests.

Feature 1: Save experiment

- Save ticker, strategy, parameters, date range, metrics, assumptions, and AI report.

Feature 2: Compare experiments

- Show two or more saved runs side by side.
- Highlight changed parameters and changed outcomes.

Acceptance criteria:

- User can answer: "Did my parameter change improve the strategy, or just overfit this period?"

### Phase 5: Real Data Hardening

Goal: improve live-readiness without depending on one fragile provider.

Feature 1: Provider-normalized option chain schema

- Normalize Moomoo, synthetic, CSV, and future providers into one schema.

Feature 2: Data freshness and fallback state

- Show whether data is live, cached, synthetic, or unavailable.
- Use synthetic chain as a graceful fallback when OpenD is offline.

Acceptance criteria:

- The Options page never silently fails or mislabels data.
- All option-chain consumers receive the same normalized fields.

## 7. Design Direction

The product should feel like a professional trading research surface:

- Dense but readable.
- Tables and charts before decorative cards.
- Clear labels for assumptions and data source.
- Bilingual from the start.
- No marketing hero pages inside the app.
- Avoid over-decorated visuals that reduce trust.

Recommended visual hierarchy:

- Top: ticker, market state, data freshness.
- Middle: chart and evidence.
- Right: interpretation and risk.
- Bottom: logs, assumptions, raw details.

## 8. Immediate Next Developer Tasks

Recommended next session:

1. Add a backtest assumption panel to the existing Backtesting page.
2. Add benchmark comparison for the simplest stock/ETF strategy path.

Recommended session after that:

1. Add `/api/strategy-lab/{ticker}/snapshot`.
2. Create the first Strategy Evidence Lab frontend page using existing chart and indicator components.

Recommended session after that:

1. Add AI Strategy Report generation from structured backtest evidence.
2. Save generated reports with experiment metadata.

## 9. Investor Demo Story

The investor demo should tell this story:

1. BRStock is building a research workbench for self-directed traders.
2. The platform already connects market data, indicators, AI commentary, synthetic options, and backtesting.
3. The unique wedge is options strategy validation when historical option-chain data is expensive or unavailable.
4. The next product milestone is Strategy Evidence Lab: evidence, assumptions, risk, and AI report in one workflow.
5. This creates a repeatable loop: research, test, explain, save, compare, improve.

