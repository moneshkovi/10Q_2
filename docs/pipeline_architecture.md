# Pipeline Architecture

How the 9 phases connect, what each source file does, and why the code is structured
the way it is.

---

## The Full Data Flow

```
User command: python main.py NVDA AAPL
                        │
                        ▼
            main.py → process_ticker()
           ┌────────────────────────────────────────────┐
           │  Called once per ticker. Returns result{} │
           └────────────────────────────────────────────┘
                        │
         ┌──────────────┼────────────────────────────────────┐
         │              │                                    │
         ▼              ▼                                    ▼
    Phase 1-2       Phase 3                             Phase 4
  SEC lookup      XBRL extract                        Validation
  sec_client.py   xbrl_parser.py                     validator.py
                                                  data_reconciler.py
         │              │                                    │
         └──────────────┼────────────────────────────────────┘
                        │
         ┌──────────────┼────────────────────────────────────┐
         │              │                                    │
         ▼              ▼                                    ▼
    Phase 5         Phase 6                             Phase 7
  XML + CSV       CLI progress                         DCF model
  xml_builder.py  cli_enhancements.py                dcf_calculator.py
  csv_builder.py
         │              │                                    │
         └──────────────┼────────────────────────────────────┘
                        │
         ┌──────────────┴────────────┐
         │                           │
         ▼                           ▼
    Phase 8                      Phase 9
  Alpaca market data           Email report
  alpaca_client.py             email_reporter.py
```

---

## Phase-by-Phase Breakdown

### Phase 1: Configuration & Setup
**Files:** `config.py`, directory creation in `main.py`

What happens:
- `config.py` loads `.env` via `python-dotenv`
- All API keys, URLs, DCF parameters loaded into constants
- Output directories created: `~/sec_filing_parser/data/{TICKER}/`
- Logging configured to file + console

**Why config.py?** Centralising all constants prevents magic numbers scattered
across files. If SEC changes an API URL, you change it in one place.

---

### Phase 2: SEC Company Lookup
**Files:** `src/sec_client.py`

What happens:
1. `get_cik_from_ticker("NVDA")` → fetch `company_tickers.json`, find CIK `0001045810`
2. `get_filings(cik, ["10-K", "20-F"], years=5)` → filing metadata list
3. Check `is_xbrl` flag on each filing

Output: `result["cik"]`, `result["filings_found"]`

**Key design:** All SEC API calls go through `SECClient._session` (a `requests.Session`)
with retry logic (3 attempts, exponential backoff) and rate limiting (0.1s between calls).
This prevents SEC bot detection and handles transient 429 / 503 errors.

---

### Phase 3: XBRL Financial Data Extraction
**Files:** `src/xbrl_parser.py`

What happens:
1. Fetch `https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json`
2. Detect taxonomy: `us-gaap` vs `ifrs-full`
3. Extract all metric values across all filings and periods
4. For each metric: store value, period end date, form type, confidence score
5. Compute year-over-year changes
6. Save `{TICKER}_xbrl_metrics.json`

Output: `result["metrics_extracted"]` (typically 200-350 metrics)

**Key design choice:** Extract ALL metrics upfront into a JSON file, then later phases
read from that. This means the expensive SEC API call happens once; all downstream
processing is local.

---

### Phase 4: Data Validation
**Files:** `src/validator.py`, `src/data_reconciler.py`

What happens:
- Cross-check numbers for internal consistency:
  - Does `NetIncome = PreTaxIncome - IncomeTaxExpense`?
  - Do assets balance? (Assets = Liabilities + Equity)
  - Are margins in reasonable ranges? (Gross margin 0-100%, FCF margin -50% to 80%)
- Flag anomalies: sudden >50% YoY swings, negative revenue, near-zero shares
- Assign quality score per metric (0-100)

Output: `result["quality_score"]`, `result["critical_issues"]`

**Why validate?** XBRL data can contain errors. Companies sometimes file restated
numbers under the same period label. A downstream DCF that blindly uses bad data
produces a completely wrong fair value. Validation catches this early.

---

### Phase 5: Output Generation
**Files:** `src/xml_builder.py`, `src/csv_builder.py`

What happens:
- **XML:** Full filing data with audit trail — every number traced back to its source
  filing, date, and XBRL tag. Designed for archival and programmatic consumption.
- **CSV (4 files):**
  - `{TICKER}_calculated_metrics.csv` — ratio calculations (margins, growth, ROIC)
  - `{TICKER}_extracted_metrics.csv` — raw XBRL values by period
  - `{TICKER}_yoy_analysis.csv` — year-over-year changes
  - `{TICKER}_summary.csv` — one-page executive summary

Output: 5 files per ticker in `~/sec_filing_parser/data/{TICKER}/parsed/`

---

### Phase 6: CLI Enhancements
**Files:** `src/cli_enhancements.py`

What it provides:
- Color-coded terminal output (green = good, red = bad, yellow = warning)
- Progress bars during long operations
- Multi-ticker comparison tables at the end
- Error formatting and summary statistics

**Why separate?** CLI presentation has nothing to do with financial logic.
Separating it keeps `main.py` clean and makes it easy to change the UI
without touching any financial calculations.

---

### Phase 7: DCF Valuation
**Files:** `src/dcf_calculator.py`

What happens:
1. Read `xbrl_metrics` dict (from Phase 3 JSON)
2. Extract historical financials (last 5 annual filings)
3. Compute historical FCFF using OCF method (preferred) or EBIT method (fallback)
4. Calculate WACC (using beta from Phase 8 if available, else sector lookup)
5. Forecast 5 years of FCF with tapering growth
6. Compute terminal value (Gordon + Exit multiple, averaged)
7. Discount all cash flows → Enterprise Value
8. Equity bridge (+ cash, - debt, ÷ shares) → Fair Value per Share
9. Run sensitivity analysis (5×5 WACC/growth matrix)
10. Run Bull/Base/Bear scenarios
11. Save 4 DCF output files

Output: `result["dcf_fair_value"]`, `result["dcf_wacc"]`, 4 CSV/JSON files

**Why Phase 7 comes after Phase 5?** The CSV export (Phase 5) saves the raw metrics.
DCF (Phase 7) reads from those same metrics but adds a separate valuation layer.
Keeping them separate means you can run the CSV export without running the DCF,
and you can re-run the DCF with different assumptions without re-fetching data.

---

### Phase 8: Alpaca Market Data
**Files:** `src/alpaca_client.py`

What happens:
1. `AlpacaClient.calculate_beta(ticker)` → 252 daily bars for ticker + SPY → OLS beta
2. `AlpacaClient.get_latest_price(ticker)` → snapshot → latest trade price
3. If DCF fair value exists:
   `premium_pct = (fair_value - price) / price × 100`

Output: `result["current_price"]`, `result["computed_beta"]`, `result["dcf_premium_pct"]`

**Why Phase 8 comes after Phase 7?** The computed beta is passed back into Phase 7
as `beta_override`. In practice, AlpacaClient is instantiated before Phase 7 and beta
is computed first, then passed to `dcf_calculator.run_dcf(beta_override=computed_beta)`.

**Graceful degradation:** If Alpaca keys are missing or the API fails, `enabled=False`
and all methods return `None`. The pipeline continues — you just don't get the market
data enrichment.

---

### Phase 9: Email Reporting
**Files:** `src/email_reporter.py`

What happens:
- After ALL tickers are processed, `EmailReporter.send_dcf_report(all_results, ...)` is called
- Builds HTML table: Ticker | Fair Value | Current Price | Premium | WACC | Beta | Quality
- Attaches per-ticker `_calculated_metrics.csv` (skips if > 1MB or not found)
- Sends via Gmail SMTP (STARTTLS, port 587)

For single-ticker failures during pipeline: `send_error_alert(ticker, error)` is called inline.

**Graceful degradation:** If email credentials are missing, `enabled=False` and nothing
is sent. The pipeline output to console and files is unaffected.

---

## File Map

| File | Lines | Purpose |
|------|-------|---------|
| `config.py` | 195 | All constants: URLs, DCF params, API keys |
| `main.py` | ~700 | CLI entry point, pipeline orchestration |
| `src/sec_client.py` | 420 | SEC EDGAR API: CIK lookup, filing metadata |
| `src/xbrl_parser.py` | 419 | XBRL data extraction from SEC API |
| `src/validator.py` | 430 | Financial data validation rules |
| `src/data_reconciler.py` | 310 | Validation orchestration |
| `src/xml_builder.py` | 450 | XML output with full audit trail |
| `src/csv_builder.py` | 400 | CSV export (4 files per ticker) |
| `src/cli_enhancements.py` | 324 | Terminal UI: colors, progress, tables |
| `src/dcf_calculator.py` | 850 | DCF valuation model |
| `src/alpaca_client.py` | ~190 | Live price + OLS beta from Alpaca API |
| `src/email_reporter.py` | ~200 | Gmail SMTP report + alerts |

---

## The `result{}` Dictionary

`process_ticker()` returns one dict. Every phase adds its own keys:

```python
result = {
    # Phase 2 (SEC)
    "success": True,
    "cik": "0001045810",
    "filings_found": 20,
    "xbrl_available": True,
    "errors": [],

    # Phase 3 (XBRL)
    "metrics_extracted": 317,
    "xbrl_data": {...},

    # Phase 4 (Validation)
    "quality_score": 85,
    "critical_issues": 0,

    # Phase 5 (Output)
    "xml_generated": True,
    "csv_generated": True,

    # Phase 7 (DCF)
    "dcf_generated": True,
    "dcf_fair_value": 151.91,
    "dcf_wacc": 0.1323,

    # Phase 8 (Alpaca)
    "current_price": 174.14,
    "computed_beta": 1.68,
    "dcf_premium_pct": -12.8,
}
```

This dict is also what `EmailReporter.send_dcf_report(all_results)` consumes to
build the HTML email table.

---

## Testing Strategy

```
tests/
├── test_sec_client.py         20 tests — mocked SEC HTTP responses
├── test_xbrl_parser.py        19 tests — uses REAL SEC API (integration)
├── test_validator.py          22 tests — synthetic metric data
├── test_xml_builder.py        17 tests — file system + XML structure
├── test_cli_enhancements.py   17 tests — output formatting
├── test_dcf_calculator.py     26 tests — synthetic financial inputs
├── test_alpaca_client.py      13 tests — mocked Alpaca HTTP responses
└── test_email_reporter.py      8 tests — mocked smtplib
```

**Total: 161 tests**

Rule: No test should make a real network call except `test_xbrl_parser.py`
(which is an explicit integration test). All other tests mock the network layer.

**Why mock?**
- Speed: mocked tests run in milliseconds; real API calls take 1-5 seconds each
- Reliability: tests don't fail due to network issues or API rate limits
- Determinism: the mock always returns the same response
- No side effects: no emails sent, no real API keys consumed during CI
