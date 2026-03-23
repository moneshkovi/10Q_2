# Design Decisions — The "Why" Behind the Code

Every non-obvious choice in this codebase is documented here with its rationale.
Understanding *why* a decision was made is as important as understanding *what* it does.

---

## Financial Design Decisions

### 1. FCFF over FCFE

**Decision:** Use Free Cash Flow to **Firm** (FCFF), not Free Cash Flow to **Equity** (FCFE).

**Difference:**
```
FCFF = Cash available to ALL capital providers (debt + equity)
FCFE = Cash available only to EQUITY holders (FCFF minus debt repayments)
```

**Why FCFF?**
- FCFF pairs naturally with **Enterprise Value** (total firm value), then we subtract debt at the end
- FCFE requires projecting the entire debt repayment schedule — fragile and hard to do from XBRL alone
- Most investment bank DCF models use FCFF + WACC for unlevered DCF
- FCFF is less sensitive to financing assumptions (capital structure doesn't affect FCFF)

**Reference:** JP Morgan Equity Research DCF Training Materials, 2023.

---

### 2. OCF Method Preferred Over EBIT Method

**Decision:** Use `FCFF = OCF - CapEx + Interest*(1-t)` as the first choice.

**Background (The March 2026 Bug):**
When extracting historical balance sheets, quarterly filing dates (e.g., Sept 30, Jun 30)
were appearing inside 10-K filing records in XBRL. This caused `ΔNWC` in the EBIT method
to be computed as a 3-month balance sheet change instead of a full annual change — a
completely silent, large error. GOOG's FCF was wrong by ~$20B as a result.

**Why OCF method avoids this:**
OCF is a single number from the cash flow statement. It inherently covers the full
annual period. NWC changes are already baked in. There's no balance sheet interpolation.

**Lesson:** Always prefer metrics that come directly from a single statement over
metrics assembled from multiple statements, when both options exist.

---

### 3. Median FCF Margin (Not Mean)

**Decision:** Use the **median** historical FCF margin for forecasting, not the mean.

**Why:**
- The mean is distorted by outliers: one bad year (COVID shutdown, restructuring charge)
  drags the average down even if 4 out of 5 years were normal
- The median is the "typical" year — unaffected by a single outlier
- For a forecast, we care about what the company normally does, not what happened
  in one exceptional year

**Example:**
```
FCF Margins: [32%, 28%, 35%, -8%, 41%]  # -8% was COVID year
Mean:   25.6%
Median: 32.0%   ← Much better representation of normal operations
```

---

### 4. Gordon Growth Rate Capped at GDP Growth

**Decision:** Terminal growth rate `g` is capped at 2.5% (≈ long-run US real GDP growth).

**Why:**
The Gordon Growth Model (`TV = FCF × (1+g) / (WACC-g)`) implies the company grows
forever at rate `g`. If g > long-run GDP growth, the company eventually becomes larger
than the entire economy — a mathematical impossibility.

**The denominator risk:** If `g` approaches `WACC`, the denominator `(WACC - g)` approaches
zero and Terminal Value approaches infinity. Setting g ≤ 2.5% keeps us well away from this.

```python
# config.py
DCF_TERMINAL_GROWTH_RATE: float = 0.025  # 2.5%
```

---

### 5. Blended Terminal Value (Gordon + Exit Multiple)

**Decision:** Average the Gordon Growth Model TV and Exit Multiple TV.

**Why:**
- Both methods have blind spots:
  - Gordon Growth: highly sensitive to small changes in g (see above)
  - Exit Multiple: depends on picking the right peer group multiple
- Averaging them provides a "cross-check" — if they diverge >50%, it signals
  that either g or the multiple is extreme
- This is standard practice in investment banking

---

### 6. Diluted Shares for Per-Share Value

**Decision:** Use **diluted** shares outstanding, not basic shares.

**Why:**
- Diluted shares include: stock options, RSUs (restricted stock units), warrants,
  and convertible bonds — all of which will eventually become real shares
- Using basic shares **overestimates** per-share value because the denominator is too small
- Standard practice: equity research always uses diluted shares for EPS and per-share valuations

---

### 7. OLS Beta Over Sector Beta (When Available)

**Decision:** Compute beta from Alpaca daily price data (OLS regression vs SPY) when
Alpaca keys are configured. Fall back to `config.DCF_INDUSTRY_BETAS` only when not.

**Why:**
- Sector betas are averages — they don't capture this specific company's current risk profile
- OLS beta from 252 days of actual price data reflects current market perception of risk
- NVDA's computed beta (1.68) differs from the sector table (1.65) by only 0.03 in this case,
  but for less-traded or restructuring companies the difference can be >0.5, which changes
  WACC by 275 basis points and fair value by 20-30%

**The `beta_source` field:** Both the beta value and its source (`"computed"` vs `"sector_lookup"`)
are stored in the DCF output so you always know which methodology was used. Transparency.

---

### 8. Annual Data Only (No Mixing With Quarterly)

**Decision:** DCF uses **only** 10-K / 20-F (annual) filings. Quarterly data (10-Q / 6-K)
is explicitly excluded from the historical FCF time series.

**Why (the hard-learned lesson):**
When you compute `ΔNWC = NWC_year2 - NWC_year1`, both data points must be from
the same period type (both annual, both quarterly). Mixing them means you're subtracting
a September 30 balance from a January 26 balance — not a 12-month change, but a ~9-month
one. The error is large, silent, and easy to miss.

```python
# config.py
ANNUAL_FORM_TYPES = ["10-K", "20-F"]

# src/dcf_calculator.py — filtering
if filing.get("form") not in config.ANNUAL_FORM_TYPES:
    continue  # Skip quarterly data
```

---

### 9. Graceful Degradation for Optional Services

**Decision:** Alpaca and Email are optional — the pipeline runs fully without them.

**Why:**
- Not everyone has Alpaca API keys or wants emails
- A missing API key should not crash a 2-minute pipeline run that successfully
  fetched 317 XBRL metrics
- `AlpacaClient.enabled = bool(ALPACA_API_KEY and ALPACA_SECRET_KEY)` — checked once
- All methods return `None` or `[]` (not exceptions) on any failure
- `EmailReporter.enabled = bool(EMAIL_ADDRESS and EMAIL_APP_PASSWORD)` — same pattern

**The pattern used throughout:**
```python
if client.enabled:
    result = client.do_thing()
else:
    result = None  # Pipeline continues with result = None
```

---

## Software Engineering Decisions

### 10. Secrets in `.env`, Never in Code

**Decision:** All API keys and passwords live in `.env` (not committed to git).

**Why:**
- If you commit a real API key to GitHub (even in a private repo), it can be scraped
  by automated bots within minutes. GitHub has had incidents where secrets in "deleted"
  commits were recovered from git history.
- `.env` is in `.gitignore` — it never enters version control
- `python-dotenv` loads `.env` into environment variables at startup (`load_dotenv()`)
- All code reads from `os.getenv("ALPACA_API_KEY", "")` — empty string if not set

**The commit check:** If you accidentally remove `.env` from `.gitignore`, running
`git status` will show it as untracked. Never `git add .` blindly.

---

### 11. `Optional[float]` Return Types (Not Exceptions)

**Decision:** Most data-fetching methods return `Optional[float]` (i.e., `None` on failure)
rather than raising exceptions.

**Why:**
- The pipeline processes multiple tickers. If NVDA beta calculation fails due to a
  network hiccup, we don't want the entire AAPL run to fail too.
- The caller can decide what to do with `None` (use fallback, skip metric, log warning)
- Exceptions are reserved for truly unrecoverable situations (e.g., the SEC API is
  completely unreachable) or for data integrity violations

**The exception:**
XBRL parsing (`xbrl_parser.py`) raises `XBRLParseError` when the data is structurally
corrupt — because there's no sensible fallback when the filing itself is malformed.

---

### 12. Try All XBRL Tag Variants

**Decision:** For each financial metric, define a priority-ordered list of XBRL tags
to try, not a single tag.

**Why:**
Different companies legitimately use different XBRL tags for the same concept:

```python
REVENUE_KEYS = [
    "Revenues",                                           # NVDA, many companies
    "RevenueFromContractWithCustomerExcludingAssessedTax", # ASC 606 adoption
    "SalesRevenueNet",                                    # Older filers
    ...
]
```

If we hardcoded `"Revenues"` only, any company using `RevenueFromContractWith...`
would show zero revenue — a silent, catastrophic error. The priority list makes
the code robust across the universe of US and foreign filers.

---

### 13. Mocked Tests for All External APIs

**Decision:** Unit tests mock all external API calls (SEC, Alpaca, SMTP).
Only `test_xbrl_parser.py` makes real network calls (and it's explicitly an
integration test, documented as such).

**Why:**
- Speed: 161 mocked tests run in ~3 seconds. With real API calls: ~10 minutes.
- Reliability: Tests don't fail because SEC is rate-limiting you at 2am.
- Determinism: The test always gets the same mock response — no "flaky" tests.
- No side effects: Running tests doesn't send real emails or consume API quota.

**Trade-off acknowledged:** Mocked tests don't catch API contract changes.
If Alpaca changes the JSON structure of `/snapshot`, the mock still passes
but the live code breaks. This is managed by having one live integration test
(`python main.py NVDA`) that can be run manually before releases.

---

### 14. Config Module Pattern

**Decision:** All constants live in `config.py` as module-level typed variables.
No constants in function bodies.

**Why:**
- Single source of truth: changing a URL, threshold, or DCF parameter requires
  one edit in one file
- Type annotations (`ALPACA_DATA_URL: str = ...`) make the expected type explicit
- Tests can patch config values: `patch.object(config, "ALPACA_API_KEY", "FAKE")`
  — this is only possible when the variable is a module-level attribute

---

### 15. Result Dictionary Pattern (Not Object)

**Decision:** `process_ticker()` returns a plain `dict`, not a dataclass or object.

**Why:**
- Simple to serialize to JSON for email body building
- Easy to merge/extend: `result["current_price"] = price` — no constructor needed
- Each phase just adds its keys; no class inheritance or method dispatch required
- The email reporter receives `Dict[str, Dict]` — works with any dict, no type coupling

**Trade-off:** Dicts have no type safety — a typo like `result["dcf_fair_vale"]` fails
silently. In a larger codebase, a dataclass or TypedDict would be better.
For this project's size, the simplicity wins.
