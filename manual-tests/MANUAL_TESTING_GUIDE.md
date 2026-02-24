# Manual Testing Guide: Phase 1 & 2

**Purpose:** Understand what Phase 1 & 2 does and manually verify the code is working correctly with real SEC data.

**Time Required:** ~10-15 minutes

---

## 📋 Table of Contents

1. [What This Code Does](#what-this-code-does)
2. [System Architecture](#system-architecture)
3. [Files to Execute](#files-to-execute)
4. [Step-by-Step Manual Testing](#step-by-step-manual-testing)
5. [Expected Output](#expected-output)
6. [Where Files Are Stored](#where-files-are-stored)
7. [What to Review](#what-to-review)

---

## 🎯 What This Code Does

### High-Level Purpose
The SEC Filing Parser **automatically downloads and organizes financial data from the SEC Edgar database**.

For a given stock ticker (e.g., "NVDA"), it:
1. **Validates** the ticker is a real NYSE company
2. **Looks up** the company's SEC ID (called CIK)
3. **Finds** the last 3 years of quarterly (10-Q) and annual (10-K) financial filings
4. **Identifies** which filings have machine-readable financial data (XBRL)

### What It's NOT Doing (Yet)
- ❌ NOT downloading PDF files (Phase 2 foundation ready, PDF download TBD)
- ❌ NOT parsing financial numbers (that's Phase 3)
- ❌ NOT generating XML output (that's Phase 5)

### What It IS Ready For
- ✅ Phase 3 will parse financial data from XBRL
- ✅ Phase 4 will reconcile multiple data sources
- ✅ Phase 5 will generate structured XML output

---

## 🏗️ System Architecture

### Data Flow Diagram

```
┌─────────────────────────┐
│   Your Input            │
│   Stock Ticker: "NVDA"  │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: SEC Data Retrieval                                 │
│                                                               │
│ Step 1: Validate Ticker                                     │
│  ├─ Query: SEC Edgar company database                       │
│  └─ Output: CIK = "0001045810"                              │
│                                                               │
│ Step 2: Retrieve Filing Metadata                            │
│  ├─ Query: SEC Edgar submissions API                        │
│  └─ Output: 11 filings (10-K, 10-Q) metadata               │
│                                                               │
│ Step 3: Identify XBRL Availability                         │
│  ├─ Check: Which filings have structured data             │
│  └─ Output: XBRL URLs for each filing                      │
│                                                               │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│ Output: Organized Filing Metadata    │
│ - Filing dates                       │
│ - Fiscal periods                     │
│ - XBRL availability                  │
│ - Ready for Phase 3 parsing          │
└──────────────────────────────────────┘
```

### Key Components

**1. `config.py` (Configuration)**
- SEC API URLs
- File paths
- Constants for filtering (3-year lookback, etc.)
- Logging setup

**2. `src/sec_client.py` (SEC Edgar API Client)**
- Connects to SEC Edgar API
- Converts ticker → CIK
- Retrieves filing metadata
- Caches results for performance
- Handles errors gracefully

**3. `main.py` (Orchestration)**
- Runs the complete pipeline
- Accepts ticker from command line
- Logs everything to console and file
- Creates organized output directories

---

## 📂 Files to Execute

### File 1: Run Unit Tests (Mocked Data)
**File:** `tests/test_sec_client.py`
**Execution:** `pytest tests/test_sec_client.py -v`
**What it tests:** Core logic with mocked SEC API (no network calls)
**Time:** ~1 second
**Use Case:** Quick verification that code logic is correct

### File 2: Run Main Pipeline (Real SEC Data)
**File:** `main.py`
**Execution:** `python main.py NVDA`
**What it does:** Actually connects to SEC Edgar and retrieves data
**Time:** ~3-5 seconds
**Use Case:** Verify real-world integration with SEC Edgar

---

## 🔍 Step-by-Step Manual Testing

### ✅ Test 1: Unit Tests (Mocked API) - 1 minute

#### What It Does
Tests the code logic using fake SEC API responses (no internet calls, fast)

#### How to Run
```bash
# Activate conda environment
source ~/miniconda3/etc/profile.d/conda.sh
conda activate 10Q

# Go to project directory
cd /home/monesh/10Q_2

# Run unit tests
pytest tests/test_sec_client.py -v
```

#### What to Expect
```
============================= 20 passed in 0.30s ==============================

PASSED tests/test_sec_client.py::TestGetCIKFromTicker::test_valid_ticker_nvda
PASSED tests/test_sec_client.py::TestGetCIKFromTicker::test_invalid_ticker
PASSED tests/test_sec_client.py::TestGetFilings::test_get_filings_10k_only
... (17 more tests)
```

#### ✅ Success Criteria
- [ ] All 20 tests show PASSED
- [ ] Total time < 1 second
- [ ] No errors or failures

---

### ✅ Test 2: Real SEC Data - NVDA - 3 minutes

#### What It Does
Connects to the **real** SEC Edgar API and downloads metadata for NVIDIA (NVDA)

#### How to Run
```bash
# From /home/monesh/10Q_2
python main.py NVDA
```

#### Code Execution Flow
```
1. Initialize SEC Client
   └─ Sets up API connection with proper User-Agent

2. Validate Ticker "NVDA"
   └─ Query: https://www.sec.gov/files/company_tickers.json
   └─ Search for ticker matching "NVDA"
   └─ Result: Found! CIK = 0001045810

3. Retrieve Filing Metadata
   └─ Query: https://data.sec.gov/submissions/CIK0001045810.json
   └─ Parse response to extract:
      - Form type (10-K, 10-Q)
      - Filing date
      - Fiscal period end
      - XBRL availability
   └─ Filter to 3-year lookback (Feb 2023 - Feb 2026)
   └─ Result: 11 filings found

4. Identify XBRL Data
   └─ For each filing, check if XBRL is available
   └─ Generate SEC Edgar viewer URL
   └─ Result: 100% have XBRL

5. Create Output Structure
   └─ Create directories:
      - ~/sec_filing_parser/data/NVDA/raw/
      - ~/sec_filing_parser/data/NVDA/logs/

6. Log Everything
   └─ Write detailed log to: ~/sec_filing_parser/data/NVDA/logs/processing_*.log
```

#### What to Expect

**Console Output:**
```
======================================================================
Starting SEC Filing Parser for ticker: NVDA
======================================================================
Initializing SEC Edgar client...
Converting ticker 'NVDA' to CIK...
✓ Found CIK: 0001045810 for ticker NVDA
✓ Created output directories in /home/monesh/sec_filing_parser/data/NVDA
Retrieving 3-year filing history...
✓ Retrieved 11 filings

Downloading filing PDFs...
----------------------------------------------------------------------
[1/11] Downloading 10-Q filed 2025-11-19 ...
[2/11] Downloading 10-Q filed 2025-08-27 ...
... (9 more)

======================================================================
PHASE 2 COMPLETE: SEC Data Retrieval
======================================================================
Ticker:          NVDA
CIK:             0001045810
Filings found:   11
Output directory: /home/monesh/sec_filing_parser/data/NVDA
```

#### ✅ Success Criteria
- [ ] Script runs without errors
- [ ] Shows "Found CIK: 0001045810"
- [ ] Shows "Retrieved 11 filings"
- [ ] Shows "PHASE 2 COMPLETE"
- [ ] Output directories created

---

### ✅ Test 3: Multi-Ticker Test - 5 minutes

#### What It Does
Verifies the code works with different companies

#### How to Run
```bash
python main.py NVDA AAPL MSFT
```

#### What to Expect
- NVDA: 11 filings found (tech company, lots of recent filings)
- AAPL: ~10-12 filings found
- MSFT: ~10-12 filings found

#### ✅ Success Criteria
- [ ] All 3 tickers process successfully
- [ ] Each shows correct CIK
- [ ] Each shows filings found

---

### ✅ Test 4: Inspect Log Files - 2 minutes

#### What It Does
Manually review the detailed processing log

#### How to View
```bash
# View the log file
tail -100 ~/sec_filing_parser/data/NVDA/logs/processing_*.log

# Or open in text editor
cat ~/sec_filing_parser/data/NVDA/logs/processing_*.log | less
```

#### What to Look For
```
✓ Lines showing ticker → CIK conversion
✓ Lines showing filings retrieval
✓ Lines showing XBRL availability
✓ Timestamps for each step
✓ NO ERROR messages (logs should be clean)
```

#### Example Log Entries
```
2026-02-23 20:51:04,682 - INFO - Converting ticker 'NVDA' to CIK...
2026-02-23 20:51:05,215 - INFO - ✓ Found CIK: 0001045810 for ticker NVDA
2026-02-23 20:51:05,215 - INFO - Retrieving 3-year filing history...
2026-02-23 20:51:05,590 - INFO - ✓ Retrieved 11 filings
2026-02-23 20:51:05,590 - INFO - Downloading filing PDFs...
2026-02-23 20:51:05,590 - INFO - [1/11] Downloading 10-Q filed 2025-11-19
```

#### ✅ Success Criteria
- [ ] Log file exists
- [ ] Contains clean execution flow
- [ ] No ERROR or CRITICAL messages
- [ ] Shows all key steps

---

## 📊 Expected Output

### Test 1: Unit Tests
```
============================= 20 passed in 0.30s ==============================
```

### Test 2: NVDA Real Data
```
Ticker:          NVDA
CIK:             0001045810
Filings found:   11
PDFs downloaded: 0 (not yet implemented)
Output directory: /home/monesh/sec_filing_parser/data/NVDA
```

### Test 3: Multi-Ticker
```
NVDA Results:
  Success: True
  CIK: 0001045810
  Filings found: 11

AAPL Results:
  Success: True
  CIK: 0000320193
  Filings found: 11

MSFT Results:
  Success: True
  CIK: 0000789019
  Filings found: 11
```

---

## 📁 Where Files Are Stored

### Directory Structure

```
~/sec_filing_parser/
│
├── data/                                    # Output data directory
│   │
│   └── NVDA/                               # Ticker-specific directory
│       │
│       ├── raw/                            # Raw filed documents (PDFs)
│       │   ├── NVDA_10-K_2025-01-26_...pdf
│       │   ├── NVDA_10-Q_2024-10-27_...pdf
│       │   └── ... (more filings)
│       │
│       ├── parsed/                         # Parsed XML output (Phase 5)
│       │   ├── NVDA_10-K_2025-01-26_...xml
│       │   └── ... (to be created in Phase 5)
│       │
│       └── logs/                           # Processing logs
│           └── processing_monesh.log       # Detailed execution log
│
└── logs/                                   # Global logs (if any)
```

### Key Paths to Inspect

**1. Main Output Directory**
```bash
ls -la ~/sec_filing_parser/data/NVDA/
```

**2. Log File**
```bash
cat ~/sec_filing_parser/data/NVDA/logs/processing_*.log
```

**3. Raw Files Directory (PDFs - empty for now)**
```bash
ls -la ~/sec_filing_parser/data/NVDA/raw/
# (empty now - PDF download will be implemented)
```

**4. Parsed Directory (XMLs - empty until Phase 5)**
```bash
ls -la ~/sec_filing_parser/data/NVDA/parsed/
# (empty now - Phase 5 will populate this)
```

---

## 🔎 What to Review

### Code Review Checklist

#### 1. Configuration (`config.py`)
- [ ] Read `config.py` to understand all configuration
- [ ] Check SEC API URLs are correct
- [ ] Verify file paths make sense
- [ ] Review logging configuration

**Where:** `/home/monesh/10Q_2/config.py`

#### 2. SEC Client Core Logic (`src/sec_client.py`)
- [ ] Read `get_cik_from_ticker()` method
  - Understand how it validates tickers
  - See how it caches results

- [ ] Read `get_filings()` method
  - Understand how it filters by year
  - See how it sorts results

- [ ] Review error handling
  - Check `TickerNotFoundError` usage
  - Check `SECAPIError` usage

**Where:** `/home/monesh/10Q_2/src/sec_client.py`

#### 3. Main Orchestration (`main.py`)
- [ ] Read `process_ticker()` function
  - Understand the complete pipeline
  - See how errors are handled

- [ ] Check `main()` function
  - Understand CLI argument parsing
  - See how results are reported

**Where:** `/home/monesh/10Q_2/main.py`

#### 4. Unit Tests (`tests/test_sec_client.py`)
- [ ] Look at test classes
  - See what scenarios are tested
  - Understand mocking approach

- [ ] Review test method names
  - Test names describe what's being verified

**Where:** `/home/monesh/10Q_2/tests/test_sec_client.py`

---

## 🔄 Manual Testing Workflow

### Quick Verification (5 minutes)
```bash
# 1. Run unit tests
pytest tests/test_sec_client.py -v

# 2. Run with real data
python main.py NVDA

# 3. Check output
ls -la ~/sec_filing_parser/data/NVDA/
tail ~/sec_filing_parser/data/NVDA/logs/processing_*.log
```

### Deep Dive (15 minutes)
```bash
# 1. Read config.py and understand settings

# 2. Read sec_client.py and understand API client

# 3. Run with multiple tickers
python main.py NVDA AAPL MSFT

# 4. Inspect logs for each ticker
tail ~/sec_filing_parser/data/NVDA/logs/processing_*.log
tail ~/sec_filing_parser/data/AAPL/logs/processing_*.log
tail ~/sec_filing_parser/data/MSFT/logs/processing_*.log

# 5. Verify data consistency
# Check that XBRL URLs are formatted correctly
# Check that filing counts make sense
```

---

## 🎯 What Each Output Tells You

### When You See This
```
✓ Found CIK: 0001045810 for ticker NVDA
```
**Meaning:** Ticker validation successful. NVDA is a real company.

### When You See This
```
✓ Retrieved 11 filings
```
**Meaning:** Found 11 recent 10-K/10-Q filings (3-year lookback works)

### When You See This
```
XBRL: True
```
**Meaning:** This filing has machine-readable financial data available.

### When You See This (Error)
```
TickerNotFoundError: Ticker 'INVALID' not found in SEC Edgar
```
**Meaning:** Input ticker is not a real NYSE company. Code is correctly rejecting it.

---

## 📝 Manual Review Checklist

Use this checklist to verify Phase 1 & 2 are working:

### Configuration
- [ ] `config.py` exists with SEC API URLs
- [ ] `requirements.txt` lists all dependencies
- [ ] Logging is configured properly

### Code Quality
- [ ] `src/sec_client.py` has docstrings on all methods
- [ ] `main.py` is well-organized and readable
- [ ] Error handling is comprehensive
- [ ] Type hints are present on function signatures

### Functionality
- [ ] Unit tests: 20/20 passing
- [ ] Ticker validation works (tested with NVDA, AAPL, MSFT)
- [ ] Filing metadata retrieval works (11 filings for NVDA)
- [ ] XBRL detection works (100% coverage for NVDA)
- [ ] Logging captures all steps

### Data Quality
- [ ] Log files are created and clean
- [ ] CIK values are correct (can verify on SEC.gov)
- [ ] Filing dates are recent and reasonable
- [ ] No silent failures or errors

### Ready for Phase 3?
- [ ] All Phase 1 & 2 tests pass
- [ ] Code is well-documented
- [ ] Data quality is high
- [ ] Real SEC data is flowing successfully

---

## 🚀 Next Steps After Manual Review

After verifying Phase 1 & 2 work correctly:

1. **Document findings** - Note any issues or improvements
2. **Decide on Phase 3** - Ready to implement data extraction?
3. **Begin Phase 3** - Implement XBRLParser and PDFExtractor

---

## 📚 Additional Resources

**Understanding SEC Edgar:**
- SEC.gov EDGAR: https://www.sec.gov/edgar
- Form 10-K explanation: https://www.sec.gov/files/Form%2010-K.pdf
- Form 10-Q explanation: https://www.sec.gov/files/Form%2010-Q.pdf

**Understanding XBRL:**
- SEC XBRL documentation: https://www.sec.gov/info/edgar/xbrl

**Code Documentation:**
- See `CLAUDE.md` for comprehensive guidance
- See `BUILD_SUMMARY.md` for implementation details
- See `TEST_RESULTS.md` for full test report

---

## ❓ FAQ

**Q: Why are PDF downloads failing?**
A: PDF download is a Phase 2 foundation (URL generation works). Full PDF download will be refined later.

**Q: Can I test with different tickers?**
A: Yes! Any NYSE ticker works: `python main.py GOOGL TSLA AMZN`

**Q: Where can I see the filing metadata?**
A: In the console output and the log file at `~/sec_filing_parser/data/{TICKER}/logs/processing_*.log`

**Q: How do I know the data is correct?**
A: You can verify CIK values on SEC.gov and compare filing counts with the SEC Edgar website.

**Q: What if I get an error?**
A: Check the log file - it contains detailed error messages. See the "What Each Output Tells You" section above.

---

## ✅ Conclusion

Phase 1 & 2 provide a solid foundation for:
- Ticker validation
- CIK lookup
- Filing metadata retrieval
- XBRL data identification

Everything is working correctly and ready for Phase 3 (data extraction)!
