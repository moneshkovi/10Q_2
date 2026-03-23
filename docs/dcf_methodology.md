# DCF Methodology — Code-Connected Reference

This document explains the DCF model as implemented in `src/dcf_calculator.py`.
For pure finance theory, see `DCF_MODEL.md` in the project root.
This doc bridges theory → code → output.

---

## The Two FCF Methods (And Why We Have Both)

This is the most important design decision in the entire model.

### Method 1: OCF Method (Preferred)

```
FCFF = Operating Cash Flow (OCF)
       - Capital Expenditures (CapEx)
       + Interest Expense × (1 - Tax Rate)
```

**Code location:** `src/dcf_calculator.py → _compute_fcff_ocf_method()`

**Why preferred:**
- OCF is a single number directly on the cash flow statement — less data assembly
- Avoids the `ΔNWC` calculation entirely (NWC changes are *inside* OCF already)
- More robust when quarterly balance sheet data bleeds into annual historicals
  (the bug we fixed in March 2026 — see `design_decisions.md`)

**When it works:** When SEC XBRL contains `NetCashProvidedByUsedInOperatingActivities`
and `PaymentsToAcquirePropertyPlantAndEquipment`.

### Method 2: EBIT Method (Fallback)

```
FCFF = EBIT × (1 - Tax Rate)
       + Depreciation & Amortization (D&A)
       - Capital Expenditures (CapEx)
       - Change in Net Working Capital (ΔNWC)
```

**Code location:** `src/dcf_calculator.py → _compute_fcff_ebit_method()`

**Why it's the fallback:**
- Requires assembling NWC from balance sheet components
- ΔNWC is computed as `this_year_NWC - prior_year_NWC`
- If the prior year's NWC comes from a quarterly filing mixed in by mistake,
  ΔNWC becomes a 3-month change instead of annual — a silent, large error

**When it's used:** When OCF data is missing from XBRL.

### Precedence Logic

```python
# In src/dcf_calculator.py → _extract_historicals()
if ocf is not None and capex is not None:
    fcff = ocf - capex + interest * (1 - tax_rate)  # OCF method
    method = "ocf"
elif ebit is not None:
    fcff = ebit * (1 - tax_rate) + da - capex - delta_nwc  # EBIT method
    method = "ebit"
```

The method used is stored and appears in DCF output for transparency.

---

## XBRL Metric Lookup Strategy

### The Problem

XBRL has no single "Revenue" tag. Different companies use different tag names
for the same concept. NVDA uses `Revenues`, but another company might use
`RevenueFromContractWithCustomerExcludingAssessedTax`.

### Our Solution: Try Multiple Tags in Priority Order

```python
REVENUE_KEYS = [
    "Revenues",                                           # Most common
    "RevenueFromContractWithCustomerExcludingAssessedTax", # ASC 606 standard
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "SalesRevenueNet",
    "SalesRevenueGoodsNet",
    "SalesRevenueServicesNet",
]
```

**Code location:** `src/dcf_calculator.py → _lookup_metric()`

The function iterates through each key until it finds a value for the target period.
First match wins. If none match, returns `None`.

### US-GAAP + IFRS Combined Lookup

For companies filing under IFRS (20-F filers like AZN), the XBRL tags differ entirely:

```python
IFRS_REVENUE_KEYS = [
    "Revenue",          # ifrs-full:Revenue
    "RevenueFromContracts",
]

# In _lookup_metric() — tries US-GAAP first, then IFRS
for key in us_gaap_keys + ifrs_keys:
    if key in metrics:
        return metrics[key]
```

---

## Revenue Forecasting in Detail

### Step 1: Calculate Historical CAGR

```python
# 5 years of historical annual revenue
revenues = [27.1, 44.9, 60.9, 79.8, 130.5]  # NVDA example (billions)

cagr = (revenues[-1] / revenues[0]) ** (1 / (len(revenues) - 1)) - 1
# = (130.5 / 27.1) ^ (1/4) - 1 = 48.1%
```

**Why 5 years?** Enough to capture a full business cycle without overweighting
very old data that may not reflect current business model.

### Step 2: Apply Tapering

Growth doesn't continue at 48% forever. We apply tapering:

```python
TAPER_FACTORS = [0.90, 0.75, 0.60, 0.45, 0.35]

for year, taper in enumerate(TAPER_FACTORS, 1):
    # Blend historical CAGR toward terminal growth rate
    year_growth = terminal_growth + taper * (cagr - terminal_growth)
    projected_revenue[year] = prior_revenue * (1 + year_growth)
```

**The blending formula ensures:**
- Year 1 growth ≈ 90% of historical, 10% terminal
- Year 5 growth ≈ 35% of historical, 65% terminal
- Smooth convergence — never a sudden jump to 2.5% growth

### Step 3: Apply Margins

Revenue → EBIT via the FCF margin:

```python
# Historical median FCF margin (FCF / Revenue)
fcf_margin = median([fcff/rev for fcff, rev in historicals])

# Apply to projected revenue
projected_fcff[year] = projected_revenue[year] * fcf_margin
```

Using the **median** (not mean) is intentional: median is robust to outliers.
A single bad year (COVID, restructuring charge) won't skew the entire forecast.

---

## Terminal Value — Two Methods, Then Averaged

### Method 1: Gordon Growth Model

```
TV_gordon = FCF_year5 × (1 + g) / (WACC - g)

Where g = 2.5% (perpetual growth rate, ≤ long-run GDP growth)
```

**Why ≤ GDP?** If a company grows faster than the entire economy forever, it
eventually becomes larger than the economy — a logical impossibility.

**Code:**
```python
tv_gordon = fcff_year5 * (1 + terminal_growth) / (wacc - terminal_growth)
```

### Method 2: Exit Multiple (EV/EBITDA)

```
TV_multiple = EBITDA_year5 × sector_multiple
```

**Code:**
```python
sector_multiple = config.DCF_EXIT_MULTIPLES.get(ticker, 15.0)
tv_multiple = ebitda_year5 * sector_multiple
```

Exit multiples by sector in `config.DCF_EXIT_MULTIPLES`:
- Semiconductors: 18x
- Technology: 20x
- Healthcare: 14x
- Financial Services: 10x

### Blended Terminal Value

```python
terminal_value = (tv_gordon + tv_multiple) / 2
```

Using both methods as a cross-check. If they diverge significantly (>50% difference),
it signals that one set of assumptions is extreme and should be reviewed.

---

## Discounting Cash Flows

Each year's FCF and the terminal value are discounted back to present value:

```
PV(FCF_year_t) = FCF_t / (1 + WACC)^t

PV(Terminal Value) = TV / (1 + WACC)^5
```

**Code:**
```python
pv_fcfs = sum(fcff[t] / (1 + wacc) ** t for t in range(1, 6))
pv_tv   = terminal_value / (1 + wacc) ** 5
enterprise_value = pv_fcfs + pv_tv
```

---

## Equity Value Bridge

```
Enterprise Value
  + Cash & Equivalents       (XBRL: CashAndCashEquivalentsAtCarryingValue)
  + Short-Term Investments   (XBRL: ShortTermInvestments)
  - Long-Term Debt           (XBRL: LongTermDebt)
  - Short-Term Debt          (XBRL: ShortTermBorrowings)
  = Equity Value

÷ Diluted Shares Outstanding (XBRL: CommonStockSharesOutstanding, diluted)
  = Fair Value Per Share
```

**Why diluted shares?** Diluted shares include stock options, RSUs, and convertible
bonds that haven't converted yet but will eventually. Using diluted shares gives
a more conservative (lower) per-share value — better to be conservative than to
overstate.

---

## WACC Construction

```python
def _calculate_wacc(ticker, historicals, beta_override=None):
    # 1. Beta
    if beta_override is not None:
        beta = beta_override          # From Alpaca OLS
        beta_source = "computed"
    else:
        beta = DCF_INDUSTRY_BETAS.get(ticker, 1.0)
        beta_source = "sector_lookup"

    # 2. Cost of equity (CAPM)
    ke = rf_rate + beta * equity_risk_premium
    # rf_rate = 4.5%, equity_risk_premium = 5.5% (Damodaran)

    # 3. Cost of debt (from filing)
    kd = interest_expense / total_debt if total_debt > 0 else 0.05

    # 4. Capital structure weights
    total_capital = equity + debt
    we = equity / total_capital   # weight of equity
    wd = debt / total_capital     # weight of debt

    # 5. After-tax cost of debt (interest is tax-deductible)
    kd_after_tax = kd * (1 - tax_rate)

    # 6. WACC
    wacc = we * ke + wd * kd_after_tax
```

---

## Sensitivity Analysis

After computing the base case, we run a 5×5 grid varying WACC and growth rate:

```python
wacc_range   = [base_wacc - 0.02, base_wacc - 0.01, base_wacc,
                base_wacc + 0.01, base_wacc + 0.02]
growth_range = [0.015, 0.020, 0.025, 0.030, 0.035]

for w in wacc_range:
    for g in growth_range:
        fair_value = compute_dcf(fcffs, terminal_value_with_g=g, wacc=w)
        sensitivity_table[w][g] = fair_value
```

This produces the classic investment bank 2D sensitivity matrix. The base case is
in the center. Read across rows to see WACC impact; down columns to see growth impact.

---

## Output Files

| File | Contents |
|------|---------|
| `{TICKER}_dcf_valuation.json` | Complete model: inputs, FCF projections, WACC breakdown, TV, sensitivity |
| `{TICKER}_dcf_summary.csv` | One row per key metric — open in Excel |
| `{TICKER}_dcf_forecast.csv` | Year-by-year: historical + 5 projected years, all line items |
| `{TICKER}_dcf_sensitivity.csv` | WACC × growth matrix + Bull/Base/Bear scenarios |

---

## Quality Score

The DCF also outputs a `quality_score` (0-100):

```python
# Deductions from 100:
- Revenue missing:           -30
- OCF missing:               -20
- Shares outstanding missing: -15
- < 3 years of data:         -15
- Only EBIT method available: -10
- WACC uses sector beta:      -5
```

A score of 85+ means the model has excellent data quality.
Below 50 means critical inputs were missing — treat the result with skepticism.

---

## Known Limitations (Be Honest About These)

1. **No segment-level revenue build.** Real equity research models revenue
   segment by segment (e.g., NVDA: Data Center / Gaming / Auto). We use
   a single consolidated revenue line. This means we cannot distinguish
   between a shift in business mix.

2. **Static FCF margin.** We use the historical median FCF margin for all 5 years.
   In reality, margins expand as a company scales or compress as competition grows.
   A more sophisticated model adjusts margins in the forecast period.

3. **No working capital forecast.** The OCF method bakes WC changes into OCF.
   We don't explicitly forecast receivables, inventory, or payables.

4. **Minority interests / joint ventures.** If a company has significant minority
   interests (like Berkshire's equity investments), the equity bridge may be
   slightly understated.

5. **Lease obligations.** Post-ASC 842, operating leases are on the balance sheet.
   We include them in total debt, which is correct but increases leverage metrics.
