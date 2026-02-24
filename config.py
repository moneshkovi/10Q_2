"""Configuration for SEC Filing Parser.

This module defines all constants, paths, and settings used throughout
the application. Centralize configuration here to make adjustments easy.
"""

from pathlib import Path
from typing import List

# ============================================================================
# DIRECTORIES & PATHS
# ============================================================================

# Base directory for data storage
BASE_DIR = Path.home() / "sec_filing_parser"

# Data directory where ticker-specific data is stored
DATA_DIR = BASE_DIR / "data"

# Logs directory
LOGS_DIR = BASE_DIR / "logs"

# Create directories if they don't exist
BASE_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# SEC EDGAR API CONFIGURATION
# ============================================================================

# SEC Edgar base URLs
SEC_BASE_URL = "https://www.sec.gov"
SEC_EDGAR_SUBMISSIONS_API = "https://data.sec.gov/submissions"
SEC_EDGAR_COMPANY_TICKERS = "https://www.sec.gov/files/company_tickers.json"

# User agent string (SEC requires this to identify your application)
# Update this to identify your application
USER_AGENT = "SECFilingParser/1.0 (research; monesh.kovi@gmail.com)"

# ============================================================================
# FILING CONFIGURATION
# ============================================================================

# Number of years of historical data to fetch
LOOKBACK_YEARS: int = 3

# Filing types to retrieve
FILING_TYPES: List[str] = ["10-K", "10-Q"]

# ============================================================================
# NETWORK & RETRY CONFIGURATION
# ============================================================================

# Maximum number of retry attempts for failed requests
MAX_RETRIES: int = 3

# Delay between retry attempts (seconds)
RETRY_DELAY: int = 5

# Request timeout (seconds)
REQUEST_TIMEOUT: int = 30

# SEC Edgar rate limit: ~10 requests per second
# We'll be conservative and wait 100ms between requests
SEC_REQUEST_DELAY: float = 0.1

# ============================================================================
# DATA QUALITY & VALIDATION
# ============================================================================

# Minimum confidence threshold for flagging items
# Items below this are marked for manual review
MIN_CONFIDENCE_THRESHOLD: float = 0.95

# Cache age: re-fetch if local data older than this many days
# Set to 0 to disable caching (always re-fetch)
CACHE_AGE_DAYS: int = 30

# Reconciliation tolerance: differences below this % are accepted automatically
# Differences above this are flagged for manual review
RECONCILIATION_TOLERANCE_PCT: float = 5.0

# ============================================================================
# PARSING CONFIGURATION
# ============================================================================

# XBRL namespace for US GAAP (standard for US public companies)
XBRL_NAMESPACE_GAAP = "http://xbrl.us/us-gaap/2023-01-31"
XBRL_NAMESPACE_DEI = "http://xbrl.sec.gov/dei/2023-01-31"

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL: str = "INFO"

# Log format
LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# ============================================================================
# OUTPUT CONFIGURATION
# ============================================================================

# Pretty-print XML output (indent & format for readability)
XML_PRETTY_PRINT: bool = True

# XML indentation level (spaces)
XML_INDENT: int = 2
