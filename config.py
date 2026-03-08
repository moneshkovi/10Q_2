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
LOOKBACK_YEARS: int = 5

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

# ============================================================================
# DCF MODEL CONFIGURATION (Phase 7)
# ============================================================================

# Forecast horizon (years)
DCF_FORECAST_YEARS: int = 5

# Risk-free rate (10-year US Treasury yield approximation)
DCF_RISK_FREE_RATE: float = 0.045  # 4.5%

# Equity risk premium (long-term average)
DCF_EQUITY_RISK_PREMIUM: float = 0.055  # 5.5% (Damodaran estimate)

# Terminal growth rate (default, typically GDP growth)
DCF_TERMINAL_GROWTH_RATE: float = 0.025  # 2.5%

# Default EV/EBITDA exit multiple (sector-adjusted at runtime)
DCF_DEFAULT_EXIT_MULTIPLE: float = 12.0

# Industry beta lookup (Damodaran unlevered betas, re-levered for typical structures)
# Source: Damodaran Online - Industry Betas (updated annually)
DCF_INDUSTRY_BETAS: dict = {
    # Technology - Hardware/Software/Semiconductors
    "NVDA": 1.65, "AMD": 1.70, "INTC": 1.10, "AVGO": 1.20,
    "AAPL": 1.20, "MSFT": 0.95, "GOOG": 1.05, "GOOGL": 1.05,
    "META": 1.30, "AMZN": 1.15, "TSLA": 1.95, "NFLX": 1.40,
    "CRM": 1.25, "ORCL": 1.00, "ADBE": 1.15, "QCOM": 1.35,

    # Financial Services
    "BLK": 1.20, "JPM": 1.10, "GS": 1.35, "MS": 1.30,
    "BAC": 1.40, "WFC": 1.15, "C": 1.45, "SCHW": 1.30,
    "V": 0.95, "MA": 1.00,

    # Healthcare / Pharma
    "JNJ": 0.60, "PFE": 0.70, "UNH": 0.75, "LLY": 0.80,
    "ABBV": 0.75, "MRK": 0.65, "TMO": 0.90, "ABT": 0.85,

    # Consumer / Retail
    "KO": 0.60, "PEP": 0.60, "PG": 0.45, "WMT": 0.50,
    "COST": 0.70, "MCD": 0.65, "NKE": 0.85, "SBUX": 0.90,

    # Energy
    "XOM": 0.95, "CVX": 1.00, "COP": 1.20,

    # Industrials
    "BA": 1.40, "CAT": 1.05, "GE": 1.15, "HON": 1.00,
    "UPS": 0.95, "RTX": 0.85,

    # Default for unknown tickers
    "DEFAULT": 1.00,
}

# Sector EV/EBITDA exit multiples (for terminal value)
DCF_SECTOR_MULTIPLES: dict = {
    "technology": 18.0,
    "semiconductors": 16.0,
    "software": 20.0,
    "financial_services": 10.0,
    "asset_management": 12.0,
    "healthcare": 14.0,
    "pharma": 13.0,
    "consumer_staples": 15.0,
    "consumer_discretionary": 14.0,
    "energy": 6.0,
    "industrials": 12.0,
    "utilities": 10.0,
    "telecom": 8.0,
    "real_estate": 15.0,
    "DEFAULT": 12.0,
}

# Revenue growth tapering (year-by-year multiplier on historical CAGR)
# Year 1: 90% of CAGR, Year 2: 75%, etc. → converging to terminal rate
DCF_GROWTH_TAPER: List[float] = [0.90, 0.75, 0.60, 0.45, 0.35]

# Sensitivity analysis ranges
DCF_SENSITIVITY_WACC_RANGE: List[float] = [-0.02, -0.01, 0.0, 0.01, 0.02]
DCF_SENSITIVITY_GROWTH_RANGE: List[float] = [-0.01, -0.005, 0.0, 0.005, 0.01]

# Scenario multipliers (Bull / Base / Bear)
DCF_SCENARIO_BULL_MULTIPLIER: float = 1.20   # 20% above base growth
DCF_SCENARIO_BEAR_MULTIPLIER: float = 0.70   # 30% below base growth
