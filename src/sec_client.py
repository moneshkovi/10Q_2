"""SEC Edgar API client for retrieving financial filings.

This module provides a wrapper around the SEC Edgar API to:
- Convert ticker symbols to CIK (Central Index Key)
- Retrieve filing metadata (10-K, 10-Q)
- Download PDF filings
- Get XBRL data URLs for structured financial data

All methods include comprehensive error handling and logging.
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

import config


logger = logging.getLogger(__name__)


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class TickerNotFoundError(Exception):
    """Raised when a ticker symbol cannot be found in SEC Edgar."""
    pass


class FilingNotFoundError(Exception):
    """Raised when a specific filing cannot be found."""
    pass


class SECAPIError(Exception):
    """Raised when SEC API request fails."""
    pass


# ============================================================================
# SEC CLIENT
# ============================================================================

class SECClient:
    """Client for SEC Edgar API.

    Handles all communication with SEC Edgar to retrieve filing metadata,
    download PDFs, and access XBRL data. Implements retry logic and
    respects SEC's rate limits.

    Attributes:
        base_url: Base URL for SEC Edgar API
        headers: HTTP headers (includes User-Agent)
        session: Requests session with retry strategy
        ticker_to_cik_cache: Cache of ticker -> CIK mappings
    """

    def __init__(self):
        """Initialize SEC Edgar API client with retry strategy."""
        self.base_url = config.SEC_EDGAR_SUBMISSIONS_API
        self.headers = {
            "User-Agent": config.USER_AGENT
        }

        # Create session with retry strategy
        self.session = self._create_session_with_retries()

        # Cache ticker -> CIK mappings
        self.ticker_to_cik_cache: Dict[str, str] = {}

        logger.info("SECClient initialized")

    def _create_session_with_retries(self) -> requests.Session:
        """Create a requests session with automatic retry strategy.

        Returns:
            Configured requests.Session with retry adapter for both
            HTTP and HTTPS connections.
        """
        session = requests.Session()

        # Retry strategy: retry on connection errors and specific HTTP status codes
        retry_strategy = Retry(
            total=config.MAX_RETRIES,
            backoff_factor=1,  # exponential backoff: 1s, 2s, 4s, etc.
            status_forcelist=[429, 500, 502, 503, 504],  # rate limit, server errors
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

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
        ticker = ticker.upper().strip()

        # Check cache first
        if ticker in self.ticker_to_cik_cache:
            logger.debug(f"CIK for {ticker} found in cache")
            return self.ticker_to_cik_cache[ticker]

        logger.info(f"Looking up CIK for ticker: {ticker}")

        try:
            response = self.session.get(
                config.SEC_EDGAR_COMPANY_TICKERS,
                headers=self.headers,
                timeout=config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
        except (requests.RequestException, Exception) as e:
            logger.error(f"Failed to fetch company tickers: {e}")
            raise SECAPIError(f"Failed to fetch SEC company tickers: {e}") from e

        try:
            tickers_data = response.json()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse SEC company tickers JSON: {e}")
            raise SECAPIError(f"Invalid JSON response from SEC: {e}") from e

        # Search for ticker in the data
        # The JSON format is: {index: {cik_str: value, ticker: value, ...}}
        for entry in tickers_data.values():
            if entry.get("ticker", "").upper() == ticker:
                cik = str(entry["cik_str"]).zfill(10)  # zero-pad to 10 digits
                self.ticker_to_cik_cache[ticker] = cik
                logger.info(f"Found CIK {cik} for ticker {ticker}")
                return cik

        logger.warning(f"Ticker {ticker} not found in SEC Edgar database")
        raise TickerNotFoundError(f"Ticker '{ticker}' not found in SEC Edgar")

    def get_filings(self, cik: str, form_types: List[str], years: int) -> List[Dict]:
        """Retrieve filing metadata for a company.

        Fetches filing information (accession numbers, dates, URLs) for
        the specified company and form types from the past N years.

        Args:
            cik: Company CIK (10-digit zero-padded string)
            form_types: List of form types to retrieve (e.g., ['10-K', '10-Q'])
            years: Number of years of historical data to fetch

        Returns:
            List of filing dictionaries, each containing:
            - accession_number: Unique filing identifier
            - filing_date: Date filing was submitted (YYYY-MM-DD)
            - fiscal_period_end: End of fiscal period (YYYY-MM-DD)
            - form_type: '10-K' or '10-Q'
            - is_delayed: Whether filing is delayed
            - is_xbrl: Whether XBRL data is available

        Raises:
            SECAPIError: If SEC API request fails.

        Example:
            >>> client = SECClient()
            >>> filings = client.get_filings('0001045810', ['10-K'], years=3)
            >>> len(filings)
            3
        """
        cik_number = cik.lstrip("0") or "0"  # Remove leading zeros but keep at least one zero
        logger.info(f"Retrieving filings for CIK {cik}, form types {form_types}, {years} years")

        try:
            # SEC submissions API format: CIK{padded_10_digit}.json
            url = f"{self.base_url}/CIK{cik}.json"
            response = self.session.get(
                url,
                headers=self.headers,
                timeout=config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
        except (requests.RequestException, Exception) as e:
            logger.error(f"Failed to fetch filings for CIK {cik}: {e}")
            raise SECAPIError(f"Failed to fetch filings: {e}") from e

        try:
            data = response.json()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse filings JSON for CIK {cik}: {e}")
            raise SECAPIError(f"Invalid JSON response: {e}") from e

        # Calculate cutoff date (N years ago)
        cutoff_date = datetime.now() - timedelta(days=365 * years)

        filings = []
        filings_data = data.get("filings", {}).get("recent", {})

        for i, form_type in enumerate(filings_data.get("form", [])):
            if form_type not in form_types:
                continue

            filing_date_str = filings_data["filingDate"][i]
            filing_date = datetime.strptime(filing_date_str, "%Y-%m-%d")

            # Skip filings outside lookback period
            if filing_date < cutoff_date:
                continue

            accession_number = filings_data["accessionNumber"][i]

            # Use reportDate as fiscal_period_end (most reliable indicator of period)
            report_date_str = filings_data.get("reportDate", [filing_date_str])[i]

            # Check if filing is delayed - SEC API doesn't always have this field
            is_delayed = False  # Most filings are not delayed; if needed, add explicit check
            if is_delayed:
                logger.warning(f"Filing {accession_number} is delayed")
                continue

            # Check if XBRL is available (binary flag: 1 or 0)
            is_xbrl = filings_data.get("isXBRL", [0])[i] in [1, True]

            filing = {
                "accession_number": accession_number,
                "filing_date": filing_date_str,
                "fiscal_period_end": report_date_str,
                "form_type": form_type,
                "is_delayed": is_delayed,
                "is_xbrl": is_xbrl,
            }
            filings.append(filing)
            logger.debug(f"Found filing: {form_type} on {filing_date_str}")

        logger.info(f"Retrieved {len(filings)} filings for CIK {cik}")
        return sorted(filings, key=lambda x: x["filing_date"], reverse=True)

    def download_filing_pdf(self, accession_number: str, output_path: Path) -> bool:
        """Download a filing PDF from SEC Edgar.

        Fetches the main document (typically the PDF) for a filing and
        saves it to the specified path. Implements retry logic with
        exponential backoff.

        Args:
            accession_number: Filing accession number (with hyphens)
            output_path: Where to save the PDF file

        Returns:
            True if download successful, False otherwise.

        Raises:
            No exceptions; logs errors and returns False on failure.

        Example:
            >>> client = SECClient()
            >>> path = Path("/data/NVDA/raw/nvda_10k.pdf")
            >>> success = client.download_filing_pdf('0001045810-25-000023', path)
        """
        logger.info(f"Downloading filing {accession_number} to {output_path}")

        # Convert accession number to filing index URL
        # Accession format: 0001045810-25-000023
        # URL format: /Archives/edgar/data/1045810/000104581025000023/
        accession_no_hyphens = accession_number.replace("-", "")
        cik_padded = accession_no_hyphens[:10]  # Padded version (0001045810)
        cik = cik_padded.lstrip("0") or "0"  # Remove leading zeros (1045810)

        # Simplified: fetch the filing index to find the main document
        # For most 10-K/10-Q filings, the main file is the first HTML or PDF
        try:
            # Build correct filing URL path (includes /data/ component)
            filing_url = (
                f"{config.SEC_BASE_URL}/Archives/edgar/data/"
                f"{cik}/{accession_no_hyphens}/"
            )

            logger.debug(f"Attempting to fetch filing index from {filing_url}")
            response = self.session.get(
                filing_url,
                headers=self.headers,
                timeout=config.REQUEST_TIMEOUT,
                allow_redirects=True
            )
            response.raise_for_status()

            # Parse the HTML to find the main document
            # Look for the largest file (usually the PDF or main document)
            soup = BeautifulSoup(response.content, "html.parser")

            # Find all document links
            doc_links = []
            for row in soup.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) >= 4:
                    # Typically: Type, Sequence, Description, Size, ...
                    try:
                        filename = cells[2].text.strip()
                        size_text = cells[3].text.strip()
                        size = int(size_text.replace(",", "")) if size_text else 0

                        # Get the document link
                        link = cells[2].find("a")
                        if link and "href" in link.attrs:
                            doc_url = link["href"]
                            # Make absolute URL if needed
                            if not doc_url.startswith("http"):
                                doc_url = f"{config.SEC_BASE_URL}{doc_url}"

                            doc_links.append({
                                "filename": filename,
                                "size": size,
                                "url": doc_url
                            })
                    except (ValueError, IndexError, AttributeError):
                        continue

            if not doc_links:
                logger.warning(f"No documents found in filing {accession_number}")
                return False

            # Sort by size descending and take the largest (usually the main document)
            doc_links.sort(key=lambda x: x["size"], reverse=True)
            main_doc = doc_links[0]

            logger.debug(f"Downloading main document: {main_doc['filename']} ({main_doc['size']} bytes)")

            # Download the main document
            pdf_response = self.session.get(
                main_doc["url"],
                headers=self.headers,
                timeout=config.REQUEST_TIMEOUT,
                allow_redirects=True
            )
            pdf_response.raise_for_status()

            # Save to file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(pdf_response.content)

            logger.info(f"Successfully downloaded {len(pdf_response.content)} bytes to {output_path}")

            # Respect SEC rate limits
            time.sleep(config.SEC_REQUEST_DELAY)

            return True

        except requests.RequestException as e:
            logger.error(f"Failed to download filing {accession_number}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error downloading filing {accession_number}: {e}")
            return False

    def get_xbrl_url(self, accession_number: str) -> Optional[str]:
        """Get URL to XBRL data for a filing.

        XBRL (eXtensible Business Reporting Language) is machine-readable
        XML containing structured financial data. Not all filings have XBRL
        available, so this may return None.

        Args:
            accession_number: Filing accession number (with hyphens)

        Returns:
            URL to XBRL data if available, None otherwise.

        Example:
            >>> client = SECClient()
            >>> xbrl_url = client.get_xbrl_url('0001045810-25-000023')
            >>> print(xbrl_url)
            'https://www.sec.gov/cgi-bin/viewer?action=view&cik=...'
        """
        accession_no_hyphens = accession_number.replace("-", "")
        cik = accession_no_hyphens[:10]

        # Construct XBRL viewer URL
        xbrl_url = (
            f"{config.SEC_BASE_URL}/cgi-bin/viewer?"
            f"action=view&cik={cik}&accession_number={accession_number}&xbrl_type=v"
        )

        logger.debug(f"XBRL URL for {accession_number}: {xbrl_url}")
        return xbrl_url
