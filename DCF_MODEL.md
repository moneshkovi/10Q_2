# DCF Model - Complete Reference Guide

**What is a DCF?** A Discounted Cash Flow (DCF) model estimates what a company is **worth today** based on all the **cash it will generate in the future**. The idea is simple: a dollar earned next year is worth less than a dollar today (because you could invest today's dollar and earn a return). So we "discount" future cash flows back to the present.

**Why it matters:** This is the #1 valuation method used by investment banks (JP Morgan, Goldman Sachs, Morgan Stanley) and institutional investors. It tells you if a stock is **overvalued** or **undervalued** compared to its intrinsic worth.

---

## Table of Contents

1. [The Big Picture](#1-the-big-picture)
2. [Free Cash Flow (FCF)](#2-free-cash-flow-fcf)
3. [WACC (Discount Rate)](#3-wacc-discount-rate)
4. [Revenue Forecasting](#4-revenue-forecasting)
5. [Terminal Value](#5-terminal-value)
6. [Enterprise Value](#6-enterprise-value)
7. [Equity Value Bridge](#7-equity-value-bridge)
8. [Sensitivity Analysis](#8-sensitivity-analysis)
9. [Scenario Analysis](#9-scenario-analysis)
10. [Key Metrics (JPM Highlights)](#10-key-metrics-jpm-highlights)
11. [How to Read the Output](#11-how-to-read-the-output)
12. [Limitations & Pitfalls](#12-limitations--pitfalls)

---

## 1. The Big Picture

### The DCF Formula

```
                     FCF₁         FCF₂         FCF₃              FCF₅ + Terminal Value
Enterprise Value = --------- + --------- + --------- + ... + -------------------------
                   (1+WACC)¹   (1+WACC)²   (1+WACC)³              (1+WACC)⁵
```

### In Plain English

1. **Estimate** how much cash the company will produce each year for the next 5 years
2. **Discount** each year's cash back to today's value (because future money is worth less)
3. **Add a Terminal Value** for all cash produced after year 5 (into perpetuity)
4. **Sum it all up** = Enterprise Value (what the whole business is worth)
5. **Add cash, subtract debt** = Equity Value (what belongs to shareholders)
6. **Divide by shares** = Fair Value per Share (what each share should be worth)

### Visual Flow

```
Historical Data (5 years of 10-K filings)
    ↓
Calculate Historical FCF, Margins, Growth Rates
    ↓
Forecast 5 Years of Future FCF
    ↓
Calculate Terminal Value (value beyond year 5)
    ↓
Discount Everything Back to Today (using WACC)
    ↓
Enterprise Value
    ↓
+ Cash - Debt = Equity Value
    ↓
÷ Shares Outstanding = Fair Value Per Share
    ↓
Compare to Current Stock Price → Overvalued or Undervalued?
```

---

## 2. Free Cash Flow (FCF)

### What is FCF?

**Free Cash Flow to Firm (FCFF)** is the cash a company generates after paying all operating expenses and reinvesting in the business. It's the cash available to **all capital providers** (both debt holders and equity holders).

Think of it like your personal finances:
- **Salary** = Revenue
- **Living expenses** = Operating costs
- **Money left after expenses** = Operating income
- **Minus taxes** = After-tax income
- **Minus home repairs/car payments** = Capital expenditures
- **What's left in your bank account** = Free Cash Flow

### The FCFF Formula

```
FCFF = EBIT × (1 - Tax Rate) + D&A - CapEx - ΔNWC
```

Let's break down each component:

### EBIT (Earnings Before Interest and Taxes)

```
EBIT = Revenue - COGS - Operating Expenses
     = Operating Income
```

**What it means:** How much profit the company makes from its core business operations, before paying interest on debt or taxes. This is also called **Operating Income**.

**Why we use EBIT (not Net Income):** EBIT removes the effect of the company's financing decisions (how much debt they have). Since WACC already accounts for debt, using EBIT avoids double-counting.

**Example (NVIDIA FY 2026):**
```
Revenue:          $130.5B
- COGS:           -$37.8B
- Operating Exp:  -$13.9B
= EBIT:           $78.8B
```

### Tax Rate (Effective)

```
Effective Tax Rate = Income Tax Expense / Pre-Tax Income
```

**What it means:** The actual percentage of income the company pays in taxes. This differs from the statutory rate (21% in the US) because of deductions, credits, and international operations.

**Typical ranges:**
- US corporate statutory rate: 21%
- Big tech companies: 12-18% (due to R&D credits, international structures)
- Average US company: 18-22%

### NOPAT (Net Operating Profit After Tax)

```
NOPAT = EBIT × (1 - Tax Rate)
```

**What it means:** The company's operating profit after paying taxes, but BEFORE any interest payments. This is the profit available to all capital providers.

**Why it matters:** NOPAT is the purest measure of a company's operating profitability. It removes the effects of capital structure (debt vs equity).

### D&A (Depreciation & Amortization)

```
D&A = Depreciation + Amortization
```

**What it means:**
- **Depreciation:** The gradual "expensing" of physical assets (buildings, machines) over their useful life. Your $10M machine doesn't become worthless overnight - depreciation spreads the cost over 10 years ($1M/year).
- **Amortization:** Same concept but for intangible assets (patents, software, goodwill).

**Why we ADD it back:** D&A is a **non-cash expense**. The company already paid for the asset; D&A just spreads the accounting cost. Since FCF measures actual cash, we add back this non-cash charge.

### CapEx (Capital Expenditures)

```
CapEx = Payments to Acquire Property, Plant & Equipment
```

**What it means:** Money the company spends buying or upgrading physical assets (factories, servers, offices, equipment). This is the cash the company MUST reinvest to maintain and grow its business.

**Why we SUBTRACT it:** Unlike D&A (which is just an accounting entry), CapEx is real cash going out the door. The company must spend this money to keep operating.

**Types of CapEx:**
- **Maintenance CapEx:** Just to keep current operations running (replacing worn-out equipment)
- **Growth CapEx:** To expand the business (new factories, data centers)

### ΔNWC (Change in Net Working Capital)

```
Net Working Capital (NWC) = Current Assets (excl. cash) - Current Liabilities

ΔNWC = This Year's NWC - Last Year's NWC
```

**What it means:** NWC is the cash tied up in day-to-day operations. When NWC increases, the company is tying up MORE cash in operations (bad for FCF). When it decreases, cash is being freed up (good for FCF).

**Components:**
- **Current Assets:** Accounts receivable (money customers owe you), inventory (products waiting to be sold)
- **Current Liabilities:** Accounts payable (money you owe suppliers), accrued expenses

**Simple example:**
- You sell $1M of products but customers haven't paid yet → $1M stuck in accounts receivable
- That's $1M of revenue that isn't actually cash yet
- ΔNWC captures this difference between accounting profit and actual cash

### EBITDA (Earnings Before Interest, Taxes, Depreciation & Amortization)

```
EBITDA = EBIT + D&A
```

**What it means:** A commonly used profitability metric that strips out financing (interest), taxes, and non-cash charges (D&A). It's a rough proxy for operating cash flow.

**Why it's popular:** EBITDA allows apples-to-apples comparison between companies with different tax situations, debt levels, and asset ages.

**Limitation:** EBITDA ignores CapEx, so a company could have great EBITDA but terrible FCF if it needs massive capital investment.

---

## 3. WACC (Discount Rate)

### What is WACC?

**Weighted Average Cost of Capital (WACC)** is the rate of return that a company must earn on its investments to satisfy both its **debt holders** and **equity holders**.

Think of it as the "hurdle rate" - the minimum return the company needs to generate to justify its existence. If a company earns less than its WACC, it's destroying value.

### The WACC Formula

```
WACC = (E/V) × Ke + (D/V) × Kd × (1 - t)

Where:
  E = Market value of equity (or book equity)
  D = Market value of debt
  V = E + D (total capital)
  Ke = Cost of Equity
  Kd = Cost of Debt
  t = Tax Rate
```

### Why Debt Gets a Tax Adjustment

Notice the `(1 - t)` on the debt portion? That's because **interest payments are tax-deductible**. If a company pays $100 in interest and its tax rate is 21%, the actual cost is only $79 (the government effectively subsidizes $21). This is called the **tax shield**.

### Cost of Equity (Ke) - CAPM

```
Ke = Rf + β × ERP

Where:
  Rf = Risk-Free Rate (10-year US Treasury yield)
  β = Beta (systematic risk)
  ERP = Equity Risk Premium (extra return for stock risk)
```

#### Risk-Free Rate (Rf)

**What it is:** The return you'd earn on a "risk-free" investment - typically the 10-year US Treasury bond yield.

**Current value used:** 4.5% (as of 2026)

**Why:** This is the baseline. Any investment must earn MORE than this, or you'd just buy Treasury bonds instead.

#### Beta (β)

**What it is:** A measure of how much a stock moves relative to the overall market (S&P 500).

**Interpretation:**
- **β = 1.0:** Stock moves exactly with the market
- **β > 1.0:** Stock is MORE volatile than the market (riskier)
- **β < 1.0:** Stock is LESS volatile than the market (safer)

**Examples:**
| Stock | Beta | Meaning |
|-------|------|---------|
| NVDA  | 1.65 | Very volatile - moves 65% more than market |
| AAPL  | 1.20 | Somewhat volatile |
| MSFT  | 0.95 | Nearly tracks the market |
| JNJ   | 0.60 | Defensive - moves less than market |
| PG    | 0.45 | Very stable - classic "safe haven" |

**Impact on valuation:** Higher beta → higher cost of equity → higher WACC → lower fair value. Risky companies are worth less because investors demand a higher return.

#### Equity Risk Premium (ERP)

**What it is:** The extra return investors demand for owning stocks instead of risk-free bonds.

**Current value used:** 5.5% (Damodaran estimate, long-term average)

**Logic:** If bonds pay 4.5% risk-free, investors need roughly 10% (4.5% + 5.5%) to justify the risk of owning stocks.

### Cost of Debt (Kd)

```
Kd = Interest Expense / Total Debt
```

**What it is:** The interest rate the company pays on its borrowings. We calculate it from the financial statements.

**After-tax cost:** Kd × (1 - Tax Rate), because interest is tax-deductible.

### Capital Structure Weights

```
Weight of Equity = Equity / (Equity + Debt)
Weight of Debt = Debt / (Equity + Debt)
```

**What it means:** How much of the company is financed by shareholders (equity) vs. lenders (debt). More debt = lower WACC (debt is cheaper due to tax shield), but also more risk.

### WACC Example (NVIDIA)

```
Inputs:
  Risk-Free Rate:    4.5%
  Beta:              1.65
  Equity Risk Premium: 5.5%
  Cost of Debt:      6.0%
  Tax Rate:          15%
  Weight Equity:     95%
  Weight Debt:       5%

Calculation:
  Cost of Equity = 4.5% + 1.65 × 5.5% = 13.58%
  After-Tax Debt = 6.0% × (1 - 0.15) = 5.10%
  WACC = 95% × 13.58% + 5% × 5.10% = 13.15%
```

---

## 4. Revenue Forecasting

### Methodology

We use a **top-down, revenue-driven** approach:

1. **Calculate historical CAGR** (Compound Annual Growth Rate) from 5 years of data
2. **Apply tapering** - growth rates gradually decline toward the terminal rate
3. **Apply margins** to convert revenue into EBIT, NOPAT, and FCF

### CAGR (Compound Annual Growth Rate)

```
CAGR = (Ending Value / Beginning Value)^(1/years) - 1
```

**What it means:** The smoothed annual growth rate over a period. If revenue went from $27B to $130B over 5 years, the CAGR is:

```
CAGR = ($130B / $27B)^(1/5) - 1 = 36.9%
```

### Growth Tapering

High growth rates don't last forever. We use a **tapering schedule** to gradually reduce growth toward the terminal rate (2.5%):

| Year | Taper Factor | Logic |
|------|-------------|-------|
| Year 1 | 90% of CAGR | Still growing fast |
| Year 2 | 75% of CAGR | Competition catches up |
| Year 3 | 60% of CAGR | Market matures |
| Year 4 | 45% of CAGR | Growth normalizing |
| Year 5 | 35% of CAGR | Approaching steady state |

**Example (NVIDIA with 37% CAGR):**
```
Year 1: 37% × 0.90 = 33.3% (blended with terminal)
Year 2: 37% × 0.75 = 27.8%
Year 3: 37% × 0.60 = 22.2%
Year 4: 37% × 0.45 = 16.7%
Year 5: 37% × 0.35 = 13.0%
```

Each year's rate is also blended with the terminal growth rate for a smooth convergence.

---

## 5. Terminal Value

### What is Terminal Value?

Terminal Value represents the value of **all cash flows beyond the forecast period** (after Year 5). Since we can't forecast forever, we estimate a "perpetuity value" for everything from Year 6 onward.

**Critical fact:** Terminal Value typically represents **60-80% of total Enterprise Value**. This is both the most important and most uncertain part of a DCF.

### Method 1: Gordon Growth Model (Perpetuity Growth)

```
Terminal Value = FCF₅ × (1 + g) / (WACC - g)

Where:
  FCF₅ = Free Cash Flow in the final forecast year
  g = Perpetual growth rate (usually 2-3%)
  WACC = Discount rate
```

**Logic:** After Year 5, we assume the company grows at a constant rate forever. The formula is derived from the math of infinite geometric series.

**Terminal Growth Rate (g):**
- Should be ≤ long-term GDP growth (2-3%)
- If g > WACC, the formula breaks (infinite value!)
- Higher g = higher Terminal Value = higher fair value
- This is the **most sensitive** assumption in the entire model

### Method 2: Exit Multiple

```
Terminal Value = EBITDA₅ × EV/EBITDA Multiple

Where:
  EBITDA₅ = EBITDA in the final forecast year
  Multiple = What investors typically pay for this type of company
```

**Logic:** Instead of assuming perpetual growth, we assume someone buys the company at the end of Year 5 at a typical market multiple.

**Typical EV/EBITDA Multiples:**
| Sector | Multiple | Why |
|--------|----------|-----|
| Software | 18-22x | High margins, recurring revenue |
| Semiconductors | 14-18x | Cyclical but growing |
| Technology | 16-20x | Growth premium |
| Financial Services | 8-12x | Regulated, lower growth |
| Healthcare | 12-16x | Stable demand |
| Energy | 5-8x | Cyclical, capital intensive |
| Consumer Staples | 13-17x | Stable but slow growth |

### Blended Terminal Value

Our model uses the **average of both methods** as the final Terminal Value. This provides a cross-check - if the two methods give very different results, it signals the assumptions may need adjustment.

### Terminal Value Risk

| TV % of EV | Risk Level | Interpretation |
|-----------|------------|----------------|
| < 65% | LOW | Well-supported by near-term cash flows |
| 65-80% | MODERATE | Typical range, acceptable |
| > 80% | HIGH | Too much value in distant future - uncertain |

---

## 6. Enterprise Value

### What is Enterprise Value?

**Enterprise Value (EV)** is the total value of the business - what you'd have to pay to buy the entire company (both the equity AND its debt).

### Calculation

```
Enterprise Value = PV(Year 1 FCF) + PV(Year 2 FCF) + ... + PV(Year 5 FCF) + PV(Terminal Value)

Where PV = Present Value = FCF / (1 + WACC)^year
```

### Discount Factor

```
Discount Factor for Year t = 1 / (1 + WACC)^t
```

**Example with WACC = 10%:**
| Year | Discount Factor | $100 FCF is worth today... |
|------|----------------|---------------------------|
| 1 | 0.909 | $90.91 |
| 2 | 0.826 | $82.64 |
| 3 | 0.751 | $75.13 |
| 4 | 0.683 | $68.30 |
| 5 | 0.621 | $62.09 |

The further out the cash flow, the less it's worth today. This is the **time value of money**.

---

## 7. Equity Value Bridge

### From Enterprise Value to Share Price

Enterprise Value includes both debt and equity. To get to what shareholders own:

```
Enterprise Value
  + Cash & Short-Term Investments    ← Cash adds to value
  - Total Debt (Long + Short Term)   ← Debt reduces value
  = Equity Value                     ← What shareholders own
  ÷ Diluted Shares Outstanding       ← Split among shares
  = Fair Value Per Share             ← What each share is worth
```

### Why Add Cash?

If a company has $50B in cash sitting in the bank, that cash belongs to shareholders. It's not part of the operating business (we already excluded it from NWC), so we add it back.

### Why Subtract Debt?

Debt holders get paid before shareholders. If you're buying the whole company, you inherit the debt. So debt reduces what's left for equity holders.

### Shares Outstanding

We use **diluted shares** (not basic shares) because:
- Stock options and RSUs will eventually become real shares
- Using diluted shares gives a more conservative (realistic) per-share value

---

## 8. Sensitivity Analysis

### Why Sensitivity Matters

The DCF result is only as good as its assumptions. Small changes in WACC or terminal growth can dramatically change the fair value. The sensitivity table shows how the fair value changes across different assumption combinations.

### WACC vs Terminal Growth Rate Matrix

This is the classic "2D sensitivity table" that every equity research report includes:

```
                    Terminal Growth Rate
                 1.5%    2.0%    2.5%    3.0%    3.5%
WACC  10%      $65.20  $72.10  $80.50  $91.30  $106.20
      11%      $55.30  $60.40  $66.80  $74.80  $85.10
      12%      $47.80  $51.70  $56.40  $62.10  $69.40  ← Base Case
      13%      $41.90  $45.00  $48.60  $53.00  $58.40
      14%      $37.10  $39.60  $42.50  $45.90  $50.10

★ = Base case (your primary estimate)
```

**How to read it:**
- Each cell shows the fair value per share under that WACC/growth combination
- The center cell (★) is your base case
- Look at the range: if fair values span $37-$106, there's significant uncertainty
- If the current stock price is $50 and most cells show >$50, the stock looks undervalued

---

## 9. Scenario Analysis

### Bull / Base / Bear

Professional analysts always present three scenarios:

### Bull Case (Optimistic)
- Revenue growth **20% above** base case
- Operating margins **expand 5%**
- WACC **0.5% lower** (market assigns less risk)
- Terminal growth **0.5% higher**

**When this happens:** Market share gains, new products succeed, industry tailwinds

### Base Case (Most Likely)
- Current growth trajectory maintained
- Margins stable at historical average
- Standard WACC and terminal growth

**When this happens:** Business continues as expected

### Bear Case (Pessimistic)
- Revenue growth **30% below** base case
- Operating margins **compress 10%**
- WACC **1% higher** (more risk)
- Terminal growth **0.5% lower**

**When this happens:** Competition intensifies, macro downturn, product failure

---

## 10. Key Metrics (JPM Highlights)

These are the metrics that a JP Morgan equity analyst would circle in red on a DCF presentation:

### ★ ROIC vs WACC (The Most Important Check)

```
ROIC = NOPAT / Invested Capital
Invested Capital = Equity + Debt

If ROIC > WACC → Company is CREATING value (every dollar invested earns more than it costs)
If ROIC < WACC → Company is DESTROYING value (would be better off returning cash to investors)
```

**This is THE single most important metric in corporate finance.** Warren Buffett's entire strategy boils down to finding companies with ROIC consistently above WACC.

**Example:**
- NVIDIA ROIC: 45%, WACC: 13% → Spread of +32% → MASSIVE value creation
- A struggling retailer: ROIC 6%, WACC 9% → Spread of -3% → Destroying value

### ★ FCF Yield

```
FCF Yield = Free Cash Flow / Enterprise Value
```

**What it means:** The cash return you'd earn if you bought the entire company at its current Enterprise Value.

**Interpretation:**
- **> 8%:** Potentially undervalued (or declining business)
- **4-8%:** Fair value range
- **< 4%:** Expensive (or high-growth company)

### ★ Implied EV/EBITDA

```
Implied EV/EBITDA = DCF Enterprise Value / Current EBITDA
```

**What it means:** What the DCF model implies the company should trade at, in terms of EV/EBITDA multiples. Compare this to:
- The company's historical average
- Peer companies' multiples
- Industry benchmarks

### ★ Terminal Value as % of Enterprise Value

A sanity check on model reliability:
- **< 65%:** Strong - most value comes from near-term (more visible) cash flows
- **65-80%:** Normal - typical DCF range
- **> 80%:** Concerning - too much value in the distant, uncertain future

### ★ Margin Trajectory

Tracking how margins evolve over time tells you if the business is:
- **Expanding margins:** Pricing power, scale benefits (bullish)
- **Stable margins:** Mature business, predictable (neutral)
- **Compressing margins:** Competition, cost pressure (bearish)

---

## 11. How to Read the Output

### Output Files Generated

```
data/{TICKER}/parsed/
├── {TICKER}_dcf_valuation.json      # Complete DCF model data
├── {TICKER}_dcf_summary.csv         # Executive summary (open in Excel)
├── {TICKER}_dcf_forecast.csv        # Historical + projected financials
└── {TICKER}_dcf_sensitivity.csv     # Sensitivity table + scenarios
```

### Quick Start: What to Look At First

1. **Open `_dcf_summary.csv`** in Excel
   - Look at **Fair Value Per Share** - is it above or below current stock price?
   - Check **ROIC vs WACC** - is the company creating value?
   - Check **Terminal Value Risk** - is it LOW/MODERATE/HIGH?

2. **Open `_dcf_sensitivity.csv`** in Excel
   - Find your base case (★)
   - Look at the range of fair values - how sensitive is it?
   - Check Bull/Base/Bear scenarios

3. **Open `_dcf_forecast.csv`** in Excel
   - Review historical vs projected numbers
   - Do the projections look reasonable?
   - Is margin trajectory realistic?

### Decision Framework

```
If Fair Value > Current Price by 20%+ → Potentially UNDERVALUED (buy signal)
If Fair Value ≈ Current Price (±10%)  → FAIRLY VALUED (hold)
If Fair Value < Current Price by 20%+ → Potentially OVERVALUED (sell signal)

BUT always check:
  1. Is ROIC > WACC? (value creation)
  2. Is TV Risk LOW? (reliable model)
  3. Do Bull/Base/Bear all agree? (conviction)
  4. Are assumptions reasonable? (garbage in = garbage out)
```

---

## 12. Limitations & Pitfalls

### What This Model Does Well
- Uses real SEC-filed financial data (not estimates)
- Industry-standard methodology (WACC, FCFF, Gordon Growth)
- Multiple valuation cross-checks (Gordon + Exit Multiple)
- Sensitivity analysis shows range of outcomes
- Bull/Base/Bear scenarios

### What This Model Does NOT Do
- **No market data integration:** We use book values for equity, not market cap. For a more accurate WACC, you'd want live stock price data.
- **No comparable company analysis:** A full valuation would include trading comps and precedent transactions alongside DCF.
- **Simplified forecasting:** Real equity research involves segment-by-segment revenue builds, not top-down CAGR tapering.
- **No industry-specific adjustments:** Financial companies (banks, insurance, asset managers) need different DCF approaches (dividend discount model, excess return model).
- **Static beta:** We use fixed industry betas, not calculated from historical stock returns.

### Common Pitfalls

1. **Terminal growth rate > GDP growth:** If you set g = 5%, you're saying the company will eventually become larger than the entire economy. Always use 2-3%.

2. **WACC too low:** A low WACC dramatically inflates fair value. Be conservative - better to undervalue slightly than to overpay.

3. **Ignoring CapEx:** EBITDA looks great but means nothing if the company must spend half of it on capital expenditures.

4. **One-time items:** Historical data may include one-time gains/losses. The model assumes these repeat, which can distort forecasts.

5. **Extrapolating hypergrowth:** A company growing 50%/year won't do so for 5 more years. The tapering schedule helps, but always sanity-check projections.

---

## Glossary

| Term | Formula | Plain English |
|------|---------|---------------|
| **EBIT** | Revenue - COGS - OpEx | Operating profit before interest & taxes |
| **EBITDA** | EBIT + D&A | Operating profit before interest, taxes, depreciation |
| **NOPAT** | EBIT × (1 - Tax Rate) | Operating profit after taxes (for all investors) |
| **FCFF** | NOPAT + D&A - CapEx - ΔNWC | Cash available to all investors |
| **WACC** | (E/V)×Ke + (D/V)×Kd×(1-t) | The "hurdle rate" for investments |
| **Ke** | Rf + β × ERP | Required return for equity investors |
| **Kd** | Interest / Debt | Interest rate on company's borrowings |
| **Beta (β)** | Stock volatility vs market | Measure of systematic risk |
| **Rf** | 10-year Treasury yield | Return on a "risk-free" investment |
| **ERP** | Market return - Rf | Extra return for owning stocks |
| **Terminal Value** | FCF × (1+g) / (WACC-g) | Value of all future cash flows after forecast |
| **EV** | PV(FCFs) + PV(TV) | Total value of the business |
| **Equity Value** | EV + Cash - Debt | Value belonging to shareholders |
| **ROIC** | NOPAT / Invested Capital | Return earned on all invested money |
| **FCF Yield** | FCF / EV | Cash return on the enterprise |
| **CAGR** | (End/Start)^(1/n) - 1 | Smoothed annual growth rate |
| **NWC** | Current Assets - Cash - Current Liabilities | Cash tied up in operations |
| **CapEx** | Purchases of PP&E | Cash spent on physical assets |
| **D&A** | Depreciation + Amortization | Non-cash expense for aging assets |

---

## Running the DCF Model

```bash
# Single ticker DCF
python main.py NVDA

# Multiple tickers (each gets its own DCF)
python main.py NVDA AAPL MSFT BLK

# Output location
ls ~/sec_filing_parser/data/NVDA/parsed/*dcf*
```

---

*Generated by SEC Filing Parser v1.0 - Phase 7 DCF Model*
*Methodology based on JP Morgan, Goldman Sachs, and Damodaran frameworks*
