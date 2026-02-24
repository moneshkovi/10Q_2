# SEC Filing Parser & Fundamental Analysis Algorithm
## Technical Specification Document

**Document Version:** 1.0  
**Author Perspective:** Algorithmic Trader + MBA (Harvard)  
**Last Updated:** February 23, 2026  
**Status:** Design Phase - Ready for Implementation

---

## EXECUTIVE SUMMARY

This document outlines a robust, manual-review-friendly Python algorithm that fetches SEC 10-K and 10-Q filings for any NYSE ticker, parses financial data into structured XML, and flags discrepancies for human validation. The system prioritizes **data integrity** and **auditability** over speed, recognizing that in quantitative investing, a single incorrect data point can invalidate an entire trading thesis.

**Core Philosophy:**
- "Trust but verify" — all automated extraction must be reviewable
- PDF as source of truth for manual verification
- XML as single source of truth for downstream analysis
- Fail safely — better to flag uncertainty than introduce garbage data

---

## GOAL

Build a **ticker-to-XML pipeline** that:

1. **Retrieves** the most recent 3 fiscal years of 10-K filings + corresponding quarterly 10-Qs from SEC Edgar
2. **Stores** raw PDFs locally for manual spot-checking
3. **Parses** all material financial metrics (balance sheet, income statement, cash flow, segment data, customer concentration, debt details, etc.) into structured XML
4. **Flags** any parsing uncertainties, missing data, or anomalies requiring human review
5. **Enables** downstream trend analysis without touching the source PDFs again
6. **Handles** edge cases gracefully (delayed filings, non-existent filings, ticker mismatches)

**Success Metrics:**
- ✅ Achieves 98%+ accuracy on major line items (verified via manual spot-checks)
- ✅ All uncertainties flagged for review (zero silent failures)
- ✅ Process takes <2 minutes per ticker for cached tickers
- ✅ XML is self-documenting and auditable

---

## METHODS & ARCHITECTURE

### 1. DATA SOURCES

**Primary Sources (Free, No Auth Required):**

| Source | Purpose | Format | Reliability |
|--------|---------|--------|-------------|
| SEC Edgar API | Filings index, metadata | JSON/Text | 99.9% uptime |
| SEC Edgar XBRL | Structured financial data | XML (XBRL format) | High, but not all filers use it |
| PDF from Edgar | Raw filing document | PDF | Source of truth |
| IEX Cloud (Free Tier) | Stock price, basic metrics | JSON | 99% uptime, rate limited |

**Data Hierarchy (Trustworthiness):**
1. **XBRL data from SEC** (most reliable — machine-readable from filer)
2. **10-K/10-Q PDF text** (human-readable, official)
3. **IEX Cloud supplement** (for ratios, price data; flagged as non-SEC-sourced)

### 2. SYSTEM ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INPUT                                │
│              (NYSE Ticker Symbol)                            │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
   ┌──────────────┐      ┌─────────────────┐
   │ Validate     │      │ Check Local     │
   │ Ticker       │      │ Cache           │
   │ (NYSE only)  │      │ (age <30 days)  │
   └──────┬───────┘      └────────┬────────┘
          │                       │
          │                   ┌───┴────┐
          │                   │ CACHE   │
          │                   │ HIT?    │
          │                   └───┬────┘
          │                       │
          ▼                       ▼
   ┌──────────────────────────────────────┐
   │   SEC Edgar API: Get CIK, Filings    │
   │   - Validate ticker → CIK mapping    │
   │   - Retrieve 10-K & 10-Q metadata    │
   │   - Handle: ticker not found         │
   └──────┬───────────────────────────────┘
          │
   ┌──────┴─────────────────────────────┐
   │   Download Latest 3 Years:          │
   │   - 3x 10-K filings (annual)        │
   │   - Up to 12x 10-Q filings (quarterly)
   │   - Save PDFs locally               │
   │   - Handle: missing/delayed filings │
   └──────┬─────────────────────────────┘
          │
   ┌──────┴──────────────────────────────┐
   │  Extract Data via Parallel Methods:  │
   │  1. XBRL Parser (if available)       │
   │  2. PDF Text Extraction (OCR backup) │
   │  3. SEC Edgar Concept API (validation)
   └──────┬──────────────────────────────┘
          │
   ┌──────┴──────────────────────────────┐
   │  Normalize & Reconcile Data:         │
   │  - Reconcile XBRL vs PDF extraction │
   │  - Flag discrepancies for review     │
   │  - Convert to standard units         │
   │  - Calculate derived metrics         │
   └──────┬──────────────────────────────┘
          │
   ┌──────┴──────────────────────────────┐
   │  Generate Structured XML:            │
   │  - Financial statements              │
   │  - Segment data                      │
   │  - Risk factors                      │
   │  - Audit trail of all sources        │
   │  - Uncertainty flags                 │
   └──────┬──────────────────────────────┘
          │
   ┌──────┴──────────────────────────────┐
   │  Save Outputs:                       │
   │  - XML: ~/data/{TICKER}/parsed/      │
   │  - PDFs: ~/data/{TICKER}/raw/        │
   │  - Log: ~/data/{TICKER}/log/         │
   │  - Report: flags for review          │
   └──────┬──────────────────────────────┘
          │
          ▼
    ┌──────────────────────┐
    │   READY FOR ANALYSIS │
    └──────────────────────┘
```

---

## IMPLEMENTATION STEPS

### PHASE 1: SETUP & VALIDATION (Week 1)

#### Step 1.1: Project Structure
```
sec_filing_parser/
├── main.py                          # Entry point
├── config.py                        # API keys, paths, constants
├── requirements.txt                 # Dependencies
├── src/
│   ├── __init__.py
│   ├── sec_client.py               # SEC Edgar API wrapper
│   ├── xbrl_parser.py              # XBRL XML parsing
│   ├── pdf_extractor.py            # PDF text extraction
│   ├── data_reconciler.py          # XBRL vs PDF reconciliation
│   ├── xml_builder.py              # Output XML generation
│   └── validator.py                # Data validation & flagging
├── data/
│   └── {TICKER}/
│       ├── raw/                    # Downloaded PDFs
│       ├── parsed/                 # Generated XMLs
│       └── logs/                   # Processing logs
└── tests/
    └── test_*.py                   # Unit tests
```

#### Step 1.2: Dependencies (Free, Open Source)
```python
# requirements.txt
requests>=2.28.0              # HTTP requests to SEC
beautifulsoup4>=4.11.0        # HTML parsing
lxml>=4.9.0                   # XML/XBRL parsing
pdfplumber>=0.7.0             # PDF text extraction
python-dateutil>=2.8.0        # Date handling
xmltodict>=0.13.0             # XML generation
structlog>=22.3.0             # Structured logging
```

#### Step 1.3: Configuration Template
```python
# config.py
import os
from pathlib import Path

# Paths
BASE_DIR = Path.home() / "sec_filing_parser"
DATA_DIR = BASE_DIR / "data"
RAW_PDF_DIR = "{ticker_dir}/raw"
PARSED_XML_DIR = "{ticker_dir}/parsed"
LOG_DIR = "{ticker_dir}/logs"

# SEC Edgar
SEC_BASE_URL = "https://www.sec.gov"
SEC_EDGAR_API = "https://data.sec.gov/api/xbrl"
SEC_SUBMISSIONS = "https://www.sec.gov/cgi-bin/browse-edgar"
USER_AGENT = "MyFirm sec_filing_parser v1.0 (contact@example.com)"

# Filings to fetch
LOOKBACK_YEARS = 3
FILING_TYPES = ["10-K", "10-Q"]  # Annual and Quarterly
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Parsing
MIN_CONFIDENCE_THRESHOLD = 0.95  # Flag items below this confidence
CACHE_AGE_DAYS = 30  # Re-fetch if local cache older than 30 days

# Free APIs (with rate limits)
IEX_CLOUD_FREE = False  # Set to True if you get free token
ALPHA_VANTAGE_FREE = False  # Set to True if you get free key
```

---

### PHASE 2: SEC DATA RETRIEVAL (Week 2)

#### Step 2.1: SEC Edgar API Client
```python
# src/sec_client.py

class SECClient:
    """
    Fetches metadata and filings from SEC Edgar.
    Handles: ticker validation, CIK lookup, filing retrieval.
    """
    
    def __init__(self):
        self.base_url = "https://data.sec.gov/submissions"
        self.headers = {"User-Agent": config.USER_AGENT}
    
    def get_cik_from_ticker(self, ticker: str) -> str:
        """
        Convert NYSE ticker to CIK (Central Index Key).
        
        Returns: CIK string (zero-padded to 10 digits)
        Raises: TickerNotFoundError if ticker invalid
        
        Source: SEC.gov ticker-to-CIK mapping
        """
        # Implementation: Query SEC Edgar search
    
    def get_filings(self, cik: str, form_types: list, years: int) -> list:
        """
        Retrieve filing metadata for past N years.
        
        Returns: List of filing dicts with:
        - accession_number (unique filing ID)
        - filing_date
        - form_type (10-K or 10-Q)
        - fiscal_period_end
        - filing_url
        
        Handles: Delayed filings (marked in metadata)
        """
        # Implementation: Query SEC submissions API
    
    def download_filing_pdf(self, accession: str, output_path: Path) -> bool:
        """
        Download PDF from SEC Edgar.
        
        Returns: True if successful, False if not found
        
        Note: Attempts main filing PDF, handles redirects
        """
        # Implementation: HTTP download with retry logic
    
    def get_xbrl_data(self, accession: str) -> dict:
        """
        Fetch XBRL-formatted financial data (if available).
        
        Returns: Parsed XBRL data or None if not available
        
        Note: Not all filers provide XBRL; fallback to PDF parsing
        """
        # Implementation: SEC XBRL API query
```

#### Step 2.2: Validation & Error Handling
```python
# Key Error Scenarios to Handle:

ERROR_CASES = {
    "TICKER_NOT_FOUND": {
        "action": "Raise TickerNotFoundError",
        "example": "INVALID → No matching NYSE ticker"
    },
    "CIK_MISMATCH": {
        "action": "Flag in log, use best guess",
        "example": "Multiple CIKs found for ticker"
    },
    "FILING_NOT_FOUND": {
        "action": "Log missing, continue with earlier filings",
        "example": "No 10-K for FY2023 (not yet filed)"
    },
    "FILING_DELAYED": {
        "action": "Flag with expected date, skip",
        "example": "10-K delayed beyond deadline"
    },
    "PDF_CORRUPT": {
        "action": "Flag, use XBRL fallback if available",
        "example": "PDF download failed or unreadable"
    },
    "XBRL_INCOMPLETE": {
        "action": "Flag items missing from XBRL, note PDF source",
        "example": "Some segments only in MD&A (non-structured)"
    }
}
```

---

### PHASE 3: DATA EXTRACTION (Week 3)

#### Step 3.1: XBRL Parser (Primary Method)
```python
# src/xbrl_parser.py

class XBRLParser:
    """
    Parse machine-readable XBRL data from SEC Edgar.
    XBRL is XML-based structured accounting data filed with 10-K/10-Q.
    
    Advantages:
    - Machine-readable, standardized
    - Direct from filer (less OCR error)
    
    Limitations:
    - Not all filers use it (check if available first)
    - Some narrative items missing
    """
    
    INCOME_STATEMENT_CONCEPTS = {
        # Revenue
        "Revenues": "us-gaap:Revenues",
        "CostOfRevenue": "us-gaap:CostOfRevenue",
        "GrossProfit": "us-gaap:GrossProfit",
        
        # Operating Expenses
        "OperatingExpenses": "us-gaap:OperatingExpenses",
        "ResearchAndDevelopment": "us-gaap:ResearchAndDevelopmentExpense",
        "SellingGeneralAdmin": "us-gaap:SellingGeneralAndAdministrativeExpense",
        
        # Operating Income
        "OperatingIncome": "us-gaap:OperatingIncomeLoss",
        
        # Non-operating Items
        "InterestExpense": "us-gaap:InterestExpense",
        "InterestIncome": "us-gaap:InterestIncome",
        "OtherIncomeExpense": "us-gaap:OtherIncomeExpenseMember",
        
        # Taxes
        "IncomeTaxExpense": "us-gaap:IncomeTaxExpenseBenefit",
        
        # Net Income
        "NetIncome": "us-gaap:NetIncomeLoss"
    }
    
    BALANCE_SHEET_CONCEPTS = {
        # Assets
        "CashAndEquivalents": "us-gaap:Cash",
        "MarketableSecurities": "us-gaap:MarketableSecurities",
        "AccountsReceivable": "us-gaap:AccountsReceivable",
        "Inventory": "us-gaap:Inventory",
        "CurrentAssets": "us-gaap:AssetsCurrent",
        "PropertyPlantEquipment": "us-gaap:PropertyPlantAndEquipmentNet",
        "Goodwill": "us-gaap:Goodwill",
        "IntangibleAssets": "us-gaap:IntangibleAssetsNetExcludingGoodwill",
        "TotalAssets": "us-gaap:Assets",
        
        # Liabilities
        "AccountsPayable": "us-gaap:AccountsPayable",
        "AccruedExpenses": "us-gaap:AccruedLiabilitiesCurrent",
        "ShortTermDebt": "us-gaap:ShortTermBorrowings",
        "CurrentLiabilities": "us-gaap:LiabilitiesCurrent",
        "LongTermDebt": "us-gaap:LongTermBorrowings",
        "TotalLiabilities": "us-gaap:Liabilities",
        
        # Equity
        "CommonStock": "us-gaap:CommonStockValue",
        "RetainedEarnings": "us-gaap:RetainedEarnings",
        "TotalStockholdersEquity": "us-gaap:StockholdersEquity"
    }
    
    CASH_FLOW_CONCEPTS = {
        "NetIncome": "us-gaap:NetIncomeLoss",
        "DepreciationAmortization": "us-gaap:DepreciationDepletionAndAmortization",
        "StockBasedCompensation": "us-gaap:StockBasedCompensation",
        "DeferredTaxes": "us-gaap:DeferredIncomeTaxExpenseBenefit",
        "OperatingCashFlow": "us-gaap:NetCashProvidedByUsedInOperatingActivities",
        "CapitalExpenditures": "us-gaap:PaymentsForCapitalExpenditures",
        "FreeCashFlow": "us-gaap:FreeCashFlow",  # May not exist; calculate
        "FinancingCashFlow": "us-gaap:NetCashProvidedByUsedInFinancingActivities"
    }
    
    def parse_filing(self, xbrl_url: str, filing_date: str) -> dict:
        """
        Parse XBRL data for a single filing.
        
        Returns: {
            "filing_date": "YYYY-MM-DD",
            "fiscal_period_end": "YYYY-MM-DD",
            "income_statement": {...},
            "balance_sheet": {...},
            "cash_flow": {...},
            "segments": {...},
            "data_quality_flags": [...]
        }
        """
        # Implementation: Fetch XBRL, parse concepts, extract values
    
    def extract_metric(self, xbrl_tree, concept: str, context: str) -> (float, str):
        """
        Extract single metric with confidence flag.
        
        Returns: (value, confidence_level)
        - confidence_level: "HIGH", "MEDIUM", "LOW"
        
        LOW confidence when:
        - Multiple contexts available (ambiguity)
        - Unit conversion required
        - Calculated field (not directly in XBRL)
        """
        # Implementation: XPath query + validation
```

#### Step 3.2: PDF Fallback Parser
```python
# src/pdf_extractor.py

class PDFExtractor:
    """
    Extract financial data from 10-K/10-Q PDF when XBRL unavailable.
    Uses pdfplumber to extract text, then regex + pattern matching.
    
    Note: This is inherently noisier than XBRL; all extracts marked
    with confidence level for manual review.
    """
    
    # Pattern examples for common financial items
    PATTERNS = {
        "REVENUE": [
            r"(?:Total\s+)?[Rr]evenue[s]?\s+[:\$]?\s*([\d,]+)",
            r"(?:Net\s+)?[Ss]ales\s+[:\$]?\s*([\d,]+)"
        ],
        "GROSS_PROFIT": [
            r"[Gg]ross\s+(?:profit|margin)\s+[:\$]?\s*([\d,]+)",
            r"[Gg]ross\s+profit\s*[:\$]?\s*([\d,]+)"
        ],
        "OPERATING_INCOME": [
            r"(?:Operating\s+)?[Ii]ncome\s+(?:from\s+)?operations\s+[:\$]?\s*([\d,]+)",
        ],
        # ... many more patterns
    }
    
    def extract_from_pdf(self, pdf_path: Path) -> dict:
        """
        Extract financial data from PDF text.
        
        Returns: {
            "income_statement": {...},
            "balance_sheet": {...},
            "confidence_flags": {...},
            "extraction_notes": "Text extraction method used"
        }
        """
        # Implementation: pdfplumber + regex extraction
    
    def locate_financial_tables(self, pdf_path: Path) -> list:
        """
        Find consolidated financial statements in 10-K.
        
        Returns: List of table locations (page #, coordinates)
        
        Logic:
        - Search for "Consolidated Statements of Operations"
        - Search for "Consolidated Balance Sheets"
        - Search for "Consolidated Statements of Cash Flows"
        """
        # Implementation: Pattern matching + table detection
```

---

### PHASE 4: DATA RECONCILIATION (Week 4)

#### Step 4.1: Reconciler & Validator
```python
# src/data_reconciler.py

class DataReconciler:
    """
    Compare XBRL vs PDF extraction.
    Flag discrepancies for manual review.
    Select best source for each metric.
    """
    
    def reconcile(self, xbrl_data: dict, pdf_data: dict, 
                  filing_date: str) -> dict:
        """
        Reconcile two data sources.
        
        Returns: {
            "reconciled_data": {...},
            "discrepancies": [
                {
                    "metric": "Revenue",
                    "xbrl_value": 130500000000,
                    "pdf_value": 130502000000,
                    "difference_pct": 0.0015,
                    "source_selected": "xbrl",
                    "reason": "Direct XBRL source preferred",
                    "flag_for_review": False
                },
                # ... more items
            ],
            "confidence_by_metric": {...}
        }
        """
        
        # Logic:
        # 1. For each metric in XBRL:
        #    - Check if PDF has corresponding value
        #    - Calculate % difference
        #    - If <5% diff: mark as reconciled (XBRL preferred)
        #    - If >5% diff: FLAG for manual review
        #    - If only in XBRL: use with HIGH confidence
        #
        # 2. For each metric only in PDF:
        #    - Mark as "PDF_ONLY" with MEDIUM/LOW confidence
        #    - Flag for manual verification
        #
        # 3. Return: Merged dataset preferring XBRL, all conflicts flagged
    
    def validate_metric(self, metric: str, value: float, 
                       filing_type: str, prior_year: float = None) -> dict:
        """
        Validate single metric for reasonableness.
        
        Returns: {
            "is_valid": bool,
            "flags": ["negative_revenue?", "100x_growth?", ...],
            "prior_year_growth": 1.5  # 150% growth
        }
        
        Checks:
        - Revenue/Profit cannot be negative (except in loss years)
        - Year-over-year growth reasonable (<1000% / >-99%)
        - Ratios within bounds (current ratio >0.5, debt ratio <10)
        """
        # Implementation: Comparative validation
```

---

### PHASE 5: XML OUTPUT GENERATION (Week 5)

#### Step 5.1: XML Schema Design
```xml
<!-- output_schema.xml -->
<!-- This is the target structure for parsed financials -->

<Filing>
  <Metadata>
    <Ticker>NVDA</Ticker>
    <CIK>1045810</CIK>
    <FilingType>10-K</FilingType>
    <FilingDate>2025-01-26</FilingDate>
    <FiscalPeriodEnd>2025-01-26</FiscalPeriodEnd>
    <FiscalYear>2025</FiscalYear>
    <CompanyName>NVIDIA Corporation</CompanyName>
    <DataExtractionDate>2025-02-23</DataExtractionDate>
    <ParsedBy>sec_filing_parser v1.0</ParsedBy>
    <SourceFiles>
      <XBRL>available</XBRL>
      <PDF>nvda-20250126.pdf</PDF>
    </SourceFiles>
  </Metadata>

  <DataQuality>
    <OverallConfidence>0.98</OverallConfidence>
    <ReconciliationStatus>PASSED</ReconciliationStatus>
    <Discrepancies>
      <Discrepancy>
        <Metric>Revenue</Metric>
        <XBRLValue>130500000000</XBRLValue>
        <PDFValue>130502000000</PDFValue>
        <DifferencePct>0.0015</DifferencePct>
        <Status>ACCEPTED (within tolerance)</Status>
        <FlagForReview>false</FlagForReview>
      </Discrepancy>
    </Discrepancies>
    <MissingItems>
      <Item metric="SegmentRevenue_Automotive">
        <Reason>Not available in this quarter</Reason>
        <FlagForReview>false</FlagForReview>
      </Item>
    </MissingItems>
  </DataQuality>

  <FinancialStatements>
    <IncomeStatement>
      <Period>
        <StartDate>2024-01-28</StartDate>
        <EndDate>2025-01-26</EndDate>
        <Duration>12 months</Duration>
      </Period>
      
      <LineItem>
        <Concept>Revenue</Concept>
        <Value>130500000000</Value>
        <Unit>USD</Unit>
        <Confidence>HIGH</Confidence>
        <Source>XBRL</Source>
        <XBRLConcept>us-gaap:Revenues</XBRLConcept>
      </LineItem>

      <LineItem>
        <Concept>CostOfRevenue</Concept>
        <Value>29050000000</Value>
        <Unit>USD</Unit>
        <Confidence>HIGH</Confidence>
        <Source>XBRL</Source>
        <XBRLConcept>us-gaap:CostOfRevenue</XBRLConcept>
      </LineItem>

      <!-- ... all income statement items -->

      <CalculatedMetrics>
        <Metric>
          <Name>GrossMargin</Name>
          <Value>0.7769</Value>
          <Percentage>77.69%</Percentage>
          <Formula>(Revenue - CostOfRevenue) / Revenue</Formula>
          <Confidence>DERIVED</Confidence>
        </Metric>
        <Metric>
          <Name>OperatingMargin</Name>
          <Value>0.6234</Value>
          <Percentage>62.34%</Percentage>
          <Formula>OperatingIncome / Revenue</Formula>
          <Confidence>DERIVED</Confidence>
        </Metric>
      </CalculatedMetrics>
    </IncomeStatement>

    <BalanceSheet>
      <AsOf>2025-01-26</AsOf>
      
      <Section name="Assets">
        <LineItem>
          <Concept>CashAndEquivalents</Concept>
          <Value>24100000000</Value>
          <Unit>USD</Unit>
          <Confidence>HIGH</Confidence>
          <Source>XBRL</Source>
        </LineItem>
        <!-- ... all asset items -->
        <LineItem>
          <Concept>TotalAssets</Concept>
          <Value>309900000000</Value>
          <Unit>USD</Unit>
          <Confidence>HIGH</Confidence>
          <Source>XBRL</Source>
        </LineItem>
      </Section>

      <Section name="Liabilities">
        <!-- ... liability items -->
        <LineItem>
          <Concept>TotalLiabilities</Concept>
          <Value>78500000000</Value>
          <Unit>USD</Unit>
          <Confidence>HIGH</Confidence>
          <Source>XBRL</Source>
        </LineItem>
      </Section>

      <Section name="Equity">
        <!-- ... equity items -->
        <LineItem>
          <Concept>TotalStockholdersEquity</Concept>
          <Value>231400000000</Value>
          <Unit>USD</Unit>
          <Confidence>HIGH</Confidence>
          <Source>XBRL</Source>
        </LineItem>
      </Section>

      <CalculatedMetrics>
        <Metric>
          <Name>CurrentRatio</Name>
          <Value>6.45</Value>
          <Formula>CurrentAssets / CurrentLiabilities</Formula>
          <HealthStatus>EXCELLENT</HealthStatus>
        </Metric>
        <Metric>
          <Name>DebtToEquity</Name>
          <Value>0.34</Value>
          <Formula>TotalDebt / TotalEquity</Formula>
          <HealthStatus>HEALTHY</HealthStatus>
        </Metric>
      </CalculatedMetrics>
    </BalanceSheet>

    <CashFlowStatement>
      <Period>
        <StartDate>2024-01-28</StartDate>
        <EndDate>2025-01-26</EndDate>
        <Duration>12 months</Duration>
      </Period>

      <OperatingActivities>
        <LineItem>
          <Concept>NetIncome</Concept>
          <Value>60922000000</Value>
          <Unit>USD</Unit>
          <Confidence>HIGH</Confidence>
        </LineItem>
        <!-- ... adjustments -->
        <LineItem>
          <Concept>NetCashFromOperations</Concept>
          <Value>73500000000</Value>
          <Unit>USD</Unit>
          <Confidence>HIGH</Confidence>
        </LineItem>
      </OperatingActivities>

      <InvestingActivities>
        <LineItem>
          <Concept>CapitalExpenditures</Concept>
          <Value>3200000000</Value>
          <Unit>USD</Unit>
          <Confidence>HIGH</Confidence>
        </LineItem>
        <!-- ... -->
        <LineItem>
          <Concept>NetCashFromInvesting</Concept>
          <Value>-2800000000</Value>
          <Unit>USD</Unit>
          <Confidence>MEDIUM</Confidence>
        </LineItem>
      </InvestingActivities>

      <FinancingActivities>
        <!-- ... -->
      </FinancingActivities>

      <CalculatedMetrics>
        <Metric>
          <Name>FreeCashFlow</Name>
          <Value>70300000000</Value>
          <Formula>OperatingCashFlow - CapitalExpenditures</Formula>
          <Confidence>DERIVED</Confidence>
        </Metric>
        <Metric>
          <Name>FCFMargin</Name>
          <Value>0.5392</Value>
          <Percentage>53.92%</Percentage>
          <Formula>FreeCashFlow / Revenue</Formula>
          <HealthStatus>EXCELLENT</HealthStatus>
        </Metric>
      </CalculatedMetrics>
    </CashFlowStatement>
  </FinancialStatements>

  <SegmentData>
    <Segment>
      <Name>Data Center</Name>
      <Revenue>119616000000</Revenue>
      <Revenue_YoY_Growth>1.28</Revenue_YoY_Growth>
      <RevenuePercentageOfTotal>0.9175</RevenuePercentageOfTotal>
      <OperatingMargin>0.6500</OperatingMargin>
      <CustomerConcentration>
        <TopCustomer>
          <Description>Customer A</Description>
          <Revenue>17500000000</Revenue>
          <PercentageOfSegment>0.1462</PercentageOfSegment>
          <PercentageOfTotal>0.1342</PercentageOfTotal>
          <FlagForReview>false</FlagForReview>
        </TopCustomer>
        <TopCustomer>
          <Description>Customer B</Description>
          <Revenue>10500000000</Revenue>
          <PercentageOfSegment>0.0877</PercentageOfSegment>
          <PercentageOfTotal>0.0805</PercentageOfTotal>
          <FlagForReview>false</FlagForReview>
        </TopCustomer>
      </CustomerConcentration>
    </Segment>
    <Segment>
      <Name>Gaming</Name>
      <Revenue>5100000000</Revenue>
      <Revenue_YoY_Growth>0.88</Revenue_YoY_Growth>
      <RevenuePercentageOfTotal>0.0391</RevenuePercentageOfTotal>
    </Segment>
    <!-- ... more segments -->
  </SegmentData>

  <DebtAndEquity>
    <Debt>
      <ShortTermBorrowings>0</ShortTermBorrowings>
      <LongTermBorrowings>10500000000</LongTermBorrowings>
      <TotalDebt>10500000000</TotalDebt>
      <DebtToEquityRatio>0.0454</DebtToEquityRatio>
      <DebtToAssetsRatio>0.0339</DebtToAssetsRatio>
      <InterestCoverage>
        <OperatingIncome>81250000000</OperatingIncome>
        <InterestExpense>350000000</InterestExpense>
        <Ratio>232.14</Ratio>
        <HealthStatus>EXCELLENT</HealthStatus>
      </InterestCoverage>
    </Debt>
    <Equity>
      <CommonStock>24400000000</CommonStock>
      <RetainedEarnings>207000000000</RetainedEarnings>
      <TotalEquity>231400000000</TotalEquity>
      <ReturnOnEquity>0.2632</ReturnOnEquity>
      <ReturnOnAssets>0.1967</ReturnOnAssets>
    </Equity>
  </DebtAndEquity>

  <RiskFactors>
    <RiskFactor>
      <Category>Customer Concentration</Category>
      <Description>Data Center revenue concentrated among few cloud providers</Description>
      <MaterialityLevel>HIGH</MaterialityLevel>
      <Source>10-K Item 1A</Source>
      <FlagForManualReview>true</FlagForManualReview>
    </RiskFactor>
    <RiskFactor>
      <Category>Manufacturing Concentration</Category>
      <Description>GPUs manufactured by TSMC in Taiwan; geopolitical risk</Description>
      <MaterialityLevel>HIGH</MaterialityLevel>
      <Source>10-K Item 1A</Source>
      <FlagForManualReview>true</FlagForManualReview>
    </RiskFactor>
    <!-- ... extracted from risk factors section -->
  </RiskFactors>

  <ManagementDiscussionAndAnalysis>
    <Summary>
      Extracted from MD&A in 10-K; narrative about business performance,
      strategy, and outlook. Key forward-looking statements flagged.
    </Summary>
    <KeyPoints>
      <Point>
        <Topic>Demand Outlook</Topic>
        <Quote>"Demand for Blackwell is amazing..."</Quote>
        <ImpliedGrowthRate>HIGH</ImpliedGrowthRate>
        <FlagForReview>false</FlagForReview>
      </Point>
    </KeyPoints>
  </ManagementDiscussionAndAnalysis>

  <AuditTrail>
    <ExtractionProcess>
      <Step sequence="1">
        <Action>Fetched XBRL from SEC Edgar</Action>
        <Timestamp>2025-02-23T10:23:45Z</Timestamp>
        <Status>SUCCESS</Status>
      </Step>
      <Step sequence="2">
        <Action>Downloaded PDF backup</Action>
        <Timestamp>2025-02-23T10:24:10Z</Timestamp>
        <Status>SUCCESS</Status>
        <FileHash>sha256:abc123...</FileHash>
      </Step>
      <Step sequence="3">
        <Action>Reconciled XBRL vs PDF extraction</Action>
        <Timestamp>2025-02-23T10:25:30Z</Timestamp>
        <Status>PASSED with 1 discrepancy flagged</Status>
        <DiscrepancyCount>1</DiscrepancyCount>
      </Step>
    </ExtractionProcess>
    <DataSources>
      <Source type="XBRL">
        <URL>https://www.sec.gov/cgi-bin/viewer?action=view&cik=1045810&accession_number=0001045810-25-000023&xbrl_type=v</URL>
        <RetrievedAt>2025-02-23T10:23:45Z</RetrievedAt>
        <Status>COMPLETE</Status>
      </Source>
      <Source type="PDF">
        <Filename>nvda-20250126.pdf</Filename>
        <FileSize>48800000</FileSize>
        <FileHash>sha256:def456...</FileHash>
        <StoredAt>~/sec_filing_parser/data/NVDA/raw/</StoredAt>
      </Source>
    </DataSources>
    <ReviewNotes>
      <Note priority="HIGH">
        <Metric>Revenue</Metric>
        <Issue>PDF shows 130.502B, XBRL shows 130.500B</Issue>
        <Resolution>Difference <0.01%; accepted XBRL</Resolution>
        <ReviewedBy>manual</ReviewedBy>
        <ReviewDate>TBD</ReviewDate>
      </Note>
    </ReviewNotes>
  </AuditTrail>

</Filing>
```

#### Step 5.2: XML Builder Implementation
```python
# src/xml_builder.py

class XMLBuilder:
    """
    Construct final output XML from reconciled data.
    """
    
    def build(self, reconciled_data: dict, metadata: dict, 
              audit_trail: dict) -> ET.Element:
        """
        Build complete XML tree.
        
        Returns: ElementTree ready for pretty-print and save
        """
        root = ET.Element("Filing")
        
        # Add metadata
        self._add_metadata(root, metadata)
        
        # Add data quality section
        self._add_data_quality(root, reconciled_data.get("flags", []))
        
        # Add financial statements
        self._add_financial_statements(root, reconciled_data)
        
        # Add segment data
        self._add_segments(root, reconciled_data)
        
        # Add risk factors
        self._add_risk_factors(root, reconciled_data)
        
        # Add audit trail
        self._add_audit_trail(root, audit_trail)
        
        return root
    
    def save(self, tree: ET.Element, output_path: Path) -> bool:
        """
        Save XML with pretty formatting.
        
        Returns: True if successful
        """
        # Implementation: Use xml.dom.minidom for formatting
```

---

### PHASE 6: MAIN ORCHESTRATION (Week 6)

#### Step 6.1: Main Script
```python
# main.py

import sys
import logging
from pathlib import Path
from src.sec_client import SECClient
from src.xbrl_parser import XBRLParser
from src.pdf_extractor import PDFExtractor
from src.data_reconciler import DataReconciler
from src.xml_builder import XMLBuilder
import config

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"sec_parser_{Path.home().name}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def process_ticker(ticker: str) -> dict:
    """
    Main processing pipeline for a single ticker.
    
    Returns: {
        "success": bool,
        "ticker": str,
        "files_saved": list,
        "xmls_generated": list,
        "flags_for_review": list,
        "errors": list
    }
    """
    
    result = {
        "success": False,
        "ticker": ticker.upper(),
        "files_saved": [],
        "xmls_generated": [],
        "flags_for_review": [],
        "errors": []
    }
    
    try:
        # 1. Validate ticker and get CIK
        logger.info(f"Processing ticker: {ticker}")
        sec_client = SECClient()
        cik = sec_client.get_cik_from_ticker(ticker)
        logger.info(f"Ticker {ticker} → CIK {cik}")
        
        # 2. Create data directories
        data_dir = config.DATA_DIR / ticker.upper()
        raw_dir = data_dir / "raw"
        parsed_dir = data_dir / "parsed"
        log_dir = data_dir / "logs"
        
        for d in [raw_dir, parsed_dir, log_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        # 3. Get filings metadata
        filings = sec_client.get_filings(
            cik=cik,
            form_types=config.FILING_TYPES,
            years=config.LOOKBACK_YEARS
        )
        
        if not filings:
            result["errors"].append("No filings found for ticker")
            logger.error(f"No filings found for {ticker}")
            return result
        
        logger.info(f"Found {len(filings)} filings for {ticker}")
        
        # 4. Download PDFs
        for filing in filings:
            accession = filing["accession_number"]
            form_type = filing["form_type"]
            filing_date = filing["filing_date"]
            
            logger.info(f"Downloading {form_type} ({filing_date})")
            
            pdf_path = raw_dir / f"{ticker}_{form_type}_{filing_date}.pdf"
            
            if sec_client.download_filing_pdf(accession, pdf_path):
                result["files_saved"].append(str(pdf_path))
                filing["pdf_path"] = pdf_path
                logger.info(f"Saved PDF: {pdf_path}")
            else:
                result["errors"].append(f"Failed to download {form_type} {filing_date}")
                logger.warning(f"Could not download {form_type} {filing_date}")
        
        # 5. Parse and reconcile each filing
        for filing in filings:
            if "pdf_path" not in filing:
                logger.warning(f"Skipping {filing['form_type']} (no PDF)")
                continue
            
            logger.info(f"Parsing {filing['form_type']} ({filing['filing_date']})")
            
            # Try XBRL parsing
            xbrl_data = None
            try:
                xbrl_parser = XBRLParser()
                xbrl_url = sec_client.get_xbrl_url(filing["accession_number"])
                if xbrl_url:
                    xbrl_data = xbrl_parser.parse_filing(xbrl_url, filing["filing_date"])
                    logger.info("XBRL data extracted")
            except Exception as e:
                logger.warning(f"XBRL parsing failed: {e}")
            
            # PDF extraction as fallback
            pdf_data = None
            try:
                pdf_extractor = PDFExtractor()
                pdf_data = pdf_extractor.extract_from_pdf(filing["pdf_path"])
                logger.info("PDF data extracted")
            except Exception as e:
                logger.warning(f"PDF extraction failed: {e}")
                result["flags_for_review"].append({
                    "filing": filing['form_type'],
                    "issue": f"PDF extraction failed: {e}",
                    "severity": "HIGH"
                })
            
            # Reconcile sources
            if xbrl_data and pdf_data:
                reconciler = DataReconciler()
                reconciled = reconciler.reconcile(xbrl_data, pdf_data, filing["filing_date"])
                
                if reconciled["discrepancies"]:
                    for disc in reconciled["discrepancies"]:
                        if disc["flag_for_review"]:
                            result["flags_for_review"].append(disc)
                            logger.warning(f"Discrepancy flagged: {disc}")
            else:
                reconciled = xbrl_data or pdf_data
                if reconciled:
                    logger.warning(f"Only one source available for {filing['form_type']}")
            
            # Generate XML
            if reconciled:
                xml_builder = XMLBuilder()
                metadata = {
                    "ticker": ticker.upper(),
                    "cik": cik,
                    "filing_type": filing["form_type"],
                    "filing_date": filing["filing_date"],
                    "fiscal_period_end": filing.get("fiscal_period_end"),
                    "sources": {"xbrl": xbrl_data is not None, "pdf": pdf_data is not None}
                }
                
                xml_tree = xml_builder.build(
                    reconciled_data=reconciled,
                    metadata=metadata,
                    audit_trail={"sources": [xbrl_data is not None, pdf_data is not None]}
                )
                
                xml_filename = f"{ticker}_{filing['form_type']}_{filing['filing_date']}.xml"
                xml_path = parsed_dir / xml_filename
                
                xml_builder.save(xml_tree, xml_path)
                result["xmls_generated"].append(str(xml_path))
                logger.info(f"Saved XML: {xml_path}")
        
        result["success"] = True
        logger.info(f"Completed processing {ticker}")
        
    except Exception as e:
        logger.error(f"Fatal error processing {ticker}: {e}", exc_info=True)
        result["errors"].append(str(e))
    
    return result


def main():
    """
    CLI entry point.
    """
    if len(sys.argv) < 2:
        print("Usage: python main.py <NYSE_TICKER>")
        print("Example: python main.py NVDA")
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    
    print(f"\n{'='*60}")
    print(f"SEC FILING PARSER")
    print(f"Processing: {ticker}")
    print(f"{'='*60}\n")
    
    result = process_ticker(ticker)
    
    # Print results
    print(f"\n{'='*60}")
    print("RESULTS")
    print(f"{'='*60}")
    print(f"Success: {result['success']}")
    print(f"Files saved: {len(result['files_saved'])}")
    print(f"XMLs generated: {len(result['xmls_generated'])}")
    print(f"Flags for review: {len(result['flags_for_review'])}")
    print(f"Errors: {len(result['errors'])}")
    
    if result["flags_for_review"]:
        print(f"\n⚠️  MANUAL REVIEW REQUIRED:")
        for flag in result["flags_for_review"]:
            print(f"  - {flag}")
    
    if result["errors"]:
        print(f"\n❌ ERRORS:")
        for error in result["errors"]:
            print(f"  - {error}")
    
    print(f"\n📂 Data saved to: {config.DATA_DIR}/{ticker}/")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
```

---

## USAGE EXAMPLES

### Single Ticker
```bash
python main.py NVDA
# Output:
# ============================================================
# SEC FILING PARSER
# Processing: NVDA
# ============================================================
#
# Success: True
# Files saved: 12
# XMLs generated: 12
# Flags for review: 2
# Errors: 0
#
# ⚠️  MANUAL REVIEW REQUIRED:
#   - Revenue (XBRL vs PDF difference: 0.15%)
#   - CapitalExpenditures (PDF only, confidence MEDIUM)
#
# 📂 Data saved to: ~/sec_filing_parser/data/NVDA/
# ============================================================
```

### Output Directory Structure
```
~/sec_filing_parser/data/NVDA/
├── raw/
│   ├── NVDA_10-K_2025-01-26.pdf
│   ├── NVDA_10-Q_2024-10-27.pdf
│   ├── NVDA_10-Q_2024-07-28.pdf
│   ├── NVDA_10-Q_2024-04-28.pdf
│   ├── NVDA_10-K_2024-01-28.pdf
│   ├── NVDA_10-Q_2023-10-29.pdf
│   ├── NVDA_10-Q_2023-07-30.pdf
│   ├── NVDA_10-Q_2023-04-30.pdf
│   └── NVDA_10-K_2023-01-29.pdf
├── parsed/
│   ├── NVDA_10-K_2025-01-26.xml
│   ├── NVDA_10-Q_2024-10-27.xml
│   ├── NVDA_10-Q_2024-07-28.xml
│   ├── NVDA_10-Q_2024-04-28.xml
│   ├── NVDA_10-K_2024-01-28.xml
│   ├── NVDA_10-Q_2023-10-29.xml
│   ├── NVDA_10-Q_2023-07-30.xml
│   ├── NVDA_10-Q_2023-04-30.xml
│   └── NVDA_10-K_2023-01-29.xml
└── logs/
    └── NVDA_processing_2025-02-23.log
```

---

## TRADER PERSPECTIVE: WHY THIS MATTERS

### As an Algorithmic Trader:
1. **Data Integrity** — A single wrong data point breaks your models. By reconciling sources and flagging discrepancies, you avoid garbage-in-garbage-out.

2. **Competitive Edge** — Most traders rely on aggregators (Yahoo, Bloomberg, etc.). By parsing official SEC filings directly, you see data 24-48 hours before market consensus.

3. **Auditability** — In case your algorithm makes a bad trade, you can trace exactly which data point was wrong and which source it came from.

4. **Full Coverage** — Segment data, customer concentration, debt covenants — all available in 10-Qs before Wall Street research catches up.

### As an MBA:
1. **Fundamental Analysis Framework** — This pipeline implements proper financial statement analysis (not just ratios from Yahoo).

2. **Risk Management** — Flagging customer concentration, manufacturing risks, etc. is how you avoid blowups.

3. **Valuation Inputs** — Once you have clean data, you can build DCF, EV/EBITDA, or other models without worrying about data quality.

---

## NEXT PHASES (Post v1.0)

Once Phase 6 is complete and working reliably:

**Phase 7: Trend Analysis**
- Compare 3 years of metrics side-by-side
- Calculate growth rates, margin trends
- Identify inflection points

**Phase 8: Fundamental Scoring**
- Weight metrics (growth 30%, profitability 30%, health 40%)
- Generate "fundamental score" (0-100)
- Flag cheap vs expensive valuations

**Phase 9: Dashboard & Alerts**
- Web UI to view parsed data
- Alert on metric changes >10% YoY
- Integration with trading system

---

## SUMMARY CHECKLIST

- [ ] **Phase 1:** Project structure, dependencies, config
- [ ] **Phase 2:** SEC client, ticker validation, PDF download
- [ ] **Phase 3:** XBRL parser, PDF extractor
- [ ] **Phase 4:** Reconciler, validator, flagging logic
- [ ] **Phase 5:** XML schema, XML builder
- [ ] **Phase 6:** Main orchestration, CLI

**Total Estimated Time:** 6-8 weeks solo development

**Quality Bar:** 98%+ accuracy on major line items, all discrepancies flagged

Good luck! 🚀
