# BRStock AI Product Ideas

BRStock AI is a bilingual stock and options analysis platform for individual traders. The product should combine long-term market data, technical indicators, AI-assisted research, custom strategy design, and realistic backtesting. The main goal is not to make a beautiful landing page; it is to build a dense, useful trading workbench.

Default UI language should be English, with a persistent Chinese/English switch available at any time.

## Core Product Direction

1. Market data ingestion
   - Download stock data from sources such as Yahoo Finance and Moomoo API.
   - Store data in an online database.
   - Daily candles are the most important dataset.
   - Each tracked stock should ideally have 10+ years of daily data, preferably 20-30 years.
   - Chart defaults to daily candles, with support for weekly and monthly views.

2. Technical analysis API
   - Backend services calculate indicators.
   - Different services may eventually provide different indicator groups.
   - First indicator set:
     - RSI
     - MACD
     - Moving averages: SMA / EMA

3. Web frontend
   - Web-based visualization for stock data and technical indicators.
   - UI should be dense and practical.
   - Avoid excessive decorative whitespace.
   - Prioritize useful information density over marketing-style presentation.

4. Watchlists and user customization
   - Users can define tracked stocks and stock groups.
   - Users can save strategy parameters to their own account.

5. AI-assisted analysis
   - Use stock data, technical indicators, and market context as model input.
   - Generate stock analysis reports.
   - Current local AI configuration should not be removed.
   - Local AI via LM Studio remains a fallback path.
   - Gemini is configured as the default cloud AI provider.
   - User should be able to switch Chinese/English report language.

6. Trading decision support
   - Use technical indicators plus additional information:
     - News
     - Earnings and company announcements
     - Political conditions
     - Sector and industry dynamics
   - Improve AI-assisted buy/sell decision models over time.
   - Users should be able to tune parameters and test decision logic.

7. Backtesting and iteration
   - Run strategies against historical data.
   - Compare model results, inspect trade logs, identify weaknesses, and iterate.
   - Backtesting should expose assumptions clearly, especially position sizing and execution pricing.

## Existing / Planned Main Modules

### Dashboard

High-level market overview, watchlist summary, market activity, AI score summary, and quick navigation.

### Chart Analysis

Candlestick charts, technical indicators, and AI analysis panel. Daily chart is the default. Weekly/monthly should be supported.

### Strategy

Create, save, and manage user-defined trading strategies.

### Backtesting

Run historical simulations for stock and option strategies. Backtesting output should include:

- Total return
- Final value
- Win rate
- Trade log
- Equity curve
- Cash balance
- Risk at work
- Available cash
- Eventually: max drawdown, benchmark comparison, and slippage sensitivity

### Portfolio Backtesting

Run combined portfolio simulations with multiple sleeves, not only single-strategy tests.

Example default template:

- Initial account value: $100,000
- Core market sleeve: 70% of account value
  - Invest in broad market ETFs
  - Example allocation: QQQ 35% and VOO 35%
  - Rebalance or dollar-cost-average according to user-selected rules
- Options sleeve: 30% of account value
  - Run one selected options strategy, such as bull call spread, LEAPS, PMCC, or wheels
  - Options risk rules still apply inside this sleeve
- Default portfolio rebalance frequency: quarterly, to control sleeve drift without excessive monthly trading.

All portfolio setup values must be user-configurable, not hardcoded:

- Initial account value
- Number of sleeves
- Sleeve names
- Sleeve target percentages
- Core ETF tickers
- Per-ETF target weights
- Contribution / DCA schedule
- Rebalance frequency and threshold
- Options sleeve percentage
- Options strategy type
- Options strategy parameters
- Whether options `Capital Utilization` is measured against the options sleeve or the whole account

Portfolio report requirements:

- Total account value curve
- Total return and annualized return for the full portfolio
- Max drawdown for the full portfolio
- Core market sleeve value, contribution, and return rate
- QQQ sleeve value, contribution, and return rate
- VOO sleeve value, contribution, and return rate
- Options sleeve value, contribution, and return rate
- Cash balance and uninvested cash drag
- Percentage contribution of each sleeve to total profit/loss
- Trade log for options sleeve
- Rebalance / contribution log for core ETF sleeve
- Benchmark comparison against buy-and-hold QQQ, VOO, and a 50/50 QQQ/VOO benchmark
- Timeframe controls must support quick presets and explicit custom start/end dates, so weak periods such as 2024-2025 can be isolated and diagnosed.
- Performance charts should overlay the tested options underlying price, using a separate axis when needed, so users can compare portfolio/option behavior against the stock or ETF itself.

Important accounting rule:

- The report must separate total portfolio performance from sleeve-level attribution.
- If the total portfolio gains $20,000, the user should see how much came from QQQ, how much came from VOO, how much came from options, and how much was affected by idle cash.
- Options `Capital Utilization` should be interpreted inside the options sleeve unless explicitly configured as a whole-account risk cap.
- Portfolio rebalance must operate across sleeves, not only inside the ETF sleeve. If the target is Core 70% / Options 30%, quarterly rebalance should sell down an oversized options sleeve or refill an underweight options sleeve.
- Changes to rebalance logic can materially change historical backtest results; document that behavior whenever it changes.
- In portfolio backtests, the Options Sleeve ticker is an explicit configurable field. Its initial/default value should follow the top-level stock ticker for convenience, but once the user edits the sleeve ticker, that sleeve ticker must control the options test independently.
- Reports must display the actual options underlying ticker used, so users can verify whether they are testing QQQ, VOO, TSLA, or another symbol.

### Options Analysis

Options chain analysis for real and synthetic data:

- Call/put IV ranking
- Greeks table
- Bid/ask/mid display
- Put/call ratios
- Volume and open interest
- IV heatmap in future versions

### Synthetic Option Chain Inspector

Dedicated page for inspecting synthetic option chain generation.

Inputs:

- Ticker
- Date
- DTE list

Outputs:

- Actual data date used
- Spot price
- RSI
- 20-day historical volatility
- Full synthetic chain
- Bid / ask / mid
- Premium
- IV
- Delta, Gamma, Theta, Vega

Purpose:

- Manually inspect whether the synthetic chain looks reasonable.
- Compare synthetic QQQ chains against real broker chains.
- Catch obvious IV, pricing, delta, and spread issues before trusting backtest results.

## OptionSynth

Detailed design document: [OptionSynth_Design.md](OptionSynth_Design.md)

OptionSynth is the synthetic options chain and options strategy backtesting engine.

Current design:

- Generate synthetic option chains from historical daily stock data.
- Use Black-Scholes pricing.
- Estimate IV from:
  - 20-day historical volatility
  - RSI sentiment multiplier
  - Basic moneyness/skew adjustment
- Generate:
  - Bid
  - Ask
  - Mid
  - Premium
  - IV
  - Delta
  - Gamma
  - Theta
  - Vega
- Do not store every generated chain in the database by default, to avoid storage bloat.

Supported / planned strategies:

- Wheels
- LEAPS
- PMCC
- Bull call debit spread
- Bear put debit spread
- Bull put credit spread

Backend file:

- `services/backend_api/options_synth.py`

## Bull Call Spread Backtest Decisions

The current working example is QQQ 40 DTE bull call debit spread.

Strategy rule:

- Buy call near target long delta.
- Sell higher strike call by spread width.
- Example target:
  - DTE: 40
  - Spread width: 20
  - Long delta target: about 0.60
  - Short delta target: about 0.30, but when width is set, short strike is mainly chosen by long strike + width.

Important clarification from real option chain review:

- A 700/720 bull call spread is:
  - Buy 700 Call
  - Sell 720 Call
- It is not calculated by subtracting two vertical spread quotes such as `700/710 - 710/720`.
- If using real option chain prices:
  - Net debit = 700C price - 720C price
  - Max loss = net debit * 100
  - Max profit = (20 - net debit) * 100
  - Breakeven = 700 + net debit

Example from real chain discussion:

- 700C last around 28.92
- 720C last around 17.37
- Net debit around 11.55
- Max loss around $1,155 per contract
- Max profit around $845 per contract
- Breakeven around 711.55

Conclusion:

- This is not a cheap lottery-like 1:18 payoff.
- It is a directional bullish spread with limited loss and limited gain.
- The trade depends heavily on the trader's view of QQQ being above breakeven, ideally above the short strike, at expiration.

## Execution Pricing Model

Backtest execution pricing must not always assume natural ask/bid fills, because frequent spread trading can lose its edge to bid/ask.

Current model:

```text
long_mid = (long_bid + long_ask) / 2
short_mid = (short_bid + short_ask) / 2

long_fill = long_mid + (long_ask - long_bid) * fill_slippage
short_fill = short_mid - (short_ask - short_bid) * fill_slippage
```

Parameter:

- `Fill Slippage`

Meaning:

- `0.00` = pure mid fill
- `0.10` = mid plus 10% of each leg's bid/ask spread in the unfavorable direction
- `0.50` = natural ask/bid fill

Working assumption:

- For high-liquidity QQQ vertical spreads, mid or near-mid fills are plausible but must be tested.
- Backtests should include sensitivity runs at `0`, `0.10`, `0.25`, and `0.50`.

## Position Sizing and Capital Utilization

For debit spreads, capital utilization is also maximum loss exposure. It must be a portfolio-level cap across all active spreads, not a fresh budget for every new entry.

Example:

- `Capital Utilization = 20%`
- Account equity = $100,000
- All currently open positions together may risk about $20,000 maximum loss.

This is very different from buying stock with 20% of capital. A debit spread can expire worthless, so the deployed debit can go to zero.

Important risk note:

- `Max Open Positions` limits the number of active spread slices.
- `Open Interval` controls how often a new slice can be opened.
- `Capital Utilization` limits total active max loss. New entries should use only the remaining risk budget after existing open spread risk is counted.
- Default ladder for 40-DTE vertical spreads: open every 10 days, allow up to 4 active positions, and cap total active risk at 30% of current account equity.
- High utilization such as 70%-80% can produce huge gains in favorable runs but can also destroy the account after consecutive full-loss cycles.
- Even 20%-30% is aggressive for natural-expiration debit spreads.
- Long-term testing must include drawdown, not only final return.

Need to add:

- Max drawdown
- Benchmark vs QQQ buy-and-hold
- Slippage sensitivity table
- Distribution of full win / partial win / partial loss / full loss
- Consecutive loss stress test

## Probability / EV Framework

For a 700/720 bull call spread with net debit 11.55:

- Max loss: $1,155
- Max profit: $845
- Breakeven: 711.55

If final QQQ price is uniformly distributed from 690 to 730:

- Ordinary profit probability is about 46.1%.
- Expected value is about -$155 per contract.
- Value-weighted profit share is about 39.8%.

If final distribution is:

- Below 700: 30%
- Between 700 and 720: 20%, uniformly distributed
- Above 720: 50%

Then approximate result:

- Weighted profit: about $458
- Weighted loss: about $413
- EV: about +$45 per contract
- Value-weighted win share: about 52.6%

This shows the strategy is only attractive if the trader's probability distribution is more bullish than the market-implied pricing.

## UI / UX Direction

The app should feel like a trading and research workstation:

- Dense layout
- Minimize decorative whitespace aggressively
- More room for useful data
- Larger fonts relative to their containers
- High-contrast labels and numbers
- Sidebar navigation must be compact: less vertical padding, larger text, brighter text color
- Parameter panels must favor data density: reduced padding/gaps, larger readable labels, stronger contrast
- Results and trade logs must keep column headers visible when scrolling
- Bilingual Chinese/English UI
- Default language: English
- User can switch language anytime
- Language preference persists in local storage

Hard UI rule:

- Do not use marketing-style whitespace in the working app.
- Do not make labels tiny gray text on dark backgrounds.
- If a screen is for trading, backtesting, or option-chain inspection, prioritize readable dense information over decorative spacing.
- When choosing between "pretty spacious" and "more useful data visible", choose more useful data visible.
- Future page design must default to compact workstation layout, not loose dashboard layout.
- Form controls should use label + field on the same row whenever width allows. Do not let labels waste a whole row while the right side is empty.
- Inputs, selects, and numeric fields should be sized to the actual data they collect. Do not stretch every field to full-card width by default.
- Parameter panels should use compact grids with 3-4 columns on desktop when practical, while preserving readability.
- Vertical spacing between form rows should be tight. A user should see more controls and results before scrolling.
- Wide screens must be used for meaningful side-by-side content, such as sleeves, strategy parameters, attribution, and trade/result panels.
- This compact style is a project skill/rule for all future BRStock pages unless a page has a specific reason to be more spacious.

Documentation rule:

- After a successful product or backtest behavior change, update this idea document in the same session whenever practical.
- Especially document changes to assumptions, sizing, execution price, rebalance behavior, reporting fields, and UI rules.
- If a code change can alter historical backtest results, write down why the result may differ from previous runs.

Recent UI decisions:

- Added English/Chinese language switch.
- Improved form label contrast.
- Increased label and input readability.
- Reduced excessive padding and vertical whitespace.
- Changed backtest forms to compact label + field rows.
- Changed vertical spread parameters to a denser 4-column desktop grid.
- Added custom backtest start/end dates for isolating specific historical periods.
- Added portfolio-level quarterly rebalance as the default for Core ETF + Options portfolios.
- Added underlying price overlay to performance charts for comparing option strategy behavior against the tested stock/ETF.
- Fixed portfolio option ticker behavior: Options Sleeve ticker now starts from the top-level ticker but remains independently configurable after user edits.
- Dashboard watchlist must never render as an empty black area. If a user watchlist is empty, show the default market symbols such as QQQ, VOO, TSLA, NVDA, AAPL, MSFT, AMZN, META, and GOOGL.
- Watchlist add/remove actions must use authenticated API helpers and the correct `/api/stocks/watchlist/{ticker}` route. Do not use raw unauthenticated `fetch` for protected user actions.
- Sidebar navigation font enlarged and spacing reduced.
- Summary/stat labels brightened and enlarged.
- Added Synthetic Chain page for model inspection.
- Added Schwab-vs-synthetic chain calibration on the Synthetic Chain page. The system now compares current Schwab option-chain snapshots against generated contracts, filters low-quality quotes, reports before/after error, and saves compact bucketed correction factors instead of storing full historical option chains.
- OptionSynth now applies saved calibration factors by symbol, option type, DTE bucket, and delta bucket when generating synthetic chains for inspection and backtesting. Backtest results may differ from older runs because synthetic mid prices, bid/ask spreads, IV, and delta can now be corrected toward observed Schwab market data.

## High-Priority Future Features

### Priority 1

Options chain analysis:

- IV
- Greeks
- Volume
- Open interest
- Put/call ratio
- IV heatmap

Position cost alerts:

- User enters cost basis.
- System calculates distance to target and stop levels.
- Alerts for important thresholds.

Real-time news and sentiment:

- Earnings
- M&A
- Financing
- Major announcements
- AI sentiment scoring

Multi-stock comparison:

- Compare peers in the same sector.
- Show price trend, relative strength, volume, and indicators side by side.

### Priority 2

Capital flow analysis:

- Block trades
- Margin financing data
- Institutional accumulation/distribution signals

Options Greeks calculator:

- Delta
- Gamma
- Theta
- Vega

Key level detection:

- Support and resistance
- Prior highs/lows
- Fibonacci levels
- Round-number levels

Strategy performance ranking:

- Top strategies by return
- Win rate
- Max drawdown
- Risk-adjusted return

Intraday volume-price analysis:

- 5-minute and 15-minute abnormal volume alerts

### Priority 3

Financial comparison:

- PE
- PB
- ROE
- Cash flow
- Peer comparison

Options strategy templates:

- Straddle
- Strangle
- Iron condor
- Vertical spreads
- Calendar spreads

Risk management panel:

- Max loss per stock
- Portfolio-level risk score
- Concentration risk

AI timing signals:

- Technicals plus sentiment
- Golden cross / death cross upgrades
- Breakout and reversal signals

Intraday anomaly alerts:

- Limit up/down
- Volume expansion
- Moving average breakout

## Moomoo Real-Time Options Notes

When Moomoo verification code is sent and connection succeeds, the user should receive clear positive feedback.

When connection fails:

- Do not keep retrying endlessly.
- Show a clear status.
- Ask for user action only when needed.

## Watchlist Interaction Rules

The dashboard watchlist is user-controlled workspace state, not a decorative feed.

- Adding a stock must not bounce a logged-in user back to login.
- The top Add Stock button must call the authenticated watchlist add flow, not the auth modal, when a token exists.
- Watchlist add/remove actions must use authenticated API helpers and the `/api/stocks/watchlist/{ticker}` route.
- Adding a stock should feel fast: persist the ticker first, render it immediately, then fetch/refresh only that ticker's data instead of blocking on a full watchlist refresh.
- While a newly added ticker is fetching data, render a real card with the ticker and a clear "Loading market data..." state. Do not show a vague blank skeleton that feels broken.
- Re-adding a ticker should reuse local cached market data when it is still fresh. Deleting from watchlist must not imply deleting downloaded price history.
- Default market-data freshness window is 72 hours so weekend re-adds do not trigger unnecessary yfinance downloads.
- Users must be able to remove any added stock from the dashboard.
- Logged-in users with an empty watchlist should see a clear empty state, not an automatic default list that makes deletion appear broken.
- Users must be able to control card order/position. Persist order server-side so refreshes keep the same layout.
- DOM ids for repeated add-stock inputs must be unique; duplicate ids cause the wrong input/button path to fire.

## Open Questions

- How close is the synthetic IV surface to real QQQ option chains?
- Does the synthetic chain overprice or underprice ATM vertical spreads?
- How sensitive are strategy results to fill slippage?
- What is the max drawdown of bull call spread backtests?
- Does the strategy still outperform QQQ buy-and-hold after realistic execution assumptions?
- Should position sizing separate:
  - max risk per trade
  - target capital utilization
  - portfolio-level exposure cap

  ## 论坛 Forum
  - Write a basic forum page for users to exchange ideas and share strategies.
  - Forum allow text discussion only for now.
