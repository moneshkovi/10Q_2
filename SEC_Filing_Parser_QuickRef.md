# SEC Filing Parser - Quick Reference & Implementation Cheat Sheet

**This is a companion to the main specification document.**

---

## QUICK ANSWERS TO COMMON QUESTIONS

### Q: What's the difference between XBRL and PDF extraction?

**XBRL (eXtensible Business Reporting Language):**
- Machine-readable XML format filed with 10-K/10-Q
- Like: Database dump of financial data
- Accuracy: ~99% (directly from filer's accounting system)
- Coverage: Most large-cap companies (mandate from SEC)
- Speed: Fast (just XPath queries)
- Example: `<us-gaap:Revenues>130500000000</us-gaap:Revenues>`

**PDF Extraction:**
- Human-readable PDF document (the official filing)
- Like: Reading a financial statement off a printout
- Accuracy: ~95% (OCR + pattern matching errors)
- Coverage: 100% (all companies file PDF)
- Speed: Slow (text extraction + regex matching)
- Example: Parse "Revenue 130,500" from PDF page 42

**Strategy:** Use XBRL if available (faster, cleaner). PDF as backup. Reconcile both. Flag differences >5%.

---

### Q: What's a "free API" for financial data?

**Truly Free (No API key needed, no signup):**
- SEC Edgar (official filing search): `https://data.sec.gov/submissions/CIK{cik}/`
- Yahoo Finance (deprecated but still works via scraping): Limited reliability
- AlphaVantage (free tier): 5 requests/min, 500/day limit
- IEX Cloud (free tier): Very limited; mostly deprecated
- FRED (Federal Reserve): Economic data, not company financials

**What we'll use:**
- SEC Edgar API (primary) — 100% free, unlimited, official
- Polygon.io (if you get free token later) — supplement only
- IEX Cloud (free tier) — last resort for stock prices

**What we'll avoid:**
- Bloomberg Terminal: $24k/year
- FactSet: $15k+/year
- Refinitiv Eikon: $20k+/year

---

### Q: How do I validate a ticker → CIK mapping?

Three-step validation:
```python
# Step 1: Query SEC EDGAR API
cik_from_ticker = sec_client.get_cik_from_ticker("NVDA")
# Response: "1045810"

# Step 2: Fetch company metadata
company_info = sec_client.get_company_info(cik_from_ticker)
# Response: {"name": "NVIDIA Corporation", "exchange": "NASDAQ", "cik": "1045810"}

# Step 3: Verify ticker matches
if company_info.get("exchange") != "NYSE":
    print("WARNING: Ticker {ticker} is {exchange}, not NYSE")
    # Ask user to confirm, or reject
```

**Why validate?** Ticker symbols can change, companies can move exchanges, tickers can be reused.

---

### Q: What if a 10-K or 10-Q doesn't exist for a year?

**Typical scenarios:**

1. **Company too young:** Founded in 2024, no 10-K yet
   - Action: Log as "FILING_DOES_NOT_EXIST", continue with earlier years

2. **Filing delayed:** Company filed extension (8-K with note)
   - Action: Check filing metadata for "delayed flag", wait/skip, log timestamp

3. **Ticker changed:** Company was acquired, name changed, spun off
   - Action: Cross-reference with SEC filing history, use old CIK if relevant

4. **Financials not yet released:** 10-K for FY2025 won't be filed until Jan 2026
   - Action: Use most recent available filing, note in metadata

**Always check filing date vs fiscal period end:**
```
Fiscal Year 2025 ends: Jan 26, 2025
10-K must file by: Mar 31, 2025 (60 days after FY end)
Today is: Feb 23, 2026

=> 10-K should definitely exist and be available
```

---

### Q: How do I extract data from XBRL without parsing errors?

**XBRL Structure (simplified):**
```xml
<xbrli:xbrl>
  <context id="FY2025">
    <xbrli:instant>2025-01-26</xbrli:instant>
  </context>
  
  <us-gaap:Revenues contextRef="FY2025" unitRef="USD">
    130500000000
  </us-gaap:Revenues>
</xbrli:xbrl>
```

**Safe extraction pattern:**
```python
def safe_extract(xbrl_tree, concept: str, fiscal_date: str):
    """
    Safely extract value, handling edge cases.
    """
    
    # Find concept in document
    elements = xbrl_tree.findall(f".//{concept}")
    
    if not elements:
        return None, "NOT_FOUND"
    
    # Multiple matches? Pick by date context
    matching = [e for e in elements 
                if e.get("contextRef") contains fiscal_date]
    
    if len(matching) > 1:
        return None, "AMBIGUOUS_MULTIPLE_CONTEXTS"
    
    if len(matching) == 0:
        return None, "NO_MATCHING_DATE_CONTEXT"
    
    value = matching[0].text
    
    # Validate
    if not value.isdigit():
        return None, f"NOT_NUMERIC: {value}"
    
    return int(value), "SUCCESS"
```

**Common XBRL issues:**
- Units: USD vs shares vs percentages (check `unitRef`)
- Decimals: Some concepts are already in thousands (check inline XBRL notes)
- Negative values: Marked as text (e.g., "(100)" = -100)
- Missing items: Segment data might not have XBRL (check MD&A instead)

---

### Q: How do I handle PDF extraction errors?

**PDF Extraction Challenges:**
- Multi-column layouts (confusing text order)
- Headers/footers repeating
- Tables with complex structures
- Fonts that don't OCR well
- Handwritten notes (rare, but exists)

**Safe approach:**
```python
def extract_with_fallback(pdf_path):
    """
    Extract from PDF with multiple strategies.
    """
    
    try:
        # Strategy 1: Use pdfplumber for table detection
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # Try to find tables
                tables = page.extract_tables()
                if tables:
                    return parse_tables(tables), "TABLE_EXTRACTION"
    except:
        pass
    
    try:
        # Strategy 2: Extract all text, use regex
        text = extract_text_from_pdf(pdf_path)
        metrics = regex_extract(text)
        return metrics, "REGEX_EXTRACTION"
    except:
        pass
    
    # Strategy 3: Give up, flag for manual review
    return None, "EXTRACTION_FAILED"
```

**Mark confidence levels:**
- HIGH: XBRL with single unambiguous context
- MEDIUM: PDF extraction with regex confidence >95%
- LOW: Multiple possible values, manual interpretation needed

---

### Q: What should I put in the XML output?

**Minimum viable XML (from your requirements):**

```xml
<Filing>
  <!-- 1. Metadata (so you know what year/quarter) -->
  <Metadata>
    <Ticker>NVDA</Ticker>
    <FiscalPeriodEnd>2025-01-26</FiscalPeriodEnd>
    <FilingType>10-K</FilingType>
    <FilingDate>2025-03-20</FilingDate>
  </Metadata>

  <!-- 2. Every Financial Statement Line Item -->
  <FinancialStatements>
    <IncomeStatement>
      <Revenue>130500000000</Revenue>
      <CostOfRevenue>29050000000</CostOfRevenue>
      <GrossProfit>101450000000</GrossProfit>
      <ResearchAndDevelopment>7720000000</ResearchAndDevelopment>
      <SellingGeneralAdmin>3480000000</SellingGeneralAdmin>
      <OperatingIncome>81250000000</OperatingIncome>
      <InterestExpense>350000000</InterestExpense>
      <OtherIncome>500000000</OtherIncome>
      <PreTaxIncome>81400000000</PreTaxIncome>
      <IncomeTaxExpense>20478000000</IncomeTaxExpense>
      <NetIncome>60922000000</NetIncome>
      <EPS_Diluted>2.94</EPS_Diluted>
    </IncomeStatement>
    
    <BalanceSheet>
      <!-- Assets -->
      <Cash>24100000000</Cash>
      <MarketableSecurities>12500000000</MarketableSecurities>
      <AccountsReceivable>9800000000</AccountsReceivable>
      <Inventory>13200000000</Inventory>
      <CurrentAssets>59600000000</CurrentAssets>
      <PPE_Gross>45600000000</PPE_Gross>
      <AccumulatedDepreciation>-8900000000</AccumulatedDepreciation>
      <PPE_Net>36700000000</PPE_Net>
      <Goodwill>85000000000</Goodwill>
      <IntangibleAssets_Net>53700000000</IntangibleAssets_Net>
      <OtherAssets>74900000000</OtherAssets>
      <TotalAssets>309900000000</TotalAssets>
      
      <!-- Liabilities -->
      <AccountsPayable>5400000000</AccountsPayable>
      <AccruedExpenses>8600000000</AccruedExpenses>
      <CurrentDebt>0</CurrentDebt>
      <CurrentLiabilities>14000000000</CurrentLiabilities>
      <LongTermDebt>10500000000</LongTermDebt>
      <DeferredTaxLiabilities>8500000000</DeferredTaxLiabilities>
      <OtherLiabilities>45500000000</OtherLiabilities>
      <TotalLiabilities>78500000000</TotalLiabilities>
      
      <!-- Equity -->
      <CommonStock>24400000000</CommonStock>
      <APIC>2100000000</APIC>
      <RetainedEarnings>207000000000</RetainedEarnings>
      <OtherComprehensiveIncome>-1600000000</OtherComprehensiveIncome>
      <TotalEquity>231400000000</TotalEquity>
    </BalanceSheet>
    
    <CashFlowStatement>
      <!-- Operating -->
      <NetIncome>60922000000</NetIncome>
      <Depreciation>2800000000</Depreciation>
      <Amortization>1200000000</Amortization>
      <StockBasedCompensation>4800000000</StockBasedCompensation>
      <DeferredTaxes>-600000000</DeferredTaxes>
      <WorkingCapitalChanges>2178000000</WorkingCapitalChanges>
      <OperatingCashFlow>71700000000</OperatingCashFlow>
      
      <!-- Investing -->
      <CapitalExpenditures>-3200000000</CapitalExpenditures>
      <AcquisitionsBuybacks>-1500000000</AcquisitionsBuybacks>
      <InvestingCashFlow>-2800000000</InvestingCashFlow>
      
      <!-- Financing -->
      <StockRepurchases>-44800000000</StockRepurchases>
      <DividendsPaid>-125000000</DividendsPaid>
      <DebtIssuanceRepayment>-1200000000</DebtIssuanceRepayment>
      <FinancingCashFlow>-46125000000</FinancingCashFlow>
    </CashFlowStatement>
  </FinancialStatements>

  <!-- 3. Segment Performance (if exists) -->
  <Segments>
    <Segment name="Data Center">
      <Revenue>119616000000</Revenue>
      <GrossMargin>0.72</GrossMargin>
    </Segment>
    <Segment name="Gaming">
      <Revenue>5100000000</Revenue>
      <GrossMargin>0.58</GrossMargin>
    </Segment>
  </Segments>

  <!-- 4. Risk Factors (top 5-10) -->
  <RiskFactors>
    <Risk priority="1">Customer Concentration - Data Center</Risk>
    <Risk priority="2">Manufacturing in Taiwan</Risk>
    <Risk priority="3">Export Controls (China)</Risk>
  </RiskFactors>

  <!-- 5. Data Quality & Flags -->
  <DataQuality>
    <Discrepancies>0</Discrepancies>
    <MissingItems>0</MissingItems>
    <FlagsForReview>false</FlagsForReview>
  </DataQuality>

  <!-- 6. Audit Trail -->
  <AuditTrail>
    <Sources>XBRL + PDF</Sources>
    <ExtractionDate>2025-02-23T10:25:00Z</ExtractionDate>
    <Confidence>0.99</Confidence>
  </AuditTrail>
</Filing>
```

**Pro tip:** Include confidence scores and data sources. Makes future debugging 10x easier.

---

### Q: What metrics should I calculate/derive?

**Key calculated metrics (from raw data):**

| Metric | Formula | Why Important |
|--------|---------|---------------|
| Gross Margin | (Revenue - COGS) / Revenue | Pricing power |
| Operating Margin | Operating Income / Revenue | Operational efficiency |
| Net Margin | Net Income / Revenue | Bottom-line profitability |
| Current Ratio | Current Assets / Current Liabilities | Short-term solvency |
| Quick Ratio | (Cash + Receivables) / Current Liabilities | Ultra-conservative liquidity |
| Debt-to-Equity | Total Debt / Total Equity | Leverage level |
| Interest Coverage | EBIT / Interest Expense | Can they service debt? |
| ROE | Net Income / Avg Equity | Return for shareholders |
| ROA | Net Income / Avg Assets | Return on all assets |
| Asset Turnover | Revenue / Avg Assets | Efficiency of asset use |
| Free Cash Flow | Operating CF - CapEx | Cash available to investors |
| FCF Margin | FCF / Revenue | Quality of earnings |
| Days Sales Outstanding | (AR / Revenue) × 365 | How fast they collect |
| Days Inventory | (Inventory / COGS) × 365 | How fast they sell inventory |
| Days Payable | (AP / COGS) × 365 | How long they pay suppliers |

**Implement these as separate `<CalculatedMetrics>` section in XML** — don't mix with raw data.

---

### Q: How do I flag something "for review"?

**Flag Levels (in your code):**

```python
class FlagLevel(Enum):
    INFO = 1      # Just noting something interesting
    WARNING = 2   # Possible data issue, should check
    ERROR = 3     # Data likely wrong, must review
    CRITICAL = 4  # Stop the pipeline, human intervention required

# Examples:
flag_info = {
    "level": FlagLevel.INFO,
    "metric": "Revenue",
    "message": "Margin expanded 200 bps YoY",
    "priority": "MEDIUM",
    "action": "Review trend analysis"
}

flag_warning = {
    "level": FlagLevel.WARNING,
    "metric": "Customer A Revenue",
    "message": "Customer concentration at 25% of total revenue",
    "priority": "HIGH",
    "action": "Cross-check with MD&A disclosures"
}

flag_error = {
    "level": FlagLevel.ERROR,
    "metric": "OperatingCashFlow",
    "message": "PDF extraction shows 70B, XBRL shows 65B (7.2% difference)",
    "priority": "CRITICAL",
    "action": "Manual review required before proceeding"
}
```

**Save all flags to the XML:**
```xml
<DataQuality>
  <Discrepancies count="1">
    <Item priority="CRITICAL">
      <Metric>OperatingCashFlow</Metric>
      <XBRLValue>65000000000</XBRLValue>
      <PDFValue>70000000000</PDFValue>
      <DifferencePct>7.2</DifferencePct>
      <FlagForManualReview>true</FlagForManualReview>
      <ResolutionSteps>
        1. Download PDF from SEC Edgar
        2. Go to Consolidated Cash Flow Statement
        3. Look for "Net Cash from Operating Activities"
        4. Reconcile with XBRL value
        5. Update XML with correct value
      </ResolutionSteps>
    </Item>
  </Discrepancies>
</DataQuality>
```

---

### Q: How do I test this before running on real data?

**Test plan (Phase 0):**

```python
# test_sec_client.py
def test_ticker_validation():
    """Test ticker → CIK mapping"""
    assert SECClient().get_cik_from_ticker("NVDA") == "1045810"
    assert SECClient().get_cik_from_ticker("AAPL") == "0000320193"
    
    # Invalid tickers should raise
    with pytest.raises(TickerNotFoundError):
        SECClient().get_cik_from_ticker("INVALID")

def test_filing_download():
    """Test PDF download"""
    result = SECClient().download_filing_pdf(
        accession="0001045810-25-000023",
        output_path="/tmp/test.pdf"
    )
    assert result.exists()
    assert result.stat().st_size > 1000000  # > 1MB

def test_xbrl_parsing():
    """Test XBRL extraction"""
    xbrl_data = XBRLParser().parse_filing(
        xbrl_url="https://...",
        filing_date="2025-01-26"
    )
    assert xbrl_data["revenue"] > 100000000000  # > $100B
    assert xbrl_data["confidence"]["revenue"] == "HIGH"

def test_pdf_extraction():
    """Test PDF text extraction"""
    pdf_data = PDFExtractor().extract_from_pdf(
        pdf_path="/tmp/test.pdf"
    )
    # Should have extracted something
    assert len(pdf_data) > 0
    assert "revenue" in pdf_data.lower()

def test_reconciliation():
    """Test XBRL vs PDF reconciliation"""
    xbrl = {"revenue": 130500000000}
    pdf = {"revenue": 130502000000}
    
    reconciled = DataReconciler().reconcile(xbrl, pdf, "2025-01-26")
    
    # Should flag small difference
    assert len(reconciled["discrepancies"]) == 1
    assert reconciled["discrepancies"][0]["difference_pct"] < 1
    assert not reconciled["discrepancies"][0]["flag_for_review"]

def test_xml_generation():
    """Test XML output"""
    data = {
        "revenue": 130500000000,
        "net_income": 60922000000,
        ...
    }
    
    xml = XMLBuilder().build(data, metadata={...})
    
    # Should be valid XML
    assert xml is not None
    assert xml.find(".//Revenue") is not None
    assert xml.find(".//Revenue").text == "130500000000"
```

**Run tests before deploying:**
```bash
python -m pytest tests/ -v
# Should see: PASSED 30/30
```

---

## KEY FILE LOCATIONS

```
~/sec_filing_parser/
├── main.py                         # Run this: python main.py NVDA
├── config.py                       # Edit: API keys, paths
├── requirements.txt                # Install: pip install -r requirements.txt
├── src/
│   ├── sec_client.py              # Fetches from SEC
│   ├── xbrl_parser.py             # Parses XBRL XML
│   ├── pdf_extractor.py           # Extracts from PDF
│   ├── data_reconciler.py         # Compares sources
│   └── xml_builder.py             # Generates output
├── tests/
│   ├── test_sec_client.py
│   ├── test_xbrl_parser.py
│   └── test_integration.py
└── data/
    └── NVDA/
        ├── raw/                    # PDFs you downloaded
        ├── parsed/                 # XMLs you generated
        └── logs/                   # Processing logs
```

---

## GOTCHAS & EDGE CASES

1. **Stock splits affect historical data.** XBRL handles this; make sure you note it.
2. **Fiscal year end varies by company.** Not all end on Dec 31 (NVDA ends in January).
3. **Acquisitions cause balance sheet jumps.** Goodwill spikes; not organic growth.
4. **Segment data not always in XBRL.** Check MD&A text if concept not in machine-readable format.
5. **Negative numbers in PDF.** Might be "(100)" instead of "-100"; regex carefully.
6. **Unit conversions.** Balance sheet might be in thousands, income in millions. Check XBRL unitRef.
7. **Multiple contexts.** Same metric for different periods (YTD vs quarter). Pick right context.
8. **Missing 10-Qs.** Smaller filers file 10-K only. Don't assume all quarters exist.

---

## SUCCESS CRITERIA

- ✅ Can input any NYSE ticker
- ✅ Fetches 3 years of 10-K + 10-Q
- ✅ Saves PDFs locally
- ✅ Generates XML with all financials
- ✅ Flags discrepancies (all <1% differences reconciled)
- ✅ XML is auditable (includes sources)
- ✅ Process takes <2 min per ticker
- ✅ Handles missing filings gracefully

---

## NEXT STEPS AFTER BUILD

Once XML is generated:

1. **Trend Analysis:** Load 3 years of XMLs, calculate YoY growth rates
2. **Fundamental Score:** Weight metrics (profitability, growth, health)
3. **Valuation:** Compare to stock price (need to fetch stock data separately)
4. **Red Flags:** Margin compression, debt spike, customer concentration
5. **Trade Signals:** Combine with technical analysis, backtest

---

Good luck! Feel free to iterate.
