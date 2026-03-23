# Data Sources

This project uses three external data sources. Understanding what each one provides —
and what it *cannot* provide — is essential for interpreting results correctly.

---

## 1. SEC EDGAR (Primary Financial Data)

### What is SEC EDGAR?

**EDGAR** = Electronic Data Gathering, Analysis, and Retrieval system.
Run by the US Securities and Exchange Commission (SEC). Every US-listed public company
must file their financial reports here. It is the **authoritative source** for all
company financial data — not Bloomberg, not Yahoo Finance, not any aggregator.

### Why we use it (not a data vendor)

| Vendor Data | SEC EDGAR Direct |
|-------------|-----------------|
| May lag filings by days | Real-time (filed today, available today) |
| May normalize/adjust numbers | Raw, as-filed numbers only |
| Requires paid subscription | Free, public API |
| May have survivorship bias | Complete historical record |
| Opaque methodology | Full audit trail back to each filing |

Our rule: **every number must trace back to a primary filing**. EDGAR makes that possible.

### The EDGAR API endpoints we use

```
https://data.sec.gov/submissions/CIK{cik}.json
  → Returns a company's full filing history
  → Used in Phase 2

https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json
  → Returns ALL XBRL-tagged financial data for a company
  → Used in Phase 3 (the main data extraction endpoint)

https://www.sec.gov/files/company_tickers.json
  → Maps ticker symbols (NVDA, AAPL) to CIK numbers
  → Used in Phase 2 (ticker lookup)
```

**Rate limit:** SEC enforces 10 requests/second. We add a 0.1s delay between calls.
**User-Agent required:** SEC blocks requests without a proper User-Agent header.
See `config.py → SEC_USER_AGENT`.

---

## 2. XBRL (The Data Format Inside SEC Filings)

### What is XBRL?

**XBRL** = eXtensible Business Reporting Language.
It is the **tagging system** that makes financial data machine-readable.

When a company files a 10-K, the financial statements are tagged using XBRL so that
computers can reliably extract specific numbers. Without XBRL, you'd be trying to
parse PDFs — a nightmare.

### How XBRL tagging works

Every financial line item gets a standardized name (called a "concept" or "tag"):

```
"Revenue" in a 10-K filing might be tagged as:
  us-gaap:Revenues
  us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax
  us-gaap:SalesRevenueNet

→ These all mean "total revenue" but different companies use different tags.
→ Our code tries all variations. See REVENUE_KEYS in src/dcf_calculator.py.
```

### US-GAAP vs IFRS

There are two main XBRL taxonomies (sets of tag names):

| Taxonomy | Used by | Tags look like |
|----------|---------|----------------|
| **US-GAAP** | US-listed companies (10-K, 10-Q) | `us-gaap:Revenues` |
| **IFRS-full** | Foreign filers (20-F) | `ifrs-full:Revenue` |

**AZN (AstraZeneca)** files a 20-F using IFRS. Our code auto-detects the taxonomy:

```python
# src/xbrl_parser.py - taxonomy detection
if "ifrs-full" in xbrl_data.get("facts", {}):
    taxonomy = "ifrs-full"
else:
    taxonomy = "us-gaap"
```

### What XBRL data gives us

From `companyfacts/CIK{cik}.json` we extract:

- **Income Statement:** Revenue, EBIT, Net Income, Tax, Interest Expense
- **Cash Flow Statement:** Operating Cash Flow (OCF), CapEx, D&A
- **Balance Sheet:** Cash, Debt, Total Assets, Equity, Shares Outstanding
- **Per-share data:** EPS (diluted), shares outstanding over time

### What XBRL does NOT give us

- **Live stock price** → That comes from Alpaca (Phase 8)
- **Market capitalization** → Requires live price × shares (Alpaca + XBRL combined)
- **Beta** → Requires historical price return data (Alpaca Phase 8)
- **Forward earnings estimates** → Not in XBRL (analyst estimates, not SEC data)

### Filing types

| Form | Meaning | Period |
|------|---------|--------|
| **10-K** | Annual report (US companies) | Full year |
| **10-Q** | Quarterly report (US companies) | 3 months |
| **20-F** | Annual report (foreign private issuers) | Full year |
| **6-K** | Quarterly/semi-annual (foreign companies) | Varies |

**Important:** We only use **annual** filings (10-K / 20-F) for the DCF model.
Quarterly data has a different time horizon and mixes with annual data silently —
a known source of bugs. See `config.ANNUAL_FORM_TYPES`.

### The CIK number

**CIK** = Central Index Key. The unique identifier SEC uses for every company.
It never changes, even if a company changes its ticker or name.

```
NVDA → CIK 0001045810
AAPL → CIK 0000320193
MSFT → CIK 0000789019
AZN  → CIK 0001816697
```

Our pipeline converts tickers to CIKs first, then uses CIKs for all subsequent calls.

---

## 3. Alpaca Markets (Live Market Data)

### What is Alpaca?

Alpaca is a brokerage and market data provider with a free-tier API. We use it
**exclusively for market data** (not for trading).

Website: https://alpaca.markets
Free tier: IEX feed, ~1-minute delay, 200 requests/minute

### Why Alpaca and not Yahoo Finance or Bloomberg?

| Source | Problem |
|--------|---------|
| Yahoo Finance | Unofficial API, frequently breaks, no SLA |
| Bloomberg Terminal | $25,000/year, not accessible |
| Alpaca Free Tier | Free, official API, reliable, IEX feed covers all US equities |

### What we use Alpaca for

#### 1. Current Stock Price (`get_latest_price`)

```
GET https://data.alpaca.markets/v2/stocks/{symbol}/snapshot

Response contains:
  latestTrade.p   → Most recent trade price
  latestQuote.ap  → Current ask price
  latestQuote.bp  → Current bid price
  dailyBar.c      → Today's closing price
  dailyBar.v      → Today's volume
```

We return the `latestTrade.p` (most recent actual trade). This is used to:
- Calculate premium/discount vs DCF fair value: `(fair_value - price) / price × 100`
- Display in the email report and console output

#### 2. Historical Daily Bars (`get_historical_bars`)

```
GET https://data.alpaca.markets/v2/stocks/{symbol}/bars
  ?timeframe=1Day
  &adjustment=split   ← split-adjusted prices (critical for accuracy)
  &limit=500

Each bar: { t, o, h, l, c, v, vw }
  t  = timestamp (ISO 8601)
  o  = open price
  h  = high price
  l  = low price
  c  = close price
  v  = volume
  vw = volume-weighted average price (VWAP)
```

We fetch `lookback_days` of daily bars and use only the closing price (`c`) for
beta calculation.

**Why `adjustment=split`?** When a company does a stock split (e.g., NVDA did a
10:1 split in June 2024), the share price drops by 10×. Without split adjustment,
a "price drop" of 90% in one day would completely distort the beta calculation.

#### 3. Beta Calculation (`calculate_beta`)

Beta is computed from these historical bars. Full explanation in
[beta_and_capm.md](beta_and_capm.md).

### What Alpaca does NOT provide (free tier)

- **Shares outstanding** → Use SEC XBRL
- **Market capitalization** → Calculate from price × shares
- **Options data** → Paid tier only
- **Fundamental data** (EPS, P/E ratios) → Use SEC XBRL
- **International stocks** → US equities only (but foreign ADRs like AZN work fine)

### Authentication

Alpaca uses two header-based API keys:
```
APCA-API-KEY-ID: your_key
APCA-API-SECRET-KEY: your_secret
```

These are stored in `.env` (never committed to git) and loaded by `config.py` via
`python-dotenv`. See `.env.example` if you need to set up your own keys.

### Data URL vs Paper Trading URL

```
Trading orders: https://paper-api.alpaca.markets/v2/   ← DO NOT use for data
Market data:    https://data.alpaca.markets/v2/          ← Use this
```

The paper trading API is for placing test orders. The data API is a completely
different service. Using the wrong URL returns 404 or empty results.
Our `config.ALPACA_DATA_URL` always points to `data.alpaca.markets`.

---

## Data Hierarchy (Priority Order)

When the same data is available from multiple sources, we follow this hierarchy:

```
1. SEC EDGAR XBRL (most authoritative — legal filing)
2. Alpaca Markets (market price data — real-time)
3. config.py constants (fallbacks — e.g., industry beta table)
```

We NEVER synthesize or estimate data from one source to fill gaps in another.
If a value is unavailable from its authoritative source, we return `None` and
log a warning. The pipeline continues without that value.
