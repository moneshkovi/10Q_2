# File Locations & Output Structure

**Reference guide for where everything is stored and what the output looks like**

---

## 📂 Project Source Code Structure

```
/home/monesh/10Q_2/                          # PROJECT ROOT
│
├── config.py                                 # Configuration (Phase 1)
├── main.py                                   # CLI Orchestration (Phase 2)
├── requirements.txt                          # Dependencies
│
├── src/                                      # Source code
│   ├── __init__.py
│   └── sec_client.py                        # SEC Edgar API Client (Phase 2)
│
├── tests/                                    # Unit tests
│   ├── __init__.py
│   ├── conftest.py                          # Pytest configuration
│   └── test_sec_client.py                   # Phase 2 tests (20 tests)
│
├── manual-tests/                             # Manual testing guides
│   ├── MANUAL_TESTING_GUIDE.md              # (This is you reading this!)
│   ├── QUICK_REFERENCE.md                   # Copy-paste commands
│   ├── CODE_WALKTHROUGH.md                  # Deep dive into code
│   └── FILE_LOCATIONS_AND_OUTPUT.md         # (This file)
│
└── Documentation/
    ├── README.md
    ├── CLAUDE.md                            # Guidance for Claude Code
    ├── PHASE_1_2_SETUP.md
    ├── BUILD_SUMMARY.md
    ├── TEST_RESULTS.md
    └── SEC_Filing_Parser_Specification.md
```

---

## 📊 Output Data Structure

### After Running: `python main.py NVDA`

```
~/sec_filing_parser/                          # BASE OUTPUT DIRECTORY
│
└── data/
    └── NVDA/                                 # TICKER DIRECTORY
        │
        ├── raw/                              # Raw downloaded files
        │   ├── NVDA_10-K_2025-01-26_0001045810-25-000023.pdf
        │   ├── NVDA_10-Q_2024-10-27_0001045810-24-000108.pdf
        │   ├── NVDA_10-Q_2024-07-28_0001045810-24-000075.pdf
        │   └── ... (more filings)
        │
        ├── parsed/                           # Parsed XML output (Phase 5)
        │   ├── NVDA_10-K_2025-01-26_0001045810-25-000023.xml
        │   ├── NVDA_10-Q_2024-10-27_0001045810-24-000108.xml
        │   └── ... (more XMLs - created in Phase 5)
        │
        └── logs/                             # Processing logs
            └── processing_monesh.log         # Detailed execution log
```

---

## 📝 Log File Location & Contents

### Location
```bash
~/sec_filing_parser/data/NVDA/logs/processing_monesh.log
```

### How to View
```bash
# View entire log
cat ~/sec_filing_parser/data/NVDA/logs/processing_*.log

# View last 50 lines
tail -50 ~/sec_filing_parser/data/NVDA/logs/processing_*.log

# View with line numbers
cat -n ~/sec_filing_parser/data/NVDA/logs/processing_*.log

# Search for errors
grep -i "error\|failed" ~/sec_filing_parser/data/NVDA/logs/processing_*.log

# Watch real-time (if script is running)
tail -f ~/sec_filing_parser/data/NVDA/logs/processing_*.log
```

### Log File Content Example

```
2026-02-23 20:51:04,682 - SECFilingParser - INFO - ======================================================================
2026-02-23 20:51:04,682 - SECFilingParser - INFO - Starting SEC Filing Parser for ticker: NVDA
2026-02-23 20:51:04,682 - SECFilingParser - INFO - ======================================================================
2026-02-23 20:51:04,682 - SECFilingParser - INFO - Initializing SEC Edgar client...
2026-02-23 20:51:04,682 - SECFilingParser - INFO - Converting ticker 'NVDA' to CIK...
2026-02-23 20:51:05,215 - SECFilingParser - INFO - ✓ Found CIK: 0001045810 for ticker NVDA
2026-02-23 20:51:05,215 - SECFilingParser - INFO - ✓ Created output directories in /home/monesh/sec_filing_parser/data/NVDA
2026-02-23 20:51:05,215 - SECFilingParser - INFO - Retrieving 3-year filing history...
2026-02-23 20:51:05,590 - SECFilingParser - INFO - ✓ Retrieved 11 filings
2026-02-23 20:51:05,590 - SECFilingParser - INFO - Downloading filing PDFs...
2026-02-23 20:51:05,590 - SECFilingParser - INFO - [1/11] Downloading 10-Q filed 2025-11-19 (accession: 0001045810-25-000230)
2026-02-23 20:51:05,859 - SECFilingParser - ERROR -   ✗ Failed to download
... (more log lines)
2026-02-23 20:51:07,241 - SECFilingParser - INFO - ======================================================================
2026-02-23 20:51:07,241 - SECFilingParser - INFO - PHASE 2 COMPLETE: SEC Data Retrieval
2026-02-23 20:51:07,241 - SECFilingParser - INFO - ======================================================================
2026-02-23 20:51:07,241 - SECFilingParser - INFO - Ticker:         NVDA
2026-02-23 20:51:07,241 - SECFilingParser - INFO - CIK:            0001045810
2026-02-23 20:51:07,241 - SECFilingParser - INFO - Filings found:  11
2026-02-23 20:51:07,241 - SECFilingParser - INFO - PDFs downloaded: 0
```

### What Each Log Line Tells You

| Log Message | Meaning | Status |
|-------------|---------|--------|
| `✓ Found CIK:` | Ticker validation succeeded | ✅ OK |
| `Retrieved 11 filings` | Found the right amount of filings | ✅ OK |
| `XBRL: True` | Machine-readable data available | ✅ OK |
| `✗ Failed to download` | PDF download not working (Phase 2 limitation) | ⚠️ Expected |
| `ERROR` | Something went wrong | ❌ Problem |

---

## 🔍 Multi-Ticker Output

### After Running: `python main.py NVDA AAPL MSFT`

```
~/sec_filing_parser/data/
│
├── NVDA/
│   ├── raw/     (0 files - PDF download not implemented)
│   ├── parsed/  (0 files - XML generation is Phase 5)
│   └── logs/
│       └── processing_monesh.log
│
├── AAPL/
│   ├── raw/
│   ├── parsed/
│   └── logs/
│       └── processing_monesh.log
│
└── MSFT/
    ├── raw/
    ├── parsed/
    └── logs/
        └── processing_monesh.log
```

### Console Output Summary

```
======================================================================
SEC Filing Parser
======================================================================
Processing 3 ticker(s): NVDA, AAPL, MSFT
======================================================================

NVDA Results:
  Success: True
  CIK: 0001045810
  Filings found: 11
  PDFs downloaded: 0

AAPL Results:
  Success: True
  CIK: 0000320193
  Filings found: 11
  PDFs downloaded: 0

MSFT Results:
  Success: True
  CIK: 0000789019
  Filings found: 11
  PDFs downloaded: 0

======================================================================
FINAL SUMMARY
======================================================================
Tickers processed: 3/3
Total PDFs downloaded: 0
Data stored in: /home/monesh/sec_filing_parser/data/
======================================================================
```

---

## 📂 Raw Files Directory (Empty for Phase 2)

### Location
```bash
~/sec_filing_parser/data/NVDA/raw/
```

### Content (Phase 2)
```bash
$ ls -la ~/sec_filing_parser/data/NVDA/raw/
total 8
(empty directory)
```

### What Will Be There (Phase 3+)
```bash
$ ls -la ~/sec_filing_parser/data/NVDA/raw/
total 450000
-rw-r--r-- 1 monesh monesh  45000000 Feb 23 20:51 NVDA_10-K_2025-01-26_0001045810-25-000023.pdf
-rw-r--r-- 1 monesh monesh  35000000 Feb 23 20:51 NVDA_10-Q_2024-10-27_0001045810-24-000108.pdf
-rw-r--r-- 1 monesh monesh  32000000 Feb 23 20:51 NVDA_10-Q_2024-07-28_0001045810-24-000075.pdf
... (more PDFs)
```

### File Naming Pattern
```
{TICKER}_{FORM_TYPE}_{FILING_DATE}_{ACCESSION_NO_HYPHENS}.pdf

Example:
NVDA_10-K_2025-01-26_0001045810-25-000023.pdf
│    │    │           └─ Accession number (unique ID)
│    │    └─ Filing date
│    └─ Form type (10-K or 10-Q)
└─ Ticker symbol
```

---

## 📋 Parsed Directory (Empty for Phase 2)

### Location
```bash
~/sec_filing_parser/data/NVDA/parsed/
```

### Content (Phase 2)
```bash
$ ls -la ~/sec_filing_parser/data/NVDA/parsed/
total 8
(empty directory)
```

### What Will Be There (Phase 5+)
```bash
$ ls -la ~/sec_filing_parser/data/NVDA/parsed/
total 5000
-rw-r--r-- 1 monesh monesh  500000 Feb 24 10:23 NVDA_10-K_2025-01-26_0001045810-25-000023.xml
-rw-r--r-- 1 monesh monesh  400000 Feb 24 10:23 NVDA_10-Q_2024-10-27_0001045810-24-000108.xml
-rw-r--r-- 1 monesh monesh  380000 Feb 24 10:23 NVDA_10-Q_2024-07-28_0001045810-24-000075.xml
... (more XMLs with financial data)
```

### XML File Contents (Preview - Phase 5)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Filing>
  <Metadata>
    <Ticker>NVDA</Ticker>
    <CIK>0001045810</CIK>
    <FilingType>10-K</FilingType>
    <FilingDate>2025-01-26</FilingDate>
    <FiscalPeriodEnd>2025-01-26</FiscalPeriodEnd>
  </Metadata>

  <FinancialStatements>
    <IncomeStatement>
      <Period>
        <StartDate>2024-01-28</StartDate>
        <EndDate>2025-01-26</EndDate>
      </Period>

      <LineItem>
        <Concept>Revenue</Concept>
        <Value>130500000000</Value>
        <Unit>USD</Unit>
        <Confidence>HIGH</Confidence>
        <Source>XBRL</Source>
      </LineItem>
      <!-- ... more financial data ... -->
    </IncomeStatement>
  </FinancialStatements>

  <AuditTrail>
    <!-- Data extraction history and sources -->
  </AuditTrail>
</Filing>
```

---

## 🔎 What to Inspect After Running

### Immediate Checks (After `python main.py NVDA`)

**Check 1: Directories Created**
```bash
ls -la ~/sec_filing_parser/data/NVDA/
# Should show: raw/  parsed/  logs/
```

**Check 2: Log File Exists**
```bash
ls -la ~/sec_filing_parser/data/NVDA/logs/
# Should show: processing_monesh.log
```

**Check 3: Log File Is Not Empty**
```bash
wc -l ~/sec_filing_parser/data/NVDA/logs/processing_*.log
# Should show: 20+ lines
```

**Check 4: Log File Has No Errors**
```bash
grep -i "error" ~/sec_filing_parser/data/NVDA/logs/processing_*.log
# Should return: Nothing (no errors expected)
```

### Deep Inspection (Code Review)

**Check 5: Verify CIK Correctness**
```bash
# Extract CIK from log
grep "Found CIK" ~/sec_filing_parser/data/NVDA/logs/processing_*.log
# Should show: ✓ Found CIK: 0001045810

# Verify on SEC.gov:
# Visit: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001045810
# Should show NVIDIA CORP
```

**Check 6: Verify Filing Count**
```bash
# Extract filing count
grep "Retrieved.*filings" ~/sec_filing_parser/data/NVDA/logs/processing_*.log
# Should show: ✓ Retrieved 11 filings

# Verify on SEC.gov:
# Visit above URL and count 10-K, 10-Q from past 3 years
# Should match 11
```

**Check 7: Check XBRL Availability**
```bash
# Look for XBRL mentioned in logs
grep -i "xbrl" ~/sec_filing_parser/data/NVDA/logs/processing_*.log
# Should show: Multiple lines mentioning XBRL URLs
```

---

## 📊 Directory Size Reference

### Expected Sizes (After Full Implementation)

```
~/sec_filing_parser/data/NVDA/

raw/        ~450 MB    (11 PDFs, each 30-50 MB)
parsed/     ~5 MB      (11 XMLs, each 400-500 KB)
logs/       ~1 MB      (detailed processing log)
────────────────────
Total:      ~456 MB per ticker
```

### Phase 2 Sizes (No PDFs Yet)
```
raw/        ~0 KB      (empty - not downloading yet)
parsed/     ~0 KB      (empty - Phase 5 only)
logs/       ~0.1 MB    (just the log file)
────────────────────
Total:      ~0.1 MB per ticker (very small)
```

---

## 🔗 File Relationships

### How Files Work Together

```
config.py
  ↓ (provides paths and URLs)
  ├─→ main.py (uses paths and URLs)
  │    ├─→ Creates directories based on paths
  │    └─→ Calls SECClient
  │
  └─→ src/sec_client.py (uses User-Agent from config)
       ├─→ Queries SEC Edgar API
       └─→ Returns filing metadata

tests/test_sec_client.py
  └─→ Mocks SEC Client for fast testing
```

### Data Flow

```
Input: "NVDA"
  ↓
SECClient.get_cik_from_ticker()
  ├─ Query SEC API
  └─ Return: "0001045810"
    ↓
SECClient.get_filings()
  ├─ Query SEC API with CIK
  └─ Return: 11 filings metadata
    ↓
main.py creates:
  ├─ ~/sec_filing_parser/data/NVDA/raw/
  ├─ ~/sec_filing_parser/data/NVDA/parsed/
  ├─ ~/sec_filing_parser/data/NVDA/logs/
  │   └─ Log file with all details
  └─ Console output with summary
```

---

## ✅ Manual Review Checklist

Use this to verify everything is in the right place:

### Directory Structure
- [ ] `/home/monesh/10Q_2/` exists (project root)
- [ ] `config.py` exists
- [ ] `main.py` exists
- [ ] `src/sec_client.py` exists
- [ ] `tests/test_sec_client.py` exists

### Output After Running
- [ ] `~/sec_filing_parser/data/NVDA/` created
- [ ] `~/sec_filing_parser/data/NVDA/raw/` created
- [ ] `~/sec_filing_parser/data/NVDA/parsed/` created
- [ ] `~/sec_filing_parser/data/NVDA/logs/` created
- [ ] `processing_*.log` file exists and has content

### Log File Quality
- [ ] Log file is readable text
- [ ] Contains "Found CIK: 0001045810"
- [ ] Contains "Retrieved 11 filings"
- [ ] Contains "PHASE 2 COMPLETE"
- [ ] No ERROR or CRITICAL messages

---

## 🎯 Summary of What's Stored Where

| Component | Location | Phase | Size | Status |
|-----------|----------|-------|------|--------|
| Configuration | `config.py` | 1 | 5 KB | ✅ Done |
| SEC Client | `src/sec_client.py` | 2 | 20 KB | ✅ Done |
| Main Script | `main.py` | 2 | 15 KB | ✅ Done |
| Unit Tests | `tests/test_sec_client.py` | 2 | 25 KB | ✅ Done |
| Raw PDFs | `~/sec_filing_parser/data/{TICKER}/raw/` | 3 | 0 (empty) | ⏳ Coming |
| Parsed XML | `~/sec_filing_parser/data/{TICKER}/parsed/` | 5 | 0 (empty) | ⏳ Coming |
| Logs | `~/sec_filing_parser/data/{TICKER}/logs/` | 2 | 0.1 MB | ✅ Done |

---

## 📞 Quick Navigation

**Looking for a specific file?**
- Configuration → `config.py`
- SEC API wrapper → `src/sec_client.py`
- Main pipeline → `main.py`
- Unit tests → `tests/test_sec_client.py`
- Log files → `~/sec_filing_parser/data/{TICKER}/logs/`
- Raw files → `~/sec_filing_parser/data/{TICKER}/raw/` (empty for Phase 2)
- Parsed output → `~/sec_filing_parser/data/{TICKER}/parsed/` (empty for Phase 2)

**Looking for documentation?**
- Quick commands → `/manual-tests/QUICK_REFERENCE.md`
- Step-by-step guide → `/manual-tests/MANUAL_TESTING_GUIDE.md`
- Code explanation → `/manual-tests/CODE_WALKTHROUGH.md`
- This file → `/manual-tests/FILE_LOCATIONS_AND_OUTPUT.md`
