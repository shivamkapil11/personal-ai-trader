# Stock Research Playbook

## Purpose

This playbook is the working framework for analyzing any stock as one of four labels:

- `Swing Trade`
- `Long-Term Investment`
- `Watchlist`
- `Avoid for now`

The goal is decision support, not prediction theater. Each conclusion must separate:

- confirmed fact
- recent but not live data
- inference
- assumption due to missing data

## Source Hierarchy

Use sources in this order whenever available:

1. Exchange and company primary sources
   - NSE announcements
   - BSE announcements
   - annual reports
   - investor presentations
   - concalls
   - shareholding disclosures
   - insider / promoter filings
2. Market and broker data
   - Kite / broker data for recent or live price and volume
   - exchange bhavcopy or chart data
3. Screening and secondary research
   - Trendlyne
   - Ratestar
   - Chartlink
   - Investstar
4. Credible public research
   - industry reports
   - management interviews
   - established financial publications
5. Framework sources
   - the uploaded books and training material

If live data is unavailable, state that clearly and continue with the best recent confirmed data.

## Decision Logic

### `Swing Trade`

Choose this when:

- price structure is constructive now
- momentum is positive or improving
- support, stop-loss, and invalidation are clear
- reward-to-risk is attractive, ideally `2:1` or better
- there is a near-term trigger such as breakout, reversal, earnings, sector strength, or strong volume confirmation

### `Long-Term Investment`

Choose this when:

- business quality is strong
- the growth runway is real and measurable
- management quality and capital allocation are acceptable
- balance sheet and cash flow quality are solid
- valuation is reasonable relative to growth and peer quality
- the thesis survives short-term volatility

### `Watchlist`

Choose this when:

- the company is interesting but the setup is not ready
- valuation is stretched despite good business quality
- technicals are mixed and offer no clean entry
- a major result, regulation, or capital allocation event needs to play out first

### `Avoid for now`

Choose this when:

- fundamentals are deteriorating
- governance or accounting concerns exist
- technical trend is weak with no edge
- downside is hard to define
- the story depends more on narrative than evidence

## Scoring Model

### Swing Score (`100`)

| Factor | Weight | What to Look For |
| --- | ---: | --- |
| Trend and structure | 25 | higher highs, higher lows, base formation, breakout quality |
| Momentum | 20 | RSI, MACD, stochastic, momentum persistence, divergence |
| Risk-reward clarity | 20 | clean stop, nearby support, target visibility |
| Volume behavior | 15 | accumulation, breakout volume, drying supply on pullbacks |
| Trigger / catalyst | 10 | news, result, sector move, pattern completion |
| Fundamental sanity check | 10 | avoid weak balance sheets or obvious landmines |

Interpretation:

- `75+`: strong swing candidate
- `60-74`: conditional swing / watchlist
- `<60`: not a swing setup

### Long-Term Score (`100`)

| Factor | Weight | What to Look For |
| --- | ---: | --- |
| Business quality | 25 | moat, pricing power, resilience, repeatability |
| Growth runway | 20 | reinvestment opportunity, market size, product pipeline |
| Financial quality | 15 | margins, ROE, ROCE, leverage, cash conversion |
| Management quality | 15 | integrity, capital allocation, execution track record |
| Valuation comfort | 15 | multiple vs growth, peers, history, downside support |
| Sector and competition | 10 | industry structure, tailwinds, disruption risk |

Interpretation:

- `75+`: long-term investable
- `60-74`: watchlist / partial thesis
- `<60`: avoid for long-term capital

## Technical Checklist

Review on at least three timeframes:

- short term: daily
- medium term: weekly
- long term: monthly when relevant

Indicators to cover:

- RSI
- MACD
- Bollinger Bands
- Stochastic
- EMA / SMA alignment
- volume trend
- breakout / breakdown levels
- support / resistance
- relative strength vs index / sector
- Elliott Wave only if the count is reasonably clear and non-forced

Momentum strength score:

- `8-10`: powerful trend with confirmation
- `5-7`: mixed but improving
- `1-4`: weak or failing

## Fundamental Checklist

Mandatory items:

- revenue growth
- profit growth
- EBITDA / operating margin direction
- ROE / ROCE
- debt and interest coverage
- free cash flow quality
- promoter holding trend
- institutional holding trend, if available
- valuation metrics
- peer comparison
- direction of change: improving, stable, or weakening

## Qualitative Checklist

Test the thesis on these questions:

- Is the business easy to understand?
- Does it have a durable advantage?
- Can management allocate capital well?
- Is growth dependent on one cycle or one customer?
- Is the sector growing structurally or only cyclically?
- What can break the thesis?
- Is the market already pricing in perfection?

## Risk Framework

Every stock must include:

- business risk
- valuation risk
- technical risk
- sector risk
- event risk
- liquidity risk
- downside scenario
- risk rating from `1` to `10`

No buy-style conclusion should be given without a clear invalidation condition.

## Book-Derived Principles

These are the ideas extracted from the uploaded reading set that should shape conclusions:

| Source | Principle Used in Analysis | Practical Effect |
| --- | --- | --- |
| `The Intelligent Investor` | distinguish investment from speculation; demand margin of safety | keep long-term labels for quality businesses at sensible risk-adjusted prices |
| `One Up on Wall Street` | understand the business simply; find growth before Wall Street fully prices it | reward understandable companies with observable ground-level growth |
| `Common Stocks and Uncommon Profits` | judge management quality, reinvestment ability, and long runway | emphasize scuttlebutt-style qualitative checks and capital allocation |
| `A Random Walk Down Wall Street` | stay skeptical of story stocks and false precision; benchmark against passive alternatives | penalize weak edge and overconfident forecasts |
| `The Little Book of Common Sense Investing` | compare all stock-picking against low-cost passive compounding | raise the hurdle for long-term stock selection |
| `Reminiscences of a Stock Operator` | respect price action, cut losses, and do not average into weak trades | enforce stop-loss discipline and wait for confirmation |
| `Japanese Candlestick Charting Techniques` | candles matter only in context | use candlestick signals as confirmation, not standalone reasons |
| `Technical Analysis of the Financial Markets` | trend, support/resistance, momentum, and volume should agree | require multi-indicator confirmation for swing trades |
| `Mastering the Trade` | define the setup, trigger, stop, target, and sizing before entering | treat swing setups as structured risk propositions |
| `How to Swing Trade` | routine, money management, and execution discipline matter as much as pattern recognition | avoid recommending trades without defined plan quality |

Note:

- some PDFs were directly text-extractable and some were not cleanly extractable in this environment
- where extraction was limited, use only broad, well-established principles from those works unless a later OCR pass confirms more specific detail

## Decision Tree

1. Check if recent price data is available.
2. Check if a primary-source business update exists.
3. Score swing setup.
4. Score long-term thesis.
5. Compare both scores with the risk profile.
6. Assign the strongest valid label.
7. State what would change the label.

## Default Output Template

### 1. Summary Dashboard

Include:

- company name
- symbol
- current price
- market cap
- sector
- 52-week high / low
- basic trend
- final label
- conviction score

### 2. Swing vs Long-Term Decision

Answer:

- better suited for swing, long-term, watchlist, or avoid
- 3 to 5 reasons why

### 3. Technical Analysis

Include:

- trend by timeframe
- RSI
- MACD
- Bollinger Bands
- Stochastic
- EMA / SMA alignment
- support and resistance
- volume behavior
- breakout / reversal / consolidation structure
- Elliott Wave view only if useful
- momentum strength score

### 4. Fundamental Analysis

Include:

- growth
- profitability
- returns on capital
- debt and cash flow
- holdings trend
- valuation
- peer comparison
- improving / stable / weakening label

### 5. Business / Management / Sector View

Include:

- business model
- moat
- management quality
- future runway
- sector outlook
- key opportunities
- key structural concerns

### 6. News / Announcements / Insider Activity

Include:

- recent exchange announcements
- management commentary
- promoter / insider activity
- important sentiment or trigger events

### 7. Risk and Conviction

Include:

- risk list
- risk rating
- conviction score
- confidence level
- what supports conviction
- what would reduce conviction

### 8. Return Scenarios

Include:

- swing return potential
- long-term return potential over `1-3 years`
- bull case
- base case
- bear case
- total return range
- risk-reward ratio

### 9. Final Verdict

Always end with:

- final label
- one-line thesis
- best action now
- what to monitor next

### 10. Sources Used

List the exact sources used and mark each as:

- `Primary`
- `Secondary`
- `Price / Technical`
- `Inference`

## Reporting Rules

- never present inferred values as facts
- call out conflicts between sources
- prefer fewer strong points over many weak ones
- separate setup quality from business quality
- avoid giving a long-term label just because a stock is popular
- avoid giving a swing label if the stop-loss is vague
- if both swing and long-term are weak, choose `Watchlist` or `Avoid`

## What to Monitor for Any Stock

- results and guidance
- volume expansion or exhaustion
- delivery data or order book when relevant
- margin trend
- promoter activity
- debt or dilution
- sector leadership changes
- major regulatory announcements
