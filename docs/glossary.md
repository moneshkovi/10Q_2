# Glossary — A to Z

All financial and technical terms used in this project, with plain-English definitions
and references to where they appear in the codebase.

---

## A

**ADR (American Depositary Receipt)**
A share in a foreign company that trades on a US stock exchange. AZN (AstraZeneca)
is a UK/Swedish company but its ADR trades on NASDAQ. ADRs are denominated in USD
and file 20-F annual reports (not 10-K) with the SEC.

**Alpaca Markets**
A US broker-dealer and market data provider with a free API tier. We use it exclusively
for current stock prices and historical daily bars (not for trading).
See `src/alpaca_client.py`.

**Amortization**
The gradual expensing of an intangible asset (patent, goodwill, software license)
over its useful life. Similar to depreciation but for non-physical assets.
Non-cash charge → added back when computing FCFF.
See also: D&A.

**Annual Report**
A comprehensive financial filing covering a full fiscal year.
- US companies: Form 10-K
- Foreign companies listed in the US: Form 20-F
We only use annual reports for DCF (not quarterly), to avoid period-mixing errors.

---

## B

**Balance Sheet**
One of the three core financial statements. Shows what a company owns (assets) and
what it owes (liabilities + equity) at a **point in time** (snapshot).

```
Assets = Liabilities + Shareholders' Equity
```

Contrast with the Income Statement (covers a period) and Cash Flow Statement (covers a period).

**Beta (β)**
A measure of a stock's systematic risk — how much it moves relative to the overall market
(measured by SPY / S&P 500). Computed via OLS regression of daily log returns.

```
β = 1.0  →  moves exactly with the market
β > 1.0  →  more volatile (e.g., NVDA ≈ 1.68)
β < 1.0  →  less volatile (e.g., JNJ ≈ 0.60)
β < 0.0  →  moves opposite (rare — e.g., some gold stocks)
```

See `src/alpaca_client.py → calculate_beta()` and `docs/beta_and_capm.md`.

**Book Value of Equity**
Total shareholders' equity from the balance sheet. Distinct from market capitalization
(which uses the current stock price). We use book equity when computing capital structure
weights in WACC, because market cap requires a live price feed.

---

## C

**CAGR (Compound Annual Growth Rate)**
The annual growth rate that would take a value from its starting amount to its ending
amount over a period, assuming compounding.

```
CAGR = (End / Start) ^ (1 / years) - 1
```

We compute CAGR on revenue and FCF over 5 historical years as inputs to the DCF forecast.

**CapEx (Capital Expenditures)**
Cash spent on purchasing or improving physical assets (property, plant, equipment).
Reported on the Cash Flow Statement as a negative number.

```
XBRL tag: PaymentsToAcquirePropertyPlantAndEquipment
```

Note: We store CapEx as a **positive magnitude** and subtract it explicitly.
Sign convention always documented in comments. Never silently flip signs.

**Capital Structure**
How a company finances its operations: the mix of equity (shareholders) and debt (lenders).

```
Capital Structure = Equity + Debt
Weight of Equity = Equity / (Equity + Debt)
Weight of Debt   = Debt   / (Equity + Debt)
```

Affects WACC: more debt → lower WACC (debt has tax shield) but also higher risk.

**CAPM (Capital Asset Pricing Model)**
The standard formula for computing the cost of equity:

```
Ke = Rf + β × ERP
```

See `docs/beta_and_capm.md` for full explanation.

**Cash Flow Statement**
One of the three core financial statements. Shows actual cash flows over a period:
- Operating Activities: Cash from running the business (OCF)
- Investing Activities: Cash from buying/selling assets (CapEx)
- Financing Activities: Cash from debt and equity transactions (dividends, buybacks)

**CIK (Central Index Key)**
The unique identifier SEC assigns to every company. Never changes. Used to fetch
all SEC filings.

```python
# src/sec_client.py
NVDA CIK = "0001045810"
```

**Comparable Company Analysis (Comps)**
A relative valuation method that values a company based on the multiples (EV/EBITDA,
P/E, etc.) of similar publicly traded companies. We do NOT implement comps — our
valuation is DCF only.

**Cost of Debt (Kd)**
The interest rate a company pays on its borrowings. Computed from SEC filings:

```
Kd = Interest Expense / Total Debt
After-tax Kd = Kd × (1 - Tax Rate)   ← interest is tax-deductible
```

**Cost of Equity (Ke)**
The return that equity investors demand for holding the stock. Computed via CAPM:

```
Ke = Rf + β × ERP
```

**Covariance**
A statistical measure of how two variables move together. Used in beta calculation:

```
Cov(stock, market) = average of [(stock_return - stock_mean) × (market_return - market_mean)]
```

Positive covariance: both move in same direction. Negative: opposite directions.

---

## D

**D&A (Depreciation & Amortization)**
A non-cash expense representing the gradual allocation of an asset's cost over time.
Added back when computing FCFF because it doesn't represent real cash leaving the company.

```
XBRL tags: DepreciationDepletionAndAmortization, DepreciationAndAmortization
```

**Damodaran**
Aswath Damodaran, Professor at NYU Stern. The leading academic authority on valuation.
His annual dataset (pages.stern.nyu.edu/~adamodar/) provides the ERP and other inputs
we use. Our ERP = 5.5% comes from his estimate.

**DCF (Discounted Cash Flow)**
A valuation method that estimates a company's intrinsic value as the present value of
all future cash flows, discounted at the company's cost of capital (WACC).

```
Enterprise Value = Σ [FCF_t / (1+WACC)^t] + Terminal Value / (1+WACC)^n
```

See `src/dcf_calculator.py` and `docs/dcf_methodology.md`.

**Diluted Shares Outstanding**
The total number of shares if all dilutive securities (options, RSUs, convertible bonds,
warrants) were exercised. More conservative (higher count → lower per-share value) than
basic shares. We use diluted shares for all per-share calculations.

**Discount Rate**
The rate used to convert future cash flows to present value. In our DCF, the discount
rate is WACC. A higher discount rate → lower present value → lower fair value.

**Discounting**
The process of converting a future value to its present value equivalent:

```
PV = FV / (1 + r)^t

Where r = discount rate (WACC), t = years from now
```

---

## E

**EBIT (Earnings Before Interest and Taxes)**
Operating income — profit from core business before financing and taxes.

```
EBIT = Revenue - COGS - Operating Expenses
XBRL tag: OperatingIncomeLoss
```

Used in the EBIT method for FCFF:
```
FCFF = EBIT × (1 - Tax Rate) + D&A - CapEx - ΔNWC
```

**EBITDA (Earnings Before Interest, Taxes, Depreciation and Amortization)**

```
EBITDA = EBIT + D&A
```

A rough proxy for operating cash generation. Used in the Exit Multiple terminal value method
and in FCF yield calculations. Not a substitute for FCF (ignores CapEx).

**EDGAR**
Electronic Data Gathering, Analysis, and Retrieval — the SEC's public database of all
company filings. Free API at `data.sec.gov`. Primary data source for this project.

**Enterprise Value (EV)**
The total value of a company — equity AND debt.

```
From DCF:
EV = PV(FCFs) + PV(Terminal Value)

From market:
EV = Market Cap + Total Debt - Cash
```

**Equity Risk Premium (ERP)**
The additional return that equity investors demand over the risk-free rate for bearing
stock market risk. We use 5.5% (Damodaran).

```
ERP = Expected market return - Risk-free rate ≈ 9.5% - 4.5% = 5.0-5.5%
```

**Equity Value**
The value belonging to shareholders — what's left after deducting debt from Enterprise Value.

```
Equity Value = Enterprise Value + Cash - Total Debt
Fair Value Per Share = Equity Value / Diluted Shares Outstanding
```

**EV/EBITDA**
A valuation multiple. The ratio of Enterprise Value to EBITDA. Used in the Exit Multiple
terminal value method. Higher multiples = market pays more per dollar of earnings.

---

## F

**FCFF (Free Cash Flow to Firm)**
The cash generated by a company's operations after reinvestment, available to all
capital providers (debt + equity).

Primary method (OCF):
```
FCFF = Operating Cash Flow - CapEx + Interest × (1 - Tax Rate)
```

Fallback method (EBIT):
```
FCFF = EBIT × (1 - Tax Rate) + D&A - CapEx - ΔNWC
```

See `src/dcf_calculator.py` and `docs/dcf_methodology.md`.

**FCFE (Free Cash Flow to Equity)**
FCF available only to equity holders after debt repayments. We use FCFF instead —
see `docs/design_decisions.md #1`.

**FCF Margin**
```
FCF Margin = FCFF / Revenue
```

Measures what fraction of revenue converts to free cash flow. High FCF margins
(>20%) indicate a capital-light, highly profitable business (e.g., software).

**FCF Yield**
```
FCF Yield = FCFF / Enterprise Value
```

How much FCF the company generates relative to its total value. Analogous to a
bond's yield. > 8% often indicates undervaluation.

---

## G

**Gordon Growth Model**
The formula for Terminal Value assuming perpetual constant growth:

```
TV = FCF_n × (1 + g) / (WACC - g)

Where g = perpetual growth rate (capped at GDP growth ≈ 2.5%)
```

Named after Myron Gordon (1959). Also called the "Dividend Discount Model" in
its equity form.

**Gross Margin**
```
Gross Margin = (Revenue - COGS) / Revenue
```

What fraction of revenue remains after direct production costs. Indicates pricing
power and scale benefits.

---

## I

**IFRS (International Financial Reporting Standards)**
The accounting standards used by most non-US listed companies (and all EU companies).
Differs from US-GAAP in several ways (revenue recognition, lease accounting, etc.).
XBRL tags use `ifrs-full:` prefix instead of `us-gaap:`.

AZN files under IFRS. Our code auto-detects the taxonomy.
See `docs/data_sources.md #2`.

**Income Statement (P&L)**
One of the three core financial statements. Shows revenue, expenses, and profit over
a **period of time** (quarter or year).

```
Revenue
- Cost of Goods Sold (COGS)
= Gross Profit
- Operating Expenses (R&D, SG&A)
= EBIT (Operating Income)
- Interest Expense
= Pre-Tax Income
- Income Tax
= Net Income
```

**Invested Capital**
The total amount of money invested in a company by both equity and debt holders.

```
Invested Capital = Equity + Total Debt - Excess Cash
```

Used in ROIC calculation.

---

## K

**Ke (Cost of Equity)**
See Cost of Equity.

**Kd (Cost of Debt)**
See Cost of Debt.

---

## L

**Log Return (Natural Log Return)**
Daily return expressed as natural logarithm of the price ratio:

```
r_t = ln(Price_t / Price_{t-1})
```

Preferred over simple percentage returns for statistical reasons:
- Symmetric (losses and gains are comparable in magnitude)
- Additive over time
- Approximately normally distributed

Used in beta calculation. See `docs/beta_and_capm.md`.

---

## M

**Market Capitalization (Market Cap)**
```
Market Cap = Share Price × Shares Outstanding
```

NOT the same as Enterprise Value. Market cap = equity value only.
EV = market cap + debt - cash.

**Minority Interest**
The portion of a subsidiary not owned by the parent company. If Company A owns 80%
of Subsidiary B, the 20% not owned is "minority interest." Complex edge case not
fully handled in our simple equity bridge.

---

## N

**Net Income**
The "bottom line" — profit after ALL expenses, interest, and taxes.

```
Net Income = Revenue - COGS - OpEx - Interest - Taxes
XBRL: NetIncomeLoss
```

We use Net Income for tax rate calculation but NOT for FCFF (FCFF uses EBIT method
or OCF method to avoid financing effects).

**Net Working Capital (NWC)**
```
NWC = Current Assets (excl. cash) - Current Liabilities
```

Cash tied up in day-to-day operations. An increase in NWC means more cash is tied
up (bad for FCF). Used in the EBIT method for FCFF as ΔNWC.

**NOPAT (Net Operating Profit After Tax)**
```
NOPAT = EBIT × (1 - Tax Rate)
```

Operating profit after taxes, before interest. Available to all capital providers.
Key input to FCFF calculation and ROIC.

---

## O

**OCF (Operating Cash Flow)**
Cash generated from core business operations. Directly from the cash flow statement.

```
XBRL: NetCashProvidedByUsedInOperatingActivities
```

Preferred input for FCFF because it already accounts for NWC changes, D&A, and
non-cash items without separate assembly.

**OLS (Ordinary Least Squares)**
The standard method for fitting a linear regression line through data points by
minimizing the sum of squared errors. Used to compute beta:

```
Minimize: Σ (r_stock_i - α - β × r_market_i)²
Solution: β = Cov(stock, market) / Var(market)
```

See `docs/beta_and_capm.md`.

---

## P

**Premium / Discount**
How the DCF fair value compares to the current market price:

```
Premium / Discount = (Fair Value - Current Price) / Current Price × 100

Positive: stock is UNDERVALUED (fair value > market price — potential buy)
Negative: stock is OVERVALUED (fair value < market price — potential sell)
```

Example: NVDA fair value $151.91, price $174.14 → **-12.8% OVERVALUED**.

**Present Value (PV)**
The value today of a future cash flow, discounted at a given rate.

```
PV = FV / (1 + r)^t
```

---

## R

**Rf (Risk-Free Rate)**
The return on a "risk-free" investment — US 10-year Treasury bond yield.
Used as the baseline in CAPM. Currently 4.5%.

**ROIC (Return on Invested Capital)**
```
ROIC = NOPAT / Invested Capital
```

If ROIC > WACC: company creates value (every invested dollar earns more than it costs).
If ROIC < WACC: company destroys value. Warren Buffett's key metric.

---

## S

**S&P 500**
The index of 500 largest US publicly traded companies. The standard benchmark for
"the market." We use SPY (SPDR S&P 500 ETF) as the market proxy in beta calculation.

**SEC (Securities and Exchange Commission)**
The US regulator that requires all public companies to file financial reports.
All 10-K, 10-Q, 20-F filings are publicly available on EDGAR.

**Sensitivity Analysis**
Running the DCF model with multiple WACC and growth rate combinations to see how
the fair value changes. Presented as a 5×5 matrix (WACC rows × growth rate columns).
Shows the range of plausible fair values given assumption uncertainty.

**Shares Outstanding (Basic vs Diluted)**
- **Basic:** Current actual shares issued
- **Diluted:** Basic + potential shares from options, RSUs, warrants, convertibles

We use diluted shares for per-share calculations. See `design_decisions.md #6`.

**SPY**
SPDR S&P 500 ETF Trust. The market proxy used in beta calculation. Tracks the S&P 500
index. The most liquid ETF in the world by trading volume.

**STARTTLS**
An email protocol command that upgrades a plain TCP connection to an encrypted TLS
connection. Used in our Gmail SMTP setup (`smtp.gmail.com:587`). More secure than
direct SSL (port 465) because the connection starts unencrypted and upgrades.

---

## T

**Tax Shield**
The reduction in taxes from interest expense deductibility. Because interest is
tax-deductible, the effective cost of debt is lower:

```
After-tax cost of debt = Kd × (1 - Tax Rate)
```

This is why companies often carry some debt — it's cheaper than equity on an
after-tax basis.

**Terminal Value (TV)**
The present value of all cash flows beyond the explicit forecast period (after Year 5).
Typically represents 60-80% of total Enterprise Value.

Two methods:
1. Gordon Growth Model: `FCF₅ × (1+g) / (WACC-g)`
2. Exit Multiple: `EBITDA₅ × EV/EBITDA_multiple`

We use the average of both.

**Time Value of Money**
The principle that a dollar today is worth more than a dollar in the future, because
today's dollar can be invested to earn returns. The entire DCF framework rests on this.

**10-K**
Annual report filed by US public companies with the SEC. Contains:
- Audited financial statements (income statement, balance sheet, cash flow statement)
- Management's Discussion and Analysis (MD&A)
- Business overview, risk factors
- XBRL-tagged financial data

**10-Q**
Quarterly report filed by US public companies. Unaudited. We extract data from these
for period lookups but exclude them from DCF historical series (annual-only rule).

**20-F**
Annual report filed by Foreign Private Issuers (non-US companies listed in the US).
Equivalent to a 10-K. May use IFRS instead of US-GAAP. AZN files 20-F.

---

## U

**Unlevered DCF**
DCF that values the firm (enterprise) before debt effects. Uses FCFF (free of financing
decisions) and WACC (which includes the debt tax shield). Contrast with levered DCF
which values only equity using FCFE.

We use unlevered DCF. See `docs/design_decisions.md #1`.

---

## V

**Variance**
Statistical measure of how spread out values are around the mean:

```
Var(x) = Σ (x_i - mean)² / (n - 1)
```

Used in beta calculation: `β = Cov(stock, market) / Var(market)`.

---

## W

**WACC (Weighted Average Cost of Capital)**
The weighted average of the cost of equity and after-tax cost of debt.
The "hurdle rate" — minimum return a company must earn to justify its existence.

```
WACC = (E/V) × Ke + (D/V) × Kd × (1 - Tax Rate)

Where:
  Ke = Cost of Equity (CAPM)
  Kd = Cost of Debt
  E  = Equity
  D  = Debt
  V  = E + D
```

The discount rate for all future cash flows in the DCF.

**Working Capital**
See Net Working Capital (NWC).

---

## X

**XBRL (eXtensible Business Reporting Language)**
The XML-based markup language used to tag financial data in SEC filings.
Makes financial data machine-readable with standardized concept names.

```
Revenue → us-gaap:Revenues  (US companies)
Revenue → ifrs-full:Revenue  (foreign IFRS filers)
```

The SEC XBRL API (`data.sec.gov/api/xbrl/companyfacts/`) provides all XBRL data
for any filing in one JSON response. This is our primary data source.
See `docs/data_sources.md`.

---

## Y

**YoY (Year-over-Year)**
Comparing a metric from one year to the same metric from the prior year.

```
YoY Growth = (Current Year - Prior Year) / Prior Year × 100
```

Computed for all extracted metrics in Phase 3. Helps identify trends and anomalies.

---

*All financial formulas follow CFA Institute, Damodaran, and JP Morgan equity research conventions.*
