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

## 4. OpenFIGI (Security Identifier Enrichment)

### What is OpenFIGI?

**OpenFIGI** = Open Financial Instrument Global Identifier. A free, public API
maintained by Bloomberg to map tickers to standardised security identifiers.

Website: https://www.openfigi.com
Free tier: API key required, returns FIGI fields only (CUSIP is premium-only).

### What identifiers we fetch

#### FIGI (Financial Instrument Global Identifier)
A 12-character alphanumeric identifier unique to every financial instrument globally.
Example: NVDA → `BBG000BBJQV0`

```
Type:       Composite FIGI (covers all exchanges where the instrument trades)
Source:     OpenFIGI /v3/mapping endpoint
XBRL tag:   N/A (not in SEC filings)
```

#### CUSIP (Committee on Uniform Securities Identification Procedures)
A 9-character alphanumeric identifier used in North American markets to uniquely
identify securities. Required for settlement and transfer of ownership.
Example: NVDA → `67066G104`

We attempt CUSIP from **three sources in priority order**:
1. **OpenFIGI API** — free tier sometimes includes `cusip` field in the response
2. **SEC XBRL DEI facts** — `dei:SecurityCUSIP` tag in `companyfacts/{CIK}.json`
   (fallback; not all companies report this in their XBRL DEI block)
3. **SEC SC 13G/13D filings** — institutional ownership filings always include the
   CUSIP of the reported security. This is the most reliable source and works for
   US-domestic, FPI (foreign private issuers like STE), and ADR securities.
   See [CUSIP Lookup Process](#cusip-lookup-process) below for details.

### Why these identifiers?

| Use Case | Identifier Needed |
|----------|-------------------|
| Equity research report headers | CUSIP + FIGI |
| Cross-referencing with Bloomberg data | FIGI |
| Regulatory filings and trade settlement | CUSIP |
| Matching securities across data providers | FIGI (universal) |

These are **enrichment data** — non-critical for the DCF valuation, but important
for professional-grade output. If neither source provides a CUSIP, the pipeline
continues without it and logs a non-critical warning.

### How it flows through the pipeline

```python
# Phase 2 in main.py — after CIK lookup
figi  = client.get_figi_from_ticker(ticker)
cusip = client.get_cusip_from_ticker(ticker, cik=cik)

result["figi"]  = figi   # Injected into result{}
result["cusip"] = cusip  # Injected into result{}

# Also passed into metrics_data so it appears in XML and CSV output
metrics_data["cusip"] = cusip
metrics_data["figi"]  = figi
```

### Code location
`src/sec_client.py` — `get_figi_from_ticker()`, `get_cusip_from_ticker()`, `_query_openfigi()`, `_extract_cusip_from_13g()`

---

## 5. CUSIP Lookup Process

### How CUSIP extraction from SC 13G/13D works

SC 13G and SC 13D are institutional ownership filings. When an institution (e.g., Vanguard,
BlackRock) accumulates a significant position in a security, they must file a 13G or 13D
with the SEC. These filings **always include the CUSIP** of the security being reported on.

This makes SC 13G/13D the most reliable public source of CUSIP data on EDGAR — more
reliable than the 10-K/10-Q cover page (which many companies omit) or the XBRL DEI tag
(which most companies don't include).

#### Strategy

```
1. Fetch the company's submission history from EDGAR submissions API
2. Find the most recent SCHEDULE 13G, 13G/A, SC 13D, or SC 13D/A filing
3. Fetch the primary XML/HTM document of that filing
4. Parse CUSIP using three patterns:
   a. <cusipNumber>G8473T100</cusipNumber>  (structured XML)
   b. CUSIP Number(s): 09290D101           (schema text pattern)
   c. G8473T100 (CUSIP Number)             (parenthetical label in HTML)
```

#### Coverage

| Security Type | Works? | Example |
|---------------|--------|---------|
| US-domestic common stock | Yes | BLK → 09290D101 |
| Foreign private issuer (FPI) | Yes | STE (Ireland) → G8473T100 |
| ADR shares | Yes | (G-prefix CUSIP) |
| Multi-class shares | Yes | GOOG (Class C) → 02079K305 |
| Mutual funds / ETFs | **No** | Require N-CEN/N-PORT parsing (see below) |

#### Verified results

| Ticker | Entity | CUSIP | Source |
|--------|--------|-------|--------|
| NVDA | NVIDIA Corp | 67066G104 | SC 13G |
| AAPL | Apple Inc | 037833100 | SC 13G |
| MSFT | Microsoft Corp | 594918104 | SC 13G |
| GOOG | Alphabet Inc (C) | 02079K305 | SC 13G |
| TSLA | Tesla Inc | 88160R101 | SC 13G |
| BLK | BlackRock Inc | 09290D101 | SC 13G |
| STE | STERIS plc (Ireland) | G8473T100 | SC 13G |
| YB | Yuanbao Inc | 987910106 | SC 13G |

#### Limitations

- **Requires institutional ownership**: Very new or micro-cap companies may not have
  any 13G/13D filings yet. In practice, any company in the S&P 500 or Russell 3000
  will have multiple 13G filings.
- **Returns the CUSIP of whichever share class the institution holds**: For multi-class
  companies (GOOG vs GOOGL), the CUSIP returned depends on which class the most recent
  13G filer held.
- **Not available for mutual funds or ETFs**: These don't have 13G/13D filings filed
  *about* them. See the Mutual Fund roadmap below.

---

## 6. Mutual Fund / ETF CUSIP Lookup (Roadmap)

Mutual funds and ETFs cannot be looked up via SC 13G/13D because those filings are
about *stocks held by funds*, not *about the fund itself*.

### What we know

| Fund ticker | Fund family | SEC CIK | Filing types |
|-------------|-------------|---------|--------------|
| DODEX | Dodge & Cox Emerging Markets Stock Fund | 0000029440 | N-CSR, 485BPOS, N-CEN |
| EQTY | Kovitz Core Equity ETF | (not in company_tickers.json) | N-PORT, N-CEN |

### Next steps for mutual fund CUSIP support

1. **N-CEN filings** (Annual Report for Registered Investment Companies):
   - Filed annually by every fund family
   - Contains structured XML with series/class identifiers
   - Maps fund ticker → CUSIP in a machine-readable format
   - Endpoint: `https://www.sec.gov/cgi-bin/browse-edgar?type=N-CEN&CIK={cik}`

2. **N-PORT filings** (Monthly Portfolio Holdings):
   - Filed monthly by every mutual fund/ETF
   - Contains the fund's own identifiers (CUSIP, ISIN, ticker)
   - Also contains CUSIPs of all portfolio holdings

3. **485BPOS filings** (Post-Effective Amendment to Registration):
   - Prospectus updates that sometimes list fund share class CUSIPs
   - Less structured — requires HTML parsing

### Implementation plan

```
Phase 1: Add N-CEN XML parser
  - Fetch N-CEN filing for fund family CIK
  - Parse <seriesId> and <classId> tags
  - Map ticker → CUSIP from structured data

Phase 2: Add ticker → fund family CIK mapping
  - SEC's company_tickers.json does not include mutual fund tickers
  - Use SEC's series/class search or EDGAR full-text search (EFTS)
  - Endpoint: https://efts.sec.gov/LATEST/search-index?q="DODEX"&forms=N-CEN

Phase 3: Integrate into get_cusip_from_ticker as Source 4
```

---

## Data Hierarchy (Priority Order)

When the same data is available from multiple sources, we follow this hierarchy:

```
1. SEC EDGAR XBRL (most authoritative — legal filing)
2. Alpaca Markets (market price data — real-time)
3. OpenFIGI (security identifiers — enrichment only)
4. config.py constants (fallbacks — e.g., industry beta table)
```

We NEVER synthesize or estimate data from one source to fill gaps in another.
If a value is unavailable from its authoritative source, we return `None` and
log a warning. The pipeline continues without that value.
