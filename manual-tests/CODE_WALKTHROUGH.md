# Code Walkthrough: Understanding Phase 1 & 2 Implementation

**For: Manual code review and understanding what each file does**

---

## 📂 File-by-File Breakdown

### 1. `config.py` - Configuration & Constants

**Purpose:** Centralize all settings so they can be changed easily

**Key Sections:**

#### Paths
```python
BASE_DIR = Path.home() / "sec_filing_parser"
DATA_DIR = BASE_DIR / "data"

# Creates directories like:
# ~/sec_filing_parser/data/NVDA/
#   ├── raw/
#   ├── parsed/
#   └── logs/
```

#### SEC Edgar API URLs
```python
SEC_BASE_URL = "https://www.sec.gov"
SEC_EDGAR_SUBMISSIONS_API = "https://data.sec.gov/submissions"
SEC_EDGAR_COMPANY_TICKERS = "https://www.sec.gov/files/company_tickers.json"
```

**What they do:**
- `SEC_EDGAR_SUBMISSIONS_API` - Returns filing metadata (10-K, 10-Q, etc.)
- `SEC_EDGAR_COMPANY_TICKERS` - JSON file with all tickers and their CIKs

#### Filtering Parameters
```python
LOOKBACK_YEARS = 3          # Retrieve last 3 years of filings
FILING_TYPES = ["10-K", "10-Q"]  # Annual and quarterly filings
MAX_RETRIES = 3             # Retry failed requests up to 3 times
SEC_REQUEST_DELAY = 0.1     # Wait 100ms between requests (respect rate limits)
```

**What they do:**
- Control which filings are retrieved
- Control error recovery behavior

#### User Agent
```python
USER_AGENT = "SECFilingParser/1.0 (educational; monesh@example.com)"
```

**Why it matters:** SEC requires a User-Agent to identify your application

---

### 2. `src/sec_client.py` - SEC Edgar API Client

**Purpose:** Handle all communication with SEC Edgar API

#### Class Definition & Initialization

```python
class SECClient:
    def __init__(self):
        self.base_url = config.SEC_EDGAR_SUBMISSIONS_API
        self.session = self._create_session_with_retries()
        self.ticker_to_cik_cache = {}
```

**What happens:**
- `self.session` - HTTP connection with automatic retry logic
- `self.ticker_to_cik_cache` - Dictionary to store ticker → CIK mappings

#### Method 1: `get_cik_from_ticker(ticker)`

**What it does:**
1. Check cache first (fast lookup)
2. If not cached, fetch SEC company tickers JSON
3. Search for matching ticker
4. Return CIK (zero-padded to 10 digits)

**API Call:**
```
GET https://www.sec.gov/files/company_tickers.json
```

**Response Format:**
```json
{
  "0": {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA CORP"},
  "1": {"cik_str": 320193, "ticker": "AAPL", "title": "APPLE INC"},
  ...
}
```

**Output:**
```python
# Input: "NVDA"
# Output: "0001045810"  (zero-padded to 10 digits)
```

**Error Handling:**
```python
except (requests.RequestException, Exception) as e:
    raise SECAPIError(f"Failed to fetch SEC company tickers: {e}")
```

#### Method 2: `get_filings(cik, form_types, years)`

**What it does:**
1. Query SEC submissions API for given CIK
2. Parse response to extract filings metadata
3. Filter by form type (10-K, 10-Q)
4. Filter by year (lookback period)
5. Sort by date (newest first)
6. Return list of filing dictionaries

**API Call:**
```
GET https://data.sec.gov/submissions/CIK{padded_cik}.json
```

**Response Structure:**
```json
{
  "filings": {
    "recent": {
      "accessionNumber": ["0001045810-25-000230", ...],
      "filingDate": ["2025-11-19", ...],
      "reportDate": ["2025-10-26", ...],
      "form": ["10-Q", "10-K", ...],
      "isXBRL": [1, 0, ...]
    }
  }
}
```

**Processing Steps:**
```python
# Step 1: Calculate date cutoff (3 years ago)
cutoff_date = datetime.now() - timedelta(days=365 * years)
# cutoff_date = Feb 23, 2023 (for 3 years from Feb 23, 2026)

# Step 2: Loop through filings
for i, form_type in enumerate(filings_data.get("form", [])):
    if form_type not in form_types:  # Skip if not 10-K or 10-Q
        continue

    filing_date = datetime.strptime(filings_data["filingDate"][i], "%Y-%m-%d")

    if filing_date < cutoff_date:  # Skip if older than 3 years
        continue

    # Step 3: Extract metadata
    filing = {
        "accession_number": filings_data["accessionNumber"][i],
        "filing_date": filings_data["filingDate"][i],
        "fiscal_period_end": filings_data["reportDate"][i],
        "form_type": form_type,
        "is_xbrl": filings_data.get("isXBRL", [0])[i] == 1
    }
    filings.append(filing)

# Step 4: Sort by date (newest first)
return sorted(filings, key=lambda x: x["filing_date"], reverse=True)
```

**Output Example:**
```python
[
  {
    "accession_number": "0001045810-25-000230",
    "filing_date": "2025-11-19",
    "fiscal_period_end": "2025-10-26",
    "form_type": "10-Q",
    "is_xbrl": True
  },
  # ... more filings, sorted newest first
]
```

#### Method 3: `get_xbrl_url(accession_number)`

**What it does:**
Constructs URL to SEC Edgar XBRL viewer for a filing

**How it works:**
```python
xbrl_url = (
    f"https://www.sec.gov/cgi-bin/viewer?"
    f"action=view&cik={cik}&accession_number={accession_number}&xbrl_type=v"
)
```

**Example Output:**
```
https://www.sec.gov/cgi-bin/viewer?action=view&cik=1045810&accession_number=0001045810-25-000230&xbrl_type=v
```

**Purpose:** This URL links to machine-readable financial data (Phase 3 will parse this)

#### Error Handling

**Three Custom Exceptions:**

```python
class TickerNotFoundError(Exception):
    """Raised when ticker not found in SEC Edgar"""
    pass

class SECAPIError(Exception):
    """Raised when SEC API request fails"""
    pass

class FilingNotFoundError(Exception):
    """Raised when specific filing not found"""
    pass
```

**Example Usage:**
```python
try:
    cik = client.get_cik_from_ticker("INVALID")
except TickerNotFoundError:
    print("Ticker doesn't exist")
except SECAPIError:
    print("API error - network problem")
```

---

### 3. `main.py` - Orchestration & CLI

**Purpose:** Tie everything together and provide command-line interface

#### Logging Setup

```python
def setup_logging(ticker: str) -> logging.Logger:
    log_dir = config.DATA_DIR / ticker.upper() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # File logging (detailed)
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)

    # Console logging (summary)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
```

**Result:**
- Console shows important messages
- File has detailed debug logs

#### Main Pipeline: `process_ticker(ticker)`

**Phase 1: Initialize**
```python
client = SECClient()  # Create API client
```

**Phase 2: Validate Ticker**
```python
cik = client.get_cik_from_ticker(ticker)
# Input: "NVDA"
# Output: "0001045810"
# Error: TickerNotFoundError
```

**Phase 3: Create Directories**
```python
raw_dir = data_dir / "raw"       # For PDFs
parsed_dir = data_dir / "parsed"  # For XMLs
logs_dir = data_dir / "logs"      # For logs

for directory in [raw_dir, parsed_dir, logs_dir]:
    directory.mkdir(parents=True, exist_ok=True)
```

**Phase 4: Get Filing Metadata**
```python
filings = client.get_filings(
    cik=cik,
    form_types=["10-K", "10-Q"],
    years=3
)
# Output: List of 11 filings with metadata
```

**Phase 5: Identify XBRL Data**
```python
for filing in filings:
    xbrl_url = client.get_xbrl_url(filing["accession_number"])
    filing["xbrl_url"] = xbrl_url
    # Now each filing has a link to its XBRL data
```

**Phase 6: Results Summary**
```python
result = {
    "success": True,
    "ticker": "NVDA",
    "cik": "0001045810",
    "filings_found": 11,
    "output_dir": "~/sec_filing_parser/data/NVDA"
}
```

#### Error Handling in Main

```python
try:
    cik = client.get_cik_from_ticker(ticker)
except TickerNotFoundError as e:
    logger.error(f"Ticker validation failed: {e}")
    result["errors"].append(str(e))
    return result  # Stop processing
```

#### CLI Entry Point: `main()`

```python
def main():
    # Get ticker(s) from command line
    tickers = sys.argv[1:]  # ["NVDA", "AAPL", "MSFT"]

    # Process each ticker
    for ticker in tickers:
        result = process_ticker(ticker)
        all_results[ticker.upper()] = result

    # Print summary
    print(f"Tickers processed: {successful}/{len(tickers)}")
    print(f"Total filings found: {total_filings}")
```

---

## 🔄 Complete Data Flow

### Example: `python main.py NVDA`

```
┌─ Input: "NVDA"
│
├─ main.py:main()
│  └─ process_ticker("NVDA")
│
├─ Step 1: Initialize SEC Client
│  └─ SECClient() creates HTTP session with retries
│
├─ Step 2: Validate Ticker
│  └─ SECClient.get_cik_from_ticker("NVDA")
│     ├─ Query: https://www.sec.gov/files/company_tickers.json
│     ├─ Search for "NVDA" in response
│     └─ Return: "0001045810"
│
├─ Step 3: Create Directories
│  └─ ~/sec_filing_parser/data/NVDA/{raw,parsed,logs}/
│
├─ Step 4: Get Filing Metadata
│  └─ SECClient.get_filings("0001045810", ["10-K", "10-Q"], 3)
│     ├─ Query: https://data.sec.gov/submissions/CIK0001045810.json
│     ├─ Parse: Extract form types, dates, XBRL availability
│     ├─ Filter: Keep only 10-K, 10-Q from past 3 years
│     └─ Return: List of 11 filings with metadata
│
├─ Step 5: Generate XBRL URLs
│  └─ For each filing:
│     └─ SECClient.get_xbrl_url(accession_number)
│        └─ Return: SEC Edgar viewer URL
│
├─ Step 6: Create Logs
│  └─ ~/sec_filing_parser/data/NVDA/logs/processing_*.log
│     (Contains all steps above with timestamps)
│
└─ Output: Results Summary
   ├─ Success: True
   ├─ Ticker: NVDA
   ├─ CIK: 0001045810
   ├─ Filings Found: 11
   └─ Output Dir: ~/sec_filing_parser/data/NVDA/
```

---

## 🧪 Unit Tests in `tests/test_sec_client.py`

### Purpose
Test code logic **without** calling real SEC API (faster, cleaner)

### Mocking Strategy

```python
# Real code calls SEC API:
response = self.session.get("https://www.sec.gov/files/company_tickers.json")

# In tests, we mock this:
with patch.object(client.session, "get") as mock_get:
    mock_response = Mock()
    mock_response.json.return_value = {
        "0": {"cik_str": 1045810, "ticker": "NVDA", ...}
    }
    mock_get.return_value = mock_response

    # Now when code calls session.get(), it returns our fake data
    cik = client.get_cik_from_ticker("NVDA")
    assert cik == "0001045810"
```

### Test Categories

**1. Valid Input Tests**
```python
def test_valid_ticker_nvda(self):
    # Verify: Valid ticker → correct CIK
    # Expected: cik == "0001045810"
```

**2. Edge Case Tests**
```python
def test_valid_ticker_lowercase(self):
    # Verify: Lowercase "nvda" → "NVDA" → CIK
    # Expected: Works correctly

def test_valid_ticker_with_whitespace(self):
    # Verify: "  NVDA  " → "NVDA" → CIK
    # Expected: Whitespace stripped correctly
```

**3. Error Handling Tests**
```python
def test_invalid_ticker(self):
    # Verify: Invalid ticker raises TickerNotFoundError
    # Expected: Exception raised

def test_api_error(self):
    # Verify: Network error raises SECAPIError
    # Expected: Exception raised
```

**4. Feature Tests**
```python
def test_cik_caching(self):
    # Verify: Second lookup uses cache (no API call)
    # Expected: API called once, second call uses cache

def test_get_filings_filters_delayed(self):
    # Verify: Delayed filings are handled correctly
    # Expected: Only non-delayed filings returned
```

---

## 📊 Data Structures

### Filing Dictionary
```python
{
    "accession_number": "0001045810-25-000230",
    "filing_date": "2025-11-19",
    "fiscal_period_end": "2025-10-26",
    "form_type": "10-Q",
    "is_xbrl": True,
    "xbrl_url": "https://www.sec.gov/cgi-bin/viewer?..."
}
```

### Result Dictionary
```python
{
    "success": True,
    "ticker": "NVDA",
    "cik": "0001045810",
    "filings_found": 11,
    "pdfs_downloaded": 0,
    "output_dir": "~/sec_filing_parser/data/NVDA",
    "errors": []
}
```

---

## 🔍 Code Quality Features

### 1. Docstrings (Google Format)
```python
def get_cik_from_ticker(self, ticker: str) -> str:
    """Convert NYSE ticker to CIK (Central Index Key).

    Fetches the company_tickers.json file from SEC and looks up the
    CIK corresponding to the given ticker. Results are cached for
    performance.

    Args:
        ticker: Stock ticker symbol (e.g., 'NVDA', 'AAPL')

    Returns:
        CIK as zero-padded 10-digit string (e.g., '0001045810')

    Raises:
        TickerNotFoundError: If ticker not found in SEC Edgar database.
        SECAPIError: If SEC API request fails.

    Example:
        >>> client = SECClient()
        >>> cik = client.get_cik_from_ticker('NVDA')
        >>> print(cik)
        '0001045810'
    """
```

### 2. Type Hints
```python
def get_filings(
    self,
    cik: str,
    form_types: List[str],
    years: int
) -> List[Dict]:
    """Type hints make code self-documenting"""
```

### 3. Comprehensive Logging
```python
logger.info(f"Converting ticker '{ticker}' to CIK...")
logger.info(f"✓ Found CIK: {cik} for ticker {ticker}")
logger.warning(f"Filing {accession_number} is delayed")
logger.error(f"Failed to fetch filings: {e}")
logger.debug(f"CIK for {ticker} found in cache")
```

### 4. Error Handling
```python
try:
    # Attempt operation
except SpecificException as e:
    # Handle specific error
    logger.error(f"Specific error: {e}")
    raise CustomError(f"Description: {e}") from e
except Exception as e:
    # Handle unexpected errors
    logger.error(f"Unexpected error: {e}", exc_info=True)
    return False
```

---

## ✅ Code Review Checklist

When reviewing Phase 1 & 2, check:

- [ ] `config.py` - All constants properly named
- [ ] `sec_client.py` - Methods have clear responsibility
- [ ] `sec_client.py` - Error handling is comprehensive
- [ ] `main.py` - Pipeline steps are logical
- [ ] `main.py` - Logging is informative
- [ ] All docstrings are present and accurate
- [ ] Type hints are complete
- [ ] No hardcoded values (all in config)
- [ ] No sensitive data in logs
- [ ] Tests cover happy path and error cases

---

## 🎯 Key Takeaways for Manual Review

1. **Configuration is Centralized** - Change settings in `config.py`, not in code
2. **API Calls are Wrapped** - `SECClient` handles all SEC Edgar communication
3. **Error Handling is Explicit** - Custom exceptions for different error types
4. **Logging is Comprehensive** - Both console and file logs for debugging
5. **Code is Well-Documented** - Docstrings and type hints throughout
6. **Tests Mock External APIs** - Fast, reliable testing without network calls

---

## 📈 What Phase 3 Will Use

Phase 3 (Data Extraction) will:
1. Use filing metadata from Phase 2 (accession numbers, XBRL URLs)
2. Use XBRL URLs to fetch machine-readable financial data
3. Parse XML to extract: revenue, net income, assets, liabilities, etc.
4. Handle errors when data is missing or malformed
5. Assign confidence scores to extracted data

The foundation in Phase 1 & 2 makes Phase 3 implementation straightforward!
