# Quick Reference: Manual Testing Commands & Output

**Quick copy-paste commands for manual testing Phase 1 & 2**

---

## 🚀 Quick Start Commands

### 1. Setup Environment
```bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate 10Q
cd /home/monesh/10Q_2
```

### 2. Run Unit Tests (Mocked API)
```bash
pytest tests/test_sec_client.py -v
```

**Expected Output:**
```
============================= 20 passed in 0.30s ==============================
PASSED tests/test_sec_client.py::TestGetCIKFromTicker::test_valid_ticker_nvda
PASSED tests/test_sec_client.py::TestGetCIKFromTicker::test_valid_ticker_lowercase
... (18 more PASSED)
```

### 3. Run Real SEC Data Test (Single Ticker)
```bash
python main.py NVDA
```

**Expected Output (summary):**
```
Starting SEC Filing Parser for ticker: NVDA
✓ Found CIK: 0001045810 for ticker NVDA
✓ Created output directories
✓ Retrieved 11 filings
PHASE 2 COMPLETE: SEC Data Retrieval
```

### 4. Run Multi-Ticker Test
```bash
python main.py NVDA AAPL MSFT
```

**Expected Output (summary):**
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

## 📂 File Inspection Commands

### View Output Directory
```bash
ls -la ~/sec_filing_parser/data/NVDA/
```

**Expected Output:**
```
drwxr-xr-x ... NVDA
  drwxr-xr-x ... raw/
  drwxr-xr-x ... parsed/
  drwxr-xr-x ... logs/
```

### View Log File
```bash
cat ~/sec_filing_parser/data/NVDA/logs/processing_*.log
```

**Sample Lines:**
```
2026-02-23 20:51:04,682 - INFO - Converting ticker 'NVDA' to CIK...
2026-02-23 20:51:05,215 - INFO - ✓ Found CIK: 0001045810 for ticker NVDA
2026-02-23 20:51:05,590 - INFO - ✓ Retrieved 11 filings
```

### Check Raw Files Directory (empty for now)
```bash
ls -la ~/sec_filing_parser/data/NVDA/raw/
```

**Expected Output:**
```
total 8
(empty - PDF downloads not yet implemented)
```

### Check Parsed Directory (empty for now)
```bash
ls -la ~/sec_filing_parser/data/NVDA/parsed/
```

**Expected Output:**
```
total 8
(empty - XML generation not yet implemented - Phase 5)
```

---

## 🔍 Code Review Commands

### View Configuration
```bash
cat /home/monesh/10Q_2/config.py | head -50
```

### View SEC Client Main Methods
```bash
# View get_cik_from_ticker method
sed -n '/def get_cik_from_ticker/,/def get_filings/p' /home/monesh/10Q_2/src/sec_client.py | head -40

# View get_filings method
sed -n '/def get_filings/,/def download_filing_pdf/p' /home/monesh/10Q_2/src/sec_client.py | head -50
```

### View Main Pipeline
```bash
sed -n '/def process_ticker/,/return result/p' /home/monesh/10Q_2/main.py | head -60
```

---

## 📊 Data Verification Commands

### Get Detailed Filing Info for NVDA
```bash
python << 'EOF'
import sys
sys.path.insert(0, '/home/monesh/10Q_2')
from src.sec_client import SECClient

client = SECClient()
cik = client.get_cik_from_ticker("NVDA")
filings = client.get_filings(cik, ["10-K", "10-Q"], years=3)

print(f"Ticker: NVDA")
print(f"CIK: {cik}")
print(f"Total Filings: {len(filings)}\n")

print("Filing Details:")
for i, f in enumerate(filings, 1):
    print(f"{i:2d}. {f['form_type']:4s} - Filed: {f['filing_date']} - Period: {f['fiscal_period_end']} - XBRL: {f['is_xbrl']}")
EOF
```

**Expected Output:**
```
Ticker: NVDA
CIK: 0001045810
Total Filings: 11

Filing Details:
 1. 10-Q - Filed: 2025-11-19 - Period: 2025-10-26 - XBRL: True
 2. 10-Q - Filed: 2025-08-27 - Period: 2025-07-27 - XBRL: True
 3. 10-Q - Filed: 2025-05-28 - Period: 2025-04-27 - XBRL: True
 4. 10-K - Filed: 2025-02-26 - Period: 2025-01-26 - XBRL: True
 ... (7 more)
```

### Test Ticker Validation with Invalid Ticker
```bash
python << 'EOF'
import sys
sys.path.insert(0, '/home/monesh/10Q_2')
from src.sec_client import SECClient, TickerNotFoundError

client = SECClient()
try:
    cik = client.get_cik_from_ticker("INVALID123")
    print("ERROR: Should have raised TickerNotFoundError!")
except TickerNotFoundError as e:
    print(f"✓ Correctly caught error: {e}")
EOF
```

**Expected Output:**
```
✓ Correctly caught error: Ticker 'INVALID123' not found in SEC Edgar
```

### Verify XBRL URLs
```bash
python << 'EOF'
import sys
sys.path.insert(0, '/home/monesh/10Q_2')
from src.sec_client import SECClient

client = SECClient()
cik = client.get_cik_from_ticker("NVDA")
filings = client.get_filings(cik, ["10-K"], years=1)

if filings:
    accession = filings[0]["accession_number"]
    xbrl_url = client.get_xbrl_url(accession)
    print(f"Sample XBRL URL:")
    print(f"{xbrl_url}")
EOF
```

**Expected Output:**
```
Sample XBRL URL:
https://www.sec.gov/cgi-bin/viewer?action=view&cik=1045810&accession_number=0001045810-25-000023&xbrl_type=v
```

---

## ✅ Full Manual Testing Script

Save this as `~/manual-test.sh` and run it:

```bash
#!/bin/bash

echo "======================================================================"
echo "Phase 1 & 2 Manual Testing"
echo "======================================================================"

source ~/miniconda3/etc/profile.d/conda.sh
conda activate 10Q
cd /home/monesh/10Q_2

echo ""
echo "Test 1: Unit Tests (Mocked API)"
echo "----------------------------------------------------------------------"
pytest tests/test_sec_client.py -v --tb=short
TEST1=$?

echo ""
echo "Test 2: Real SEC Data - NVDA"
echo "----------------------------------------------------------------------"
python main.py NVDA
TEST2=$?

echo ""
echo "Test 3: Check Output Directory"
echo "----------------------------------------------------------------------"
ls -la ~/sec_filing_parser/data/NVDA/
echo ""
echo "Log file:"
tail -20 ~/sec_filing_parser/data/NVDA/logs/processing_*.log

echo ""
echo "======================================================================"
echo "Summary"
echo "======================================================================"
if [ $TEST1 -eq 0 ] && [ $TEST2 -eq 0 ]; then
    echo "✅ ALL TESTS PASSED"
else
    echo "❌ SOME TESTS FAILED"
fi
```

Run it:
```bash
bash ~/manual-test.sh
```

---

## 🔎 What to Look For

### ✅ Green Flags (Everything is Good)
- [ ] All 20 unit tests PASSED
- [ ] No RED or ERROR messages
- [ ] CIK values are 10 digits (zero-padded)
- [ ] Filing counts are reasonable (8-15 per ticker)
- [ ] XBRL availability is True for most filings
- [ ] Log file is clean with no error messages
- [ ] Output directories are created

### ⚠️ Yellow Flags (Investigate)
- [ ] Some tests SKIPPED (probably fine)
- [ ] Long execution time (>10 seconds - might be network)
- [ ] Filings found = 0 (might be invalid ticker)
- [ ] XBRL availability is False (some old filings don't have it)

### ❌ Red Flags (Problem)
- [ ] Any tests FAILED
- [ ] ERROR or CRITICAL in logs
- [ ] TickerNotFoundError for valid ticker (NVDA, AAPL, MSFT)
- [ ] Output directory not created
- [ ] Log file missing or empty

---

## 📋 Testing Checklist

Use this to verify Phase 1 & 2:

### Unit Tests
- [ ] Run: `pytest tests/test_sec_client.py -v`
- [ ] Result: 20 PASSED
- [ ] Time: < 1 second
- [ ] Output: Clean, no errors

### Real Data - NVDA
- [ ] Run: `python main.py NVDA`
- [ ] CIK: 0001045810 ✓
- [ ] Filings: 11 found
- [ ] Directory: `/home/monesh/sec_filing_parser/data/NVDA/` created
- [ ] Logs: File created with clean execution

### Real Data - Multi-Ticker
- [ ] Run: `python main.py NVDA AAPL MSFT`
- [ ] NVDA: Success, 11 filings
- [ ] AAPL: Success, 11 filings
- [ ] MSFT: Success, 11 filings

### Code Quality
- [ ] Read `config.py` - Makes sense
- [ ] Read `src/sec_client.py` - Clear logic
- [ ] Read `main.py` - Well-organized
- [ ] Check docstrings - All present

### Data Quality
- [ ] Log files are clean
- [ ] CIK values match SEC Edgar
- [ ] Filing dates are recent
- [ ] XBRL URLs are formatted correctly

---

## 🎯 Success Criteria

Phase 1 & 2 are successful if:

1. ✅ All 20 unit tests pass in < 1 second
2. ✅ Real SEC data retrieval works (11 filings for NVDA)
3. ✅ Output directories are created
4. ✅ Log files show clean execution
5. ✅ Code is well-documented
6. ✅ Error handling works (test with invalid ticker)
7. ✅ Multi-ticker support works

---

## 📍 Key File Locations for Manual Review

| Component | File Location | Key Method/Section |
|-----------|---------------|-------------------|
| Configuration | `/home/monesh/10Q_2/config.py` | SEC_EDGAR_SUBMISSIONS_API |
| SEC Client | `/home/monesh/10Q_2/src/sec_client.py` | `class SECClient` |
| Main Pipeline | `/home/monesh/10Q_2/main.py` | `def process_ticker()` |
| Unit Tests | `/home/monesh/10Q_2/tests/test_sec_client.py` | `TestGetCIKFromTicker` class |
| Output Logs | `~/sec_filing_parser/data/{TICKER}/logs/` | `processing_*.log` |
| Raw Files | `~/sec_filing_parser/data/{TICKER}/raw/` | (empty for now) |

---

## 📞 Troubleshooting

### "ModuleNotFoundError: No module named 'requests'"
```bash
pip install -r requirements.txt
```

### "TickerNotFoundError: Ticker 'NVDA' not found"
- Make sure ticker is correct spelling
- Check internet connection
- Verify SEC Edgar API is accessible

### "No such file or directory: /home/monesh/sec_filing_parser/..."
- Run `python main.py NVDA` first to create directories
- Check permissions: `ls -la ~/sec_filing_parser/`

### Log file shows "Failed to download"
- This is OK for Phase 2 - PDF download not fully implemented yet
- Phase 3 will implement proper PDF extraction

---

## 🎉 Next Steps After Manual Review

After successfully testing Phase 1 & 2:

1. Document any findings or improvements
2. Review code comments and docstrings
3. Verify all edge cases are handled
4. Ready to proceed with Phase 3: Data Extraction

Phase 3 will:
- Parse XBRL financial data
- Extract PDF data as fallback
- Assign confidence scores
- Reconcile multiple sources
