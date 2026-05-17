# Mobile-First Options Decision Layer - Product and Engineering Plan

> **Project**: BRstock1 Extension  
> **Date**: 2026-05-15  
> **Status**: Planning  
> **Pain Origin**: Real trading experience across Schwab, Moomoo, IBKR

---

## 1. The Pain Point — Why This Matters

### 1.1 What Every Options App Gets Wrong

All existing options platforms (Schwab, Moomoo, IBKR, Robinhood, Webull) are built from a **brokerage execution perspective**:

- How to place an order
- How to route fills
- How to display a full option chain

But the user's real question is always:

> **"What should I do right now with this position?"**

Specifically:

| Real Decision Question | What Brokers Show Instead |
|---|---|
| Should I roll this spread? | Raw chain table with 200+ rows |
| What's my new breakeven after rolling? | Nothing — mental math required |
| Is IV high or low right now? | A single IV number with no context |
| How much theta am I bleeding daily? | Greeks buried in a sub-menu |
| What's my total portfolio delta risk? | Individual position Greeks only |
| Is this spread mainly vega or delta? | No dominant-risk indicator |
| What's my recovery probability? | Not available anywhere |

### 1.2 Why Mobile Makes It 10x Worse

Options are the **highest information-density instrument** in retail trading:

- Strike × Expiration × IV × Greeks × Skew × Term Structure × Assignment Risk × Theta Decay × Position Interaction

On desktop, this is barely manageable. On mobile:

- Tables are too dense to read
- Numbers are too small to parse
- Users must mentally cross-reference multiple screens
- Multi-leg spreads are completely non-intuitive
- Roll comparison requires 3-4 screen switches

**Result**: Users are "manually parsing risk" on a 6-inch screen. This is the gap.

### 1.3 The Opportunity

Build a **decision layer**, not a **trading execution layer**.

The product doesn't compete with brokers on order routing. It competes on **compressed, actionable insight** — the thing brokers don't provide:

```
"Your QQQ 700/720 bull call spread has 18 DTE remaining.
 Current breakeven: 711.55. QQQ is at 708.
 IV is at 78th percentile (past 1 year).
 This position is now primarily theta-driven — you're losing $18/day.
 Rolling to June 720/740 would lower breakeven to 722 but costs $3.20 net debit.
 Recommendation: Hold if you expect QQQ above 712 in 18 days."
```

No broker gives you this. **BRstock1 can.**

---

## 2. BRstock1 Existing Asset Audit

Before building anything new, here's what the project already has:

### 2.1 Direct Reuse — Ready Now

| Module | Location | Reuse For |
|---|---|---|
| **OptionSynth Engine** | `options_synth.py` (919 lines) | Black-Scholes pricing, Greeks, IV estimation, chain generation |
| **Schwab Market Data** | `schwab_market_data.py` (444 lines) | Real-time option chains, quotes, normalized schema |
| **Options Calibration** | `options_calibration.py` (226 lines) | Synth-vs-real IV correction factors |
| **Options Routes** | `routes/options.py` (596 lines) | Schwab chain, synthetic chain, calibration APIs |
| **Backtest Engine** | `options_synth.py` — `OptionBacktester` | Wheels, LEAPS, vertical spreads backtesting |
| **AI Analysis Pipeline** | `routes/stocks.py` — Gemini/OpenRouter/Local | Structured AI report generation |
| **FastAPI Backend** | `main.py` + modular routes | API framework with auth, DB, static serving |
| **Bilingual UI** | `app.js` i18n system | EN/ZH language switching |

### 2.2 Needs Extension

| Capability | Current State | What's Needed |
|---|---|---|
| **Position Tracking** | No real position storage | New: `user_option_positions` table |
| **IV Percentile** | HV_20d + RSI sentiment | New: Historical IV series for percentile ranking |
| **Roll Analysis** | Not implemented | New: Roll comparison calculator |
| **Portfolio Greeks** | Individual contract Greeks | New: Aggregate position-level Greeks |
| **Mobile UI** | Desktop-only static HTML | New: Responsive mobile-first pages |
| **Push Insights** | None | New: Decision alert engine |

### 2.3 Key Advantage

BRstock1 already has what most startups spend months building:

1. **Working Black-Scholes + Greeks engine** with calibration
2. **Live Schwab data integration** with OAuth token management
3. **Synthetic chain fallback** when real data is unavailable
4. **AI report generation** with structured input
5. **Bilingual support** baked into the UI framework

The decision layer is an **integration and presentation problem**, not a computation problem.

---

## 3. Product Definition

### 3.1 Core Concept

**Options Copilot** - A mobile-first decision surface layered on top of broker data.

Not a broker. Not a charting app. A **decision compression engine** that answers:

1. **Position Health**: "How is my current position doing?"
2. **Action Clarity**: "Should I hold, roll, close, or adjust?"
3. **Risk Awareness**: "What's my real exposure right now?"
4. **IV Context**: "Am I buying expensive or cheap volatility?"
5. **What-If Scenarios**: "If I roll to X, what changes?"

### 3.2 User Flow (Mobile-First)

```
+-----------------------------+
|  [Mobile] Options Copilot   |
|                             |
|  +---------------------+    |
|  | QQQ 700/720 BCS     |    |
|  | (Yellow) 18 DTE | -$340 |
|  | BE: 711.55 | Delta 0.32 |
|  | Theta: -$18/day         |
|  | IV Rank: 78%  ###.      |
|  | [Roll] [Close] [AI]     |
|  +---------------------+    |
|                             |
|  +---------------------+    |
|  | TSLA LEAPS 180C     |    |
|  | (Green) 245 DTE | +$2.1k |
|  | Delta 0.78 | Theta: -$8/day |
|  | IV Rank: 45%  ##..      |
|  | [Details] [AI]          |
|  +---------------------+    |
|                             |
|  -- Portfolio Risk --       |
|  Net Delta: +0.65 | Net Theta: -$26 |
|  Total Risk: $4,200         |
|  Max Loss Today: -$890      |
+-----------------------------+
```

### 3.3 Decision Cards - The Core UI Primitive

Each position renders as a **Decision Card** that shows:

| Layer | Content | Source |
|---|---|---|
| **Header** | Position name + structure | User input / broker import |
| **Status** | P/L, DTE, color-coded health | OptionSynth real-time calc |
| **Key Metrics** | Breakeven, dominant Greek, IV rank | OptionSynth + historical IV |
| **Theta Burn** | Daily/weekly dollar decay | OptionSynth Greeks |
| **Risk Gauge** | Primary risk factor (theta/vega/delta) | Greek analysis |
| **Actions** | Roll / Close / AI Analysis buttons | UI actions |

### 3.4 AI Decision Reports

When user taps "AI" on a position card:

**Input to AI** (structured JSON):
```json
{
  "position": "QQQ 700/720 Bull Call Spread",
  "current_price": 708.50,
  "entry_debit": 11.55,
  "current_value": 8.20,
  "breakeven": 711.55,
  "dte": 18,
  "greeks": {"delta": 0.32, "theta": -0.18, "vega": 0.35, "gamma": 0.008},
  "iv_rank_1y": 78,
  "hv_20": 0.22,
  "rsi": 48,
  "underlying_trend": "neutral-bearish",
  "roll_options": [
    {"target": "Jun 720/740", "net_cost": 3.20, "new_breakeven": 723.20, "new_dte": 48}
  ]
}
```

**AI Output** (compressed for mobile):
```
[Report] Position Assessment: HOLD with caution

Your QQQ 700/720 spread is -29% from entry with 18 DTE.
QQQ needs to reach 712 for breakeven - that's +0.5% from here.

[Warning] IV is elevated (78th percentile). This helps your long leg
   but time decay is now dominant at $18/day.

[Roll] Roll Analysis: Rolling to Jun 720/740 costs $3.20 and extends
   DTE by 30 days but raises breakeven from 712 -> 723.
   Only attractive if you expect QQQ above 725.

[Tip] Suggestion: If QQQ doesn't recover above 710 within 5 days,
   consider closing at ~30% loss rather than rolling into a
   higher-breakeven position.
```

---

## 4. Technical Architecture

### 4.1 New Backend Modules

```
services/backend_api/
|-- routes/
|   |-- options.py              -- Existing (extend)
|   |-- positions.py            -- [New] Position management & decision APIs
|   |-- decision.py             -- [New] AI decision report generation
|-- options_synth.py            -- Existing (extend with roll calculator)
|-- position_analyzer.py        -- [New] Portfolio-level risk aggregation
+-- iv_history.py               -- [New] Historical IV percentile tracker
```

### 4.2 New Database Tables

```sql
-- User option positions (manual entry or broker import)
CREATE TABLE IF NOT EXISTS user_option_positions (
    id              SERIAL PRIMARY KEY,
    user_id         VARCHAR(100) NOT NULL,
    ticker          VARCHAR(10) NOT NULL,
    position_type   VARCHAR(30) NOT NULL,      -- 'BULL_CALL_SPREAD', 'LEAPS', etc.
    legs            JSONB NOT NULL,             -- [{type, strike, expiry, qty, entry_price}]
    entry_date      DATE NOT NULL,
    entry_debit     DECIMAL(12,2),
    status          VARCHAR(20) DEFAULT 'OPEN', -- OPEN / CLOSED / ROLLED
    notes           TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Historical IV snapshots for percentile calculation
CREATE TABLE IF NOT EXISTS iv_history (
    id          SERIAL PRIMARY KEY,
    ticker      VARCHAR(10) NOT NULL,
    date        DATE NOT NULL,
    hv_20       DECIMAL(8,6),
    synth_atm_iv_30d  DECIMAL(8,6),
    rsi         DECIMAL(6,2),
    spot_price  DECIMAL(12,2),
    UNIQUE(ticker, date)
);

-- Decision reports cache
CREATE TABLE IF NOT EXISTS option_decision_reports (
    id          SERIAL PRIMARY KEY,
    user_id     VARCHAR(100) NOT NULL,
    position_id INTEGER REFERENCES user_option_positions(id),
    report_type VARCHAR(30),
    language    VARCHAR(5) DEFAULT 'en',
    report      TEXT NOT NULL,
    input_snapshot JSONB,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.3 New API Endpoints

```
# Position Management
POST   /api/positions                  - Add a position (manual entry)
GET    /api/positions                  - List user's open positions
GET    /api/positions/{id}/snapshot    - Live snapshot: Greeks, P/L, IV rank
PUT    /api/positions/{id}            - Update position (roll, close, notes)
DELETE /api/positions/{id}            - Remove position

# Decision Engine
GET    /api/positions/{id}/decision   - AI decision report for one position
GET    /api/positions/portfolio-risk  - Aggregate portfolio Greeks & risk
GET    /api/positions/{id}/roll-analysis?target_dte=48&target_width=20

# IV Context
GET    /api/iv/{ticker}/percentile    - Current IV rank (1Y, 6M, 3M)
GET    /api/iv/{ticker}/history       - Historical IV series for charting
```

### 4.4 Position Analyzer Core Logic

```python
class PositionAnalyzer:
    """Aggregates real-time analytics for user option positions."""

    def snapshot(self, position, current_price, chain_or_synth):
        """Returns a decision-ready snapshot for one position."""
        return {
            "current_value": ...,
            "unrealized_pl": ...,
            "breakeven": ...,
            "dte": ...,
            "net_delta": ...,
            "net_theta": ...,      # Daily dollar theta
            "net_vega": ...,
            "dominant_greek": ..., # "theta" | "vega" | "delta"
            "iv_rank_1y": ...,
            "health": ...,        # "healthy" | "at_risk" | "critical"
        }

    def portfolio_risk(self, positions, current_prices):
        """Aggregate risk across all open positions."""
        return {
            "total_net_delta": ...,
            "total_net_theta_daily": ...,
            "total_risk_at_work": ...,
            "max_loss_today": ...,
            "concentration_warning": ...,
        }

    def roll_analysis(self, position, current_price, target_dte, target_width):
        """Compare current position vs proposed roll."""
        return {
            "current": { "breakeven": ..., "max_profit": ..., "dte": ... },
            "rolled":  { "breakeven": ..., "max_profit": ..., "net_cost": ... },
            "cost_per_day_gained": ...,
            "recommendation": ...,
        }
```

---

## 5. Mobile UI Architecture

### 5.1 Approach: Responsive Web, Not Native App

Build as a responsive web page within BRstock1, not a separate native app.

**Rationale**:
- BRstock1 already serves static HTML via FastAPI
- No app store approval needed
- Users can "Add to Home Screen" for app-like experience
- Reuses existing auth, API, and i18n infrastructure

### 5.2 Mobile Design Principles

1. **Card-based layout** - One position = one swipeable card
2. **Color-coded health** - Green/Yellow/Red instant status
3. **Large touch targets** - Minimum 44px tap zones
4. **Progressive disclosure** - Summary first, tap for details
5. **Bottom-sheet actions** - Roll/Close/AI as bottom drawers
6. **Dark theme default** - Matches trading environment

---

## 6. Implementation Roadmap

### Phase 0: IV History Foundation (1 session)

**Goal**: Start collecting IV history — needed for percentile rankings.

- [ ] Create `iv_history` table
- [ ] Add daily IV snapshot job (runs with existing after-close scheduler)
- [ ] Backfill 1 year of synthetic ATM IV for QQQ, TSLA, AAPL, NVDA, SPY
- [ ] Add `GET /api/iv/{ticker}/percentile` endpoint

**Why first**: IV percentile is the single most valuable context signal. Every day without collection = one less data point.

### Phase 1: Position Management Backend (1-2 sessions)

**Goal**: Users can manually enter and track option positions.

- [ ] Create `user_option_positions` table
- [ ] Create `routes/positions.py` with CRUD endpoints
- [ ] Implement `PositionAnalyzer.snapshot()` - live P/L, Greeks, breakeven
- [ ] Wire to existing OptionSynth for real-time pricing
- [ ] Wire to Schwab for live chain data when available

### Phase 2: Decision Cards - Mobile UI MVP (2-3 sessions)

**Goal**: Working mobile-first position dashboard.

- [ ] Add `page-copilot` to `index.html` with responsive layout
- [ ] Build Decision Card component with health indicators
- [ ] Add position entry form (bottom sheet on mobile)
- [ ] Portfolio risk summary bar
- [ ] Theta burn counter (daily $ loss across all positions)
- [ ] Test on iPhone Safari, Android Chrome

### Phase 3: Roll Calculator (1 session)

**Goal**: Compare roll scenarios directly on the position card.

- [ ] Implement `PositionAnalyzer.roll_analysis()`
- [ ] Add roll comparison UI as expandable card section
- [ ] Show side-by-side: current vs rolled breakeven, cost, DTE
- [ ] Cost-per-day-gained metric

### Phase 4: AI Decision Reports (1-2 sessions)

**Goal**: One-tap AI analysis for any position.

- [ ] Create `routes/decision.py` with structured AI prompt
- [ ] Reuse existing Gemini/OpenRouter pipeline
- [ ] Create `option_decision_reports` table for caching
- [ ] Mobile-optimized report display
- [ ] Bilingual report generation (EN/ZH)

### Phase 5: Broker Position Import (future)

- [ ] Schwab positions API (requires trading scope)
- [ ] IBKR / Moomoo position sync (when available)
- [ ] Auto-detect position structure

---

## 7. Competitive Positioning

| Feature | Brokers | Analytics Sites | **BRstock1 Copilot** |
|---|---|---|---|
| Mobile-first design | [NO] Desktop-first | [NO] Desktop-only | [YES] Built for phone |
| Decision compression | [NO] Raw data dump | [WARN] Charts only | [YES] Actionable cards |
| AI position analysis | [NO] | [NO] | [YES] Per-position AI |
| Roll comparison | [WARN] Manual only | [NO] | [YES] One-tap compare |
| IV percentile context | [WARN] Some | [YES] | [YES] On every card |
| Portfolio risk aggregate | [WARN] Basic | [NO] | [YES] Net Greeks + risk |
| Bilingual EN/ZH | [NO] | [NO] | [YES] Built-in |
| Synthetic chain fallback | [NO] | [NO] | [YES] Works offline |

**Wedge Strategy**: Personal tool first -> if it saves 10+ min per decision and prevents 1-2 bad rolls/month -> real product value for any mobile options trader.

---

## 8. Open Questions

1. **Which broker will you use most?** Determines position import priority.
2. **How many active positions do you typically hold?** Affects portfolio view design.
3. **Real-time updates or 30-second refresh acceptable?**
4. **Separate page or replace existing Options Analysis page?**
5. **Start Phase 0 (IV history) immediately or Phase 1 (positions)?**

---

## 9. Summary

BRstock1 is **uniquely positioned** to build this:

- [YES] **Math engine** exists (OptionSynth + Greeks + B-S + calibration)
- [YES] **Data pipeline** exists (Schwab + synthetic fallback)
- [YES] **AI infrastructure** exists (Gemini + OpenRouter + bilingual)
- [YES] **Backend framework** exists (FastAPI + auth + DB)
- [YES] **You are the target user** - every design decision comes from real pain

What's missing is the **presentation layer** that compresses all this into mobile-friendly decision cards. That's a UI/UX problem, not an infrastructure problem.

**Recommended first action**: Start Phase 0 today — begin collecting IV history data. It costs almost nothing and creates irreplaceable time-series data.
