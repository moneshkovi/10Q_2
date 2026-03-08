# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 🎯 Project Overview

**SEC Filing Parser**: A production-grade system that retrieves and parses financial data from SEC Edgar filings.

**Current Status**: ALL PHASES COMPLETE (Production Ready)
- ✅ Phase 1: Project setup and configuration
- ✅ Phase 2: SEC Edgar filing metadata retrieval + XBRL availability checking
- ✅ Phase 3: XBRL financial data extraction
- ✅ Phase 4: Data reconciliation and validation
- ✅ Phase 5: XML/CSV output generation
- ✅ Phase 6: CLI orchestration and production polish
- ✅ Phase 7: DCF valuation model (industry standard)

**Tests**: 121/121 passing
**Architecture**: SEC Edgar API → XBRL Extraction → Validation → XML/CSV/DCF Output

---

## 🔧 Quick Commands

### Development Setup
```bash
# Activate conda environment
source ~/miniconda3/etc/profile.d/conda.sh
conda activate 10Q
cd /home/monesh/10Q_2

# Install dependencies (if needed)
pip install -r requirements.txt

# Install optional test dependencies
pip install pytest pytest-cov
```

### Running the Full Pipeline
```bash
# Process single ticker (all 7 phases)
python main.py NVDA

# Process multiple tickers
python main.py AAPL MSFT GOOG TSLA BLK

# Expected output:
# - CIK retrieval + filing metadata (5-year lookback)
# - XBRL metrics extraction (317+ metrics)
# - Data validation + quality score
# - XML + CSV output (4 files per ticker)
# - DCF valuation (fair value per share + sensitivity)
# - Comparison reports (multi-ticker runs)
```

### Testing
```bash
# Run all 121 unit tests
pytest tests/ -v

# Run specific phase tests
pytest tests/test_sec_client.py -v       # Phase 2 (20 tests)
pytest tests/test_xbrl_parser.py -v      # Phase 3 (19 tests)
pytest tests/test_validator.py -v        # Phase 4 (22 tests)
pytest tests/test_xml_builder.py -v      # Phase 5 (17 tests)
pytest tests/test_cli_enhancements.py -v # Phase 6 (17 tests)
pytest tests/test_dcf_calculator.py -v   # Phase 7 (26 tests)

# Run with coverage report
pytest tests/test_sec_client.py --cov=src --cov-report=html

# Expected: 121/121 tests PASSING
```

### Debugging
```bash
# View logs while running
tail -f ~/sec_filing_parser/data/NVDA/logs/processing_*.log

# Check what's in a specific directory
ls -lh ~/sec_filing_parser/data/NVDA/

# Expected structure:
# ├── logs/        → Processing logs
# ├── raw/         → (Empty for Phase 2 - XBRL data fetched via API in Phase 3)
# └── parsed/      → (Empty for Phase 2 - populated in Phase 3+)
```

---

## 📁 Important Files & Architecture

### Core Implementation Files

**`config.py` (110 lines)**
- All configuration constants: SEC API URLs, paths, timeouts, thresholds
- Key URLs:
  - `SEC_EDGAR_SUBMISSIONS_API = "https://data.sec.gov/submissions"`
  - `SEC_EDGAR_COMPANY_TICKERS = "https://www.sec.gov/files/company_tickers.json"`
- User-Agent: `"SECFilingParser/1.0 (research; monesh.kovi@gmail.com)"`
- **NEVER hardcode** constants here - always use config module

**`src/sec_client.py` (420 lines)**
- `SECClient` class: Main API client for SEC Edgar
- Key methods:
  - `get_cik_from_ticker(ticker)` → Converts NYSE ticker to CIK
  - `get_filings(cik, form_types, years)` → Retrieves filing metadata
  - `get_xbrl_url(accession)` → Generates XBRL viewer URL
  - `download_filing_pdf()` → (BLOCKED BY SEC - do not use)
- Exceptions: `TickerNotFoundError`, `SECAPIError`, `FilingNotFoundError`
- Session management with automatic retries (3 attempts, exponential backoff)

**`main.py` (323 lines)**
- `process_ticker(ticker)` → Complete Phase 2 pipeline
  1. Validates ticker via company_tickers.json
  2. Retrieves CIK
  3. Fetches 3-year filing history
  4. Checks XBRL availability (doesn't download PDFs - they're blocked)
- `setup_logging(ticker)` → Configures logging to file + console
- CLI interface with support for multiple tickers

**`tests/test_sec_client.py` (492 lines)**
- 20 comprehensive unit tests (all PASSING)
- All tests use mocked SEC API responses (no network calls during tests)
- Test classes:
  - `TestGetCIKFromTicker` (8 tests)
  - `TestGetFilings` (6 tests)
  - `TestGetXBRLURL` (2 tests)
  - `TestDownloadFilingPDF` (4 tests)
- Important: Mocks prevent SEC bot detection during testing

---

## 🔑 Key Technical Concepts

### SEC API Endpoints (Phase 2)
```
✓ WORKING:
  - /filings/company_tickers.json → List of all tickers + CIKs
  - /submissions/CIK{cik}.json → Filing metadata for a company

✗ BLOCKED (403 Forbidden):
  - /Archives/edgar/data/... → Filing directory index (SEC bot detection)
  - /api/xbrl/* → Most XBRL endpoints when accessed directly

ℹ️ WILL USE IN PHASE 3:
  - /api/xbrl/companyfacts/CIK{cik}.json → Company's XBRL financial data
     (This works! Used for direct data extraction in Phase 3)
```

### Data Flow
```
User Input (ticker: "NVDA")
  ↓
[PHASE 2 - Current]
  ├─ get_cik_from_ticker("NVDA") → "0001045810"
  ├─ get_filings(cik, ["10-K", "10-Q"], 3) → [filing metadata]
  └─ get_xbrl_url(accession) → Store XBRL URLs
  ↓
[PHASE 3 - Next]
  ├─ Fetch /api/xbrl/companyfacts/CIK0001045810.json
  ├─ Parse financial metrics (revenue, net income, etc.)
  └─ Generate structured data
  ↓
[PHASE 4 - Later]
  ├─ Validate data quality
  ├─ Cross-reference sources
  └─ Flag discrepancies
  ↓
[PHASE 5 - Later]
  └─ Generate XML output with audit trail
```

### Filing Metadata Structure
```python
filing = {
    "accession_number": "0001045810-25-000023",
    "filing_date": "2025-02-26",
    "fiscal_period_end": "2025-01-26",
    "form_type": "10-K",
    "is_xbrl": True,  # Indicates XBRL data available
    "xbrl_url": "https://www.sec.gov/cgi-bin/viewer?..."
}
```

---

## ⚠️ Critical Issues & Solutions

### SEC Bot Detection (KNOWN ISSUE)
**Problem**: SEC blocks automated HTTP requests with 403 "Your Request Originates from an Undeclared Automated Tool"

**Affected**: Trying to fetch `/Archives/edgar/data/{cik}/` filing index pages

**Solution**: Use `/api/xbrl/companyfacts/` endpoint in Phase 3 instead. This endpoint works without bot detection.

**Do NOT**:
- ✗ Try to work around 403 by changing User-Agent headers
- ✗ Use Selenium/browser automation (too slow for production)
- ✗ Attempt to bypass SEC's restrictions
- ✗ Try PDF downloads (Phase 2) - they don't work

**Do**:
- ✓ Use XBRL API in Phase 3 (preferred data source anyway)
- ✓ Cache results to reduce API calls
- ✓ Respect SEC rate limits (0.1s delay between requests)

### Common Errors

**`TickerNotFoundError`**
- Cause: Ticker doesn't exist in SEC Edgar database
- Solution: Check spelling, ensure NYSE ticker
- Example: "FAKE" → Error

**`SECAPIError`**
- Cause: Network error or SEC API returns bad response
- Solution: Check logs, retry with delay
- Location: src/sec_client.py line 145

**`KeyError: 'pdfs_downloaded'`**
- Cause: Code references old Phase 2 metric names
- Solution: Use `xbrl_available` instead
- Fixed in: main.py (updated Feb 23, 2026)

---

## 🧪 Testing Strategy

### Unit Tests (Phase 2)
```bash
pytest tests/test_sec_client.py -v
```
- All tests mock SEC API responses
- No actual network calls during testing
- Verify: All 20 tests PASS

### Integration Tests (Manual)
```bash
python main.py NVDA
# Verify:
# - CIK found: 0001045810
# - Filings retrieved: 11
# - XBRL availability: 11 with XBRL, 0 without
# - Success: True
```

### Test with Multiple Tickers
```bash
python main.py AAPL MSFT GOOG TSLA NVDA
# Each should return similar success metrics
```

---

## 📊 Expected Output

### Phase 2 Log Output
```
2026-02-23 21:38:41,017 - SECFilingParser - INFO - ✓ Found CIK: 0001045810 for ticker NVDA
2026-02-23 21:38:41,017 - SECFilingParser - INFO - ✓ Retrieved 11 filings
2026-02-23 21:38:41,017 - SECFilingParser - INFO - [1/11] 10-Q filed 2025-11-19
2026-02-23 21:38:41,017 - SECFilingParser - INFO -   ✓ XBRL data available (will parse in Phase 3)
...
2026-02-23 21:38:41,017 - SECFilingParser - INFO - ✓ Data check complete: 11 with XBRL, 0 without
```

### Directory Structure After Run
```
~/sec_filing_parser/data/NVDA/
├── logs/
│   └── processing_2026-02-23_*.log    # Processing details
├── raw/                                # (Empty - XBRL fetched via API in Phase 3)
└── parsed/                             # (Empty - generated in Phase 3+)
```

---

## 🚀 Workflow for Next Phases

### Phase 3: XBRL Data Extraction
**Location to implement**: `src/xbrl_parser.py` (new file)

**Key method**:
```python
def parse_xbrl_data(cik: str, filing_date: str) -> Dict:
    """Fetch and parse XBRL financial data from SEC API."""
    response = requests.get(
        f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    )
    xbrl_data = response.json()

    # Extract key metrics
    metrics = {
        'revenue': xbrl_data.get('us-gaap:Revenues'),
        'net_income': xbrl_data.get('us-gaap:NetIncomeLoss'),
        'total_assets': xbrl_data.get('us-gaap:Assets'),
        ...
    }
    return metrics
```

**Reference**: `SEC_API_INVESTIGATION.md` for detailed API structure

### Phase 4: Reconciliation
**Logic**:
- Compare XBRL data from different periods
- Validate against financial ratios
- Flag inconsistencies (>5% difference)

### Phase 5: XML Output
**Schema**: See `SEC_Filing_Parser_Specification.md` for full XML schema
**Tool**: `xml.etree.ElementTree` or `lxml`

---

## 📚 Documentation Files

| File | Purpose | Read When |
|------|---------|-----------|
| `README.md` | Project overview | Starting out |
| `SEC_Filing_Parser_Specification.md` | Complete design spec | Implementing phases |
| `SEC_Filing_Parser_QuickRef.md` | Developer cheat sheet | Coding |
| `SEC_API_INVESTIGATION.md` | Root cause analysis | Understanding bot detection |
| `/manual-tests/` directory | Testing guides | Testing Phase 2 |

---

## 💡 Pro Tips

1. **Logging is your friend**: Always check logs in `~/sec_filing_parser/data/{TICKER}/logs/` first when debugging

2. **Respect SEC rate limits**: 0.1s delay between requests is already implemented. Don't remove it.

3. **Cache results**: Filing metadata doesn't change frequently. Consider caching to reduce API calls.

4. **Use mocking in tests**: Never make real API calls during testing. Mock all SEC responses.

5. **Keep configuration centralized**: All constants go in `config.py`. Never hardcode values in functions.

6. **Type hints everywhere**: All functions have type hints. Maintain this standard.

7. **Google docstring format**: All docstrings follow Google format. Match this style.

8. **Test before committing**: Always run `pytest` before making changes.

---

## 🎯 Phase 2 Success Criteria (ACHIEVED ✓)

- [x] Ticker validation works
- [x] CIK lookup works
- [x] Filing metadata retrieval works (11 filings for NVDA)
- [x] XBRL availability detection works
- [x] All 20 unit tests PASS
- [x] Multi-ticker support works
- [x] Logging is informative
- [x] Error handling is comprehensive
- [x] SEC bot detection documented and worked around

---

## 📞 Debugging Checklist

When something breaks:
1. Check logs first: `~/sec_filing_parser/data/{TICKER}/logs/processing_*.log`
2. Run single ticker in debug mode: `python -u main.py NVDA 2>&1 | head -100`
3. Check network: `ping data.sec.gov` (SEC API should be reachable)
4. Verify ticker: `python main.py FAKE` (should give clear error)
5. Check config: Verify `config.py` URLs are correct
6. Run tests: `pytest tests/ -v` (should all pass: 121/121)

---

**Last Updated**: March 8, 2026
**Phase Status**: 7/7 Complete (PRODUCTION READY)
**Test Status**: 121/121 PASSING
**Status**: All phases complete

---

## 🚀 Phase 3 Implementation (COMPLETED ✅)

**Status**: Phase 3 implemented, tested, and production-ready
**Date Completed**: February 23, 2026
**Test Coverage**: 19/19 tests PASSING with real SEC data

### Phase 3: XBRL Financial Data Extraction

```bash
# Run Phases 2 & 3 automatically:
python main.py NVDA

# Output:
# - Retrieves 11 filings (Phase 2)
# - Extracts 275 metrics (Phase 3)
# - Saves JSON with confidence scores and YoY analysis
```

### Files for Phase 3

**`src/xbrl_parser.py` (419 lines)**
- `XBRLParser` class for XBRL data extraction
- Methods:
  - `fetch_xbrl_data(cik)` - Fetch from SEC API
  - `extract_metrics_for_filings()` - Main pipeline
  - `_calculate_confidence()` - Score data quality
  - `_calculate_yoy_change()` - YoY comparisons
  - `save_metrics_to_json()` - Write output

**`tests/test_xbrl_parser.py` (550+ lines)**
- 19 comprehensive unit tests
- All tests use REAL SEC data (no mocking!)
- Test categories:
  - Data fetching from SEC API
  - Metric extraction (615 metrics)
  - Confidence scoring (0-100%)
  - Year-over-year calculations
  - JSON file generation
  - Multiple companies
  - Edge cases
  - Full pipeline integration

### Test Results

```
Phase 2 + Phase 3 Combined Tests:
  39/39 PASSING ✓

Breakdown:
  Phase 2 (SEC Client):   20/20 ✓
  Phase 3 (XBRL Parser):  19/19 ✓
```

### Phase 3 Output

```json
{
  "cik": "0001045810",
  "entity_name": "NVIDIA CORP",
  "filings_processed": 11,
  "metrics_extracted": 275,
  "metrics": {
    "Revenues:USD": {
      "name": "Revenues",
      "unit": "USD",
      "confidence": 100.0,
      "values": [
        {
          "val": 60240000000,
          "end": "2025-01-26",
          "form": "10-K",
          "filed": "2025-02-26",
          "in_target_filing": true
        }
      ],
      "yoy_change": {
        "yoy_comparisons": [
          {
            "period": "FY",
            "current_year": 2025,
            "prior_year": 2024,
            "change_percent": 45.3
          }
        ]
      }
    }
  }
}
```

### Key Features

✅ **Comprehensive Extraction**
- Fetches all 615 US-GAAP metrics
- 275+ metrics per company
- Complete 3-year history

✅ **Confidence Scoring**
- 100% for metrics from target filings
- Automatic quality assessment
- Used for downstream validation

✅ **Year-over-Year Analysis**
- Automatic period-to-period comparison
- Quarterly and annual comparisons
- Percentage change calculations

✅ **Structured Output**
- JSON format for easy parsing
- Complete audit trail
- Links back to original filings

### Verified Companies

| Ticker | Filings | Metrics | Confidence |
|--------|---------|---------|------------|
| NVDA   | 11      | 275     | 100%       |
| AAPL   | 12      | 211     | 100%       |
| MSFT   | 12      | 258     | 100%       |
| GOOG   | 12      | 250+    | 100%       |
| TSLA   | 12      | 240+    | 100%       |

### Running Phase 3

```bash
# Automatic (Phase 2 + 3):
python main.py NVDA AAPL MSFT

# Check output:
ls -lh ~/sec_filing_parser/data/NVDA/parsed/
cat ~/sec_filing_parser/data/NVDA/parsed/NVDA_xbrl_metrics.json | jq .
```

### Performance

- **Per Ticker**: ~4-5 seconds (fetch + extract + save)
- **Scalability**: Linear (4-5 sec per additional ticker)
- **Output Size**: ~2.3 MB JSON per company

---

## Current Status (As of March 8, 2026)

✅ **Phase 1**: Project setup (COMPLETE)
✅ **Phase 2**: SEC data retrieval (COMPLETE - 20/20 tests)
✅ **Phase 3**: XBRL extraction (COMPLETE - 19/19 tests)
✅ **Phase 4**: Data validation (COMPLETE - 22/22 tests)
✅ **Phase 5**: XML/CSV output (COMPLETE - 17/17 tests)
✅ **Phase 6**: CLI enhancements (COMPLETE - 17/17 tests)
✅ **Phase 7**: DCF valuation (COMPLETE - 26/26 tests)

---

**Total Tests Passing**: 121/121 ✓
**Code Quality**: Type hints, docstrings, comprehensive error handling
**Production Ready**: YES

---

## 📁 Complete File Structure

### Source Files
| File | Lines | Purpose |
|------|-------|---------|
| `config.py` | 195 | All configuration (SEC API, DCF params, betas) |
| `main.py` | 650 | CLI entry point & pipeline orchestration |
| `src/sec_client.py` | 420 | SEC Edgar API client |
| `src/xbrl_parser.py` | 419 | XBRL data extraction |
| `src/validator.py` | 430 | Data validation rules |
| `src/data_reconciler.py` | 310 | Validation orchestration |
| `src/xml_builder.py` | 450 | XML output generator |
| `src/csv_builder.py` | 400 | CSV export engine |
| `src/cli_enhancements.py` | 324 | CLI features (progress, colors) |
| `src/dcf_calculator.py` | 850 | DCF valuation model |

### Test Files
| File | Tests | Purpose |
|------|-------|---------|
| `tests/test_sec_client.py` | 20 | SEC API client tests |
| `tests/test_xbrl_parser.py` | 19 | XBRL extraction tests |
| `tests/test_validator.py` | 22 | Validation tests |
| `tests/test_xml_builder.py` | 17 | XML/CSV output tests |
| `tests/test_cli_enhancements.py` | 17 | CLI feature tests |
| `tests/test_dcf_calculator.py` | 26 | DCF model tests |

### Documentation
| File | Purpose |
|------|---------|
| `CLAUDE.md` | Developer guide |
| `DCF_MODEL.md` | DCF terms explained |
| `CSV_EXPORT_GUIDE.md` | CSV usage guide |
| `PHASE_*_COMPLETE.md` | Phase completion reports |
| `PROJECT_COMPLETE.md` | Project summary |

