# Beta and CAPM — From Scratch

This document explains **beta**, the **Capital Asset Pricing Model (CAPM)**, and how
we compute beta using **Ordinary Least Squares (OLS) regression** from Alpaca price data.
No prior statistics knowledge is assumed.

---

## Part 1: What is Beta?

### The Core Idea

If the stock market drops 10% today, how much does YOUR stock drop?

- If it drops **exactly 10%** → your stock moves with the market → **beta = 1.0**
- If it drops **20%** → your stock is twice as sensitive → **beta = 2.0**
- If it drops **5%** → your stock is half as sensitive → **beta = 0.5**
- If it **rises 10%** when the market falls 10% → **beta = -1.0** (rare, like gold)

Beta measures **systematic risk** — the portion of your stock's risk that comes
from broad market movements, not from the company itself.

### Types of Risk

```
Total Risk = Systematic Risk + Unsystematic Risk
                 (beta)          (company-specific)

Systematic Risk:   Cannot be diversified away — affects ALL stocks
  Examples: Interest rate changes, recessions, geopolitical events

Unsystematic Risk: CAN be diversified away — affects ONE company
  Examples: CEO scandal, product recall, one earnings miss
```

**Why this distinction matters:** Modern portfolio theory says investors are only
compensated for taking **systematic risk** (beta), not for unsystematic risk. You
can eliminate unsystematic risk for free by owning many stocks. Therefore the
discount rate (cost of equity) only includes systematic risk.

### Beta Values in Context

| Company | Beta | Why |
|---------|------|-----|
| NVDA | ~1.65 | AI/chip demand highly cyclical, growth stock |
| TSLA | ~2.20 | Very volatile, growth + speculative positioning |
| AAPL | ~1.20 | Large cap tech, some defensive characteristics |
| MSFT | ~0.95 | Mature enterprise software, relatively stable |
| JNJ | ~0.60 | Healthcare/consumer staples — people buy medicine in recessions |
| PG | ~0.45 | Soap and detergent — "no beta" defensive |
| Gold (GLD) | ~-0.10 | Flight-to-safety asset, often rises when market falls |

---

## Part 2: The Capital Asset Pricing Model (CAPM)

### The Formula

```
Ke = Rf + β × ERP

Where:
  Ke  = Cost of Equity (the return investors DEMAND for owning this stock)
  Rf  = Risk-Free Rate (10-year US Treasury yield — what you get for zero risk)
  β   = Beta (systematic risk of this stock)
  ERP = Equity Risk Premium (extra return demanded for owning stocks vs bonds)
```

### Every Term Explained

#### Risk-Free Rate (Rf) = 4.5%
The US 10-year Treasury bond is considered the closest thing to a "risk-free" investment
because the US government has never defaulted. It's the baseline return.

If you can earn 4.5% with ZERO risk, any risky investment must earn MORE than 4.5%
or rational investors would just buy Treasury bonds instead.

#### Equity Risk Premium (ERP) = 5.5%
The average extra return that stocks have provided over bonds, historically.
Over the last 100 years, US stocks have returned about 9-10%/year while bonds
returned about 4-5%. The difference (~5.5%) is the ERP.

Source: Aswath Damodaran (NYU Stern) — the leading academic authority on this.
Updated annually at: `pages.stern.nyu.edu/~adamodar/`

#### Beta (β) — computed from Alpaca data
See Part 3 for the calculation.

### Example: NVIDIA Cost of Equity

```
Rf  = 4.5%
β   = 1.68  (computed from 252 days of Alpaca daily bars vs SPY)
ERP = 5.5%

Ke = 4.5% + 1.68 × 5.5%
   = 4.5% + 9.24%
   = 13.74%

This means: NVDA investors demand a 13.74% annual return.
If the stock is not expected to return at least 13.74%, rational investors sell it.
```

### Why CAPM? (Alternatives Exist)

CAPM is one of several models for cost of equity:

| Model | Formula | Used When |
|-------|---------|-----------|
| **CAPM** (we use this) | Rf + β × ERP | Standard equity research |
| Fama-French 3-factor | Adds size + value factors | Academic research |
| Build-up method | Rf + ERP + size + company risk | Private companies |
| Dividend discount | D1 / P0 + g | Dividend-paying mature companies |

CAPM is the **industry standard** at investment banks for public equity valuation.
JP Morgan, Goldman Sachs, and Morgan Stanley use CAPM in their equity research.
We use it because it is simple, transparent, and widely accepted.

---

## Part 3: Computing Beta from Price Data (OLS Regression)

### The Mathematical Relationship

Beta is defined as:

```
β = Cov(r_stock, r_market) / Var(r_market)

Where:
  r_stock  = daily return of the stock
  r_market = daily return of the market (we use SPY = S&P 500 ETF)
  Cov      = Covariance (how the two move together)
  Var      = Variance of the market (how much the market itself moves)
```

This is equivalent to running an **OLS (Ordinary Least Squares) linear regression**:

```
r_stock = α + β × r_market + ε

Where:
  α = alpha (the "intercept" — returns not explained by the market)
  β = beta (the "slope" — sensitivity to market movements)
  ε = error term (random noise)
```

### Why Daily Log Returns (not price levels)

We don't use raw prices. We use **log returns**:

```python
r_t = ln(close_t / close_{t-1})  # natural log of price ratio
```

**Why log returns?**
1. **Symmetry:** A 10% gain followed by a 10% loss is symmetric in log returns
   (whereas in percentage returns: 100 → 110 → 99, a net loss)
2. **Additivity:** Log returns add up across time periods correctly
3. **Normality:** Log returns are approximately normally distributed — a key
   assumption of OLS regression
4. **Stationarity:** Price levels trend upward forever (non-stationary), while
   daily returns fluctuate around zero (stationary)

### Step-by-Step Beta Calculation

Here's exactly what `AlpacaClient.calculate_beta()` does:

```python
# Step 1: Fetch 252 trading days of daily bars for both tickers
stock_bars = self.get_historical_bars("NVDA", lookback_days=365)
spy_bars   = self.get_historical_bars("SPY",  lookback_days=365)

# Step 2: Build price series indexed by date (to handle missing dates)
stock_prices = {bar["t"][:10]: bar["c"] for bar in stock_bars}
spy_prices   = {bar["t"][:10]: bar["c"] for bar in spy_bars}

# Step 3: Find the INTERSECTION of dates (both must have data that day)
common_dates = sorted(set(stock_prices) & set(spy_prices))
# Markets close on different holidays sometimes — intersection handles this

# Step 4: Compute daily log returns for each asset
# For each consecutive pair of dates:
r_stock = [ln(stock_prices[d2] / stock_prices[d1]) for d1, d2 in pairs]
r_spy   = [ln(spy_prices[d2]   / spy_prices[d1])   for d1, d2 in pairs]

# Step 5: Compute OLS beta from scratch (no numpy, pure Python)
n    = len(r_stock)
mean_stock = sum(r_stock) / n
mean_spy   = sum(r_spy)   / n

# Covariance = average of (stock_deviation × spy_deviation)
cov = sum((r_stock[i] - mean_stock) * (r_spy[i] - mean_spy)
          for i in range(n)) / (n - 1)

# Variance = average of (spy_deviation²)
var = sum((r_spy[i] - mean_spy)**2 for i in range(n)) / (n - 1)

beta = cov / var

# Step 6: Sanity check — clamp to reasonable range
beta = max(-1.0, min(5.0, beta))
```

### Why 252 Trading Days?

252 is the approximate number of trading days in a US calendar year
(365 days × 5/7 weekdays × adjustment for holidays ≈ 252).

Using 1 year of daily data is the **industry standard** for beta estimation:
- Too short (< 30 days): beta is statistically unreliable
- Too long (> 5 years): beta reflects the company's past, not its current risk profile

We return `None` if there are fewer than 30 overlapping trading days — not enough
data to produce a meaningful beta.

### Why SPY as the Market Proxy?

SPY is the SPDR S&P 500 ETF — the most liquid and widely held index fund in the world.
It tracks the S&P 500, which is the standard definition of "the market" in US finance.

Alternatives:
- **VTI** (total US market): More stocks, slightly different results
- **QQQ** (NASDAQ 100): Too tech-heavy — biases betas of tech stocks downward
- **SPY** (S&P 500): **Industry standard** — used by Bloomberg, FactSet, academic papers

### Beta vs Sector Lookup (Fallback)

When Alpaca data is unavailable (API down, key not configured, fewer than 30 data points),
we fall back to `config.DCF_INDUSTRY_BETAS`:

```python
DCF_INDUSTRY_BETAS = {
    "NVDA": 1.65, "AMD": 1.60, "INTC": 0.95,
    "AAPL": 1.20, "MSFT": 0.95, "GOOG": 1.05,
    "DEFAULT": 1.0,
}
```

The result dict includes a `beta_source` field so you always know which was used:
- `"computed"` → Alpaca OLS regression
- `"sector_lookup"` → config.py fallback table

---

## Part 4: Beta in the WACC Calculation

Once we have beta, it flows through to WACC:

```
Beta (computed or sector lookup)
  ↓
Cost of Equity = Rf + β × ERP
  ↓
WACC = (E/V) × Ke + (D/V) × Kd × (1 - t)
  ↓
Discount rate for all future DCF cash flows
  ↓
DCF Fair Value per Share
```

**Impact of beta on fair value (holding everything else constant):**

| Beta | Cost of Equity | WACC (approx) | Fair Value Impact |
|------|---------------|---------------|-------------------|
| 0.50 | 7.25% | ~7.5% | High — future cash flows discounted less |
| 1.00 | 10.00% | ~10.2% | Baseline |
| 1.50 | 12.75% | ~13.0% | Lower — future cash flows heavily discounted |
| 2.00 | 15.50% | ~15.7% | Much lower |

A 1-point increase in beta raises the cost of equity by 5.5% (= 1 × ERP),
which can easily change fair value by 20-40%.

---

## Part 5: Common Questions

### "Isn't using historical beta to predict future risk circular?"

Yes, and this is a known limitation of CAPM. Beta is **backward-looking** by definition.
A company that restructures, pivots, or changes its leverage ratio will have a different
future beta. This is why professional analysts often adjust the raw ("raw") beta toward 1.0
(called "adjusted beta" or "Blume adjustment"):

```
Adjusted Beta = 0.67 × Raw Beta + 0.33 × 1.0
```

We don't apply the Blume adjustment — we use raw beta for simplicity and transparency.

### "What if there's not enough data?"

`calculate_beta()` returns `None` if:
- Alpaca keys are not configured (`enabled = False`)
- Either ticker returns < 30 common trading days
- Any exception occurs during fetch or calculation

The pipeline then falls back to `DCF_INDUSTRY_BETAS`. This is always logged.

### "Why do we compute beta instead of just looking it up?"

Services like Bloomberg and FactSet publish beta. But:
- They require paid subscriptions
- Their methodology may differ (weekly vs daily, 1yr vs 5yr, adjustments applied)
- Computing it ourselves gives us **full transparency** and **traceable methodology**

For a study project, understanding *how* beta is computed is more valuable than
getting a pre-packaged number.
