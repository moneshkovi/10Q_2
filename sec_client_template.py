# sec_client.py - SEC Edgar API Wrapper (Starter Template)
# This is the first module to implement. It handles all communication with SEC.gov

"""
SEC Edgar API Client

Responsibilities:
1. Convert NYSE ticker → CIK (Central Index Key)
2. Fetch filing metadata (dates, accession numbers, URLs)
3. Download PDF files from SEC Edgar
4. Retrieve XBRL data (if available)
5. Handle errors gracefully (missing tickers, delayed filings, etc.)

No authentication required; SEC provides free API access.
Rate limits: Reasonable (~10 requests/sec)
"""

import requests
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

SEC_BASE_URL = "https://www.sec.gov"
SEC_DATA_API = "https://data.sec.gov"
SEC_CIK_LOOKUP_URL = "https://www.sec.gov/cgi-bin/browse-edgar"

USER_AGENT = "Mozilla/5.0 (MyFirm SEC Filing Parser v1.0; contact@example.com)"

# Rate limiting (SEC requests we don't hammer them)
REQUEST_DELAY = 0.1  # seconds between requests
RETRY_MAX = 3
RETRY_DELAY = 5  # seconds


# ============================================================================
# EXCEPTIONS
# ============================================================================

class TickerNotFoundError(Exception):
    """Raised when ticker doesn't exist or can't be mapped to CIK"""
    pass

class CIKNotFoundError(Exception):
    """Raised when CIK doesn't return company data"""
    pass

class FilingNotFoundError(Exception):
    """Raised when filing doesn't exist"""
    pass

class SECAPIError(Exception):
    """Raised on SEC API errors"""
    pass


# ============================================================================
# MAIN CLIENT
# ============================================================================

class SECClient:
    """
    Wrapper around SEC Edgar API.
    
    Usage:
        client = SECClient()
        cik = client.get_cik_from_ticker("NVDA")
        filings = client.get_filings(cik, ["10-K", "10-Q"], years=3)
        client.download_filing_pdf(filings[0]["accession_number"], Path("./nvda.pdf"))
    """
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize SEC client.
        
        Args:
            cache_dir: Optional directory to cache CIK lookups (speeds up repeat calls)
        """
        self.cache_dir = cache_dir or Path.home() / ".sec_cache"
        self.cache_dir.mkdir(exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self._cik_cache = {}  # In-memory cache for this session
    
    # ========================================================================
    # TICKER → CIK MAPPING
    # ========================================================================
    
    def get_cik_from_ticker(self, ticker: str) -> str:
        """
        Convert NYSE ticker symbol to CIK (Central Index Key).
        
        Args:
            ticker: Stock ticker (e.g., "NVDA", "AAPL")
        
        Returns:
            CIK as zero-padded 10-digit string (e.g., "0001045810")
        
        Raises:
            TickerNotFoundError: If ticker not found or not NYSE
        
        Logic:
            1. Check in-memory cache
            2. Query SEC EDGAR API
            3. Validate result
            4. Cache for future use
        
        Note:
            SEC requires User-Agent header and rate limiting.
            Will retry on temporary failures.
        """
        
        # Step 1: Check cache (in-memory)
        if ticker in self._cik_cache:
            logger.debug(f"CIK for {ticker} found in cache")
            return self._cik_cache[ticker]
        
        # Step 2: Query SEC API
        logger.info(f"Looking up CIK for ticker: {ticker}")
        
        try:
            # Use SEC submissions API (most reliable)
            url = f"{SEC_DATA_API}/submissions/CIK{ticker.upper()}.json"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            cik = data["cik_str"]  # e.g., 1045810
            
            # Validate: Make sure it's properly formatted
            if not cik or not str(cik).isdigit():
                raise TickerNotFoundError(f"Invalid CIK for ticker {ticker}: {cik}")
            
            # Zero-pad to 10 digits
            cik_padded = str(cik).zfill(10)
            
            logger.info(f"{ticker} → CIK {cik_padded}")
            
            # Step 3: Cache it
            self._cik_cache[ticker] = cik_padded
            
            return cik_padded
        
        except requests.exceptions.RequestException as e:
            logger.error(f"SEC API error looking up {ticker}: {e}")
            raise SECAPIError(f"Failed to lookup CIK for {ticker}: {e}")
        except (KeyError, json.JSONDecodeError) as e:
            logger.error(f"Invalid response for {ticker}: {e}")
            raise TickerNotFoundError(f"Ticker {ticker} not found in SEC database")
    
    # ========================================================================
    # FILING METADATA
    # ========================================================================
    
    def get_filings(self, cik: str, form_types: List[str], 
                   years: int = 3) -> List[Dict]:
        """
        Fetch filing metadata for a company.
        
        Args:
            cik: Central Index Key (e.g., "0001045810")
            form_types: List of form types to fetch (e.g., ["10-K", "10-Q"])
            years: How many years back to go
        
        Returns:
            List of filing dicts:
            [
                {
                    "accession_number": "0001045810-25-000023",
                    "filing_date": "2025-01-26",
                    "form_type": "10-K",
                    "fiscal_period_end": "2025-01-26",
                    "fiscal_year": 2025,
                    "status": "FILED",  # or "DELAYED"
                    "filing_url": "https://www.sec.gov/cgi-bin/viewer?...",
                    "xbrl_url": "https://...",  # or None if not available
                    "size_bytes": 48800000
                },
                ...
            ]
        
        Raises:
            CIKNotFoundError: If CIK doesn't exist
        
        Logic:
            1. Query SEC submissions API for company
            2. Filter by form type
            3. Filter by date (past N years)
            4. Extract metadata for each filing
            5. Return sorted by date (newest first)
        """
        
        logger.info(f"Fetching filings for CIK {cik}: {form_types} (past {years} years)")
        
        try:
            # Fetch company's filing history
            url = f"{SEC_DATA_API}/submissions/CIK{cik}.json"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            company_data = response.json()
            
            # Validate company exists
            if "filings" not in company_data:
                raise CIKNotFoundError(f"Invalid CIK: {cik}")
            
            company_name = company_data.get("name", "Unknown")
            exchange = company_data.get("entityType", "Unknown")
            logger.info(f"Company: {company_name} ({exchange})")
            
            # Extract all filings
            all_filings = company_data["filings"]["recent"]
            
            # Calculate cutoff date (N years ago)
            cutoff_date = datetime.now() - timedelta(days=365 * years)
            
            # Filter filings
            results = []
            
            for i, filing in enumerate(all_filings["accessionNumber"]):
                form = all_filings["form"][i]
                filing_date_str = all_filings["filingDate"][i]
                fiscal_end_str = all_filings["reportDate"][i]
                
                # Filter by form type
                if form not in form_types:
                    continue
                
                # Filter by date
                try:
                    filing_date = datetime.strptime(filing_date_str, "%Y-%m-%d")
                    if filing_date < cutoff_date:
                        continue
                except ValueError:
                    continue
                
                # Extract metadata
                accession = filing.replace("-", "")  # Remove hyphens for URL
                accession_display = filing  # Keep hyphens for display
                
                result = {
                    "accession_number": accession_display,
                    "filing_date": filing_date_str,
                    "form_type": form,
                    "fiscal_period_end": fiscal_end_str,
                    "fiscal_year": int(fiscal_end_str[:4]),
                    "status": "FILED",  # TODO: Check for delayed flag
                    "filing_url": f"https://www.sec.gov/cgi-bin/viewer?action=view&cik={cik}&accession_number={accession}&xbrl_type=v",
                    "xbrl_available": True,  # TODO: Verify XBRL existence
                    "size_bytes": all_filings.get("sizeInBytes", [None])[i]
                }
                
                results.append(result)
            
            # Sort by date (newest first)
            results.sort(key=lambda x: x["filing_date"], reverse=True)
            
            logger.info(f"Found {len(results)} matching filings")
            
            return results
        
        except requests.exceptions.RequestException as e:
            logger.error(f"SEC API error: {e}")
            raise SECAPIError(f"Failed to fetch filings: {e}")
        except (KeyError, IndexError, ValueError) as e:
            logger.error(f"Error parsing response: {e}")
            raise SECAPIError(f"Invalid response format: {e}")
    
    # ========================================================================
    # FILE DOWNLOADS
    # ========================================================================
    
    def download_filing_pdf(self, accession_number: str, 
                           output_path: Path) -> bool:
        """
        Download 10-K/10-Q PDF from SEC Edgar.
        
        Args:
            accession_number: Unique filing ID (e.g., "0001045810-25-000023")
            output_path: Where to save the PDF
        
        Returns:
            True if successful, False if not found
        
        Logic:
            1. Construct URL to filing document
            2. Download with retries
            3. Validate it's a real PDF
            4. Save to disk
            5. Log success/failure
        
        Example:
            >>> client.download_filing_pdf("0001045810-25-000023", Path("./nvda.pdf"))
            True
        """
        
        logger.info(f"Downloading filing {accession_number}")
        
        # Construct URL
        # SEC structure: /Archives/edgar/data/1045810/000104581025000023/
        accession_clean = accession_number.replace("-", "")
        cik_from_accession = accession_clean[:10]
        
        # Try multiple possible URLs (SEC filing structure varies)
        possible_urls = [
            f"{SEC_BASE_URL}/cgi-bin/viewer?action=view&cik={cik_from_accession}&accession_number={accession_number}&xbrl_type=v",
            f"{SEC_BASE_URL}/Archives/edgar/data/{int(cik_from_accession)}/{accession_clean}/",
        ]
        
        # Attempt download with retries
        for attempt in range(RETRY_MAX):
            try:
                # Most recent 10-Ks use standardized naming
                # Try the most common pattern first
                
                url = f"{SEC_BASE_URL}/Archives/edgar/data/{int(cik_from_accession)}/{accession_clean}/"
                
                # Fetch directory listing
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                
                # Find the main 10-K/10-Q file (usually ends with .htm or .html)
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Look for the main document link
                links = soup.find_all("a")
                pdf_or_htm = None
                
                for link in links:
                    href = link.get("href", "")
                    # Prefer .htm files (usually contain full document)
                    if ".htm" in href and not "0001193125" in href:
                        pdf_or_htm = href
                        break
                
                if not pdf_or_htm:
                    logger.warning(f"Could not find document link in {url}")
                    continue
                
                # Download the actual document
                doc_url = url + pdf_or_htm if not pdf_or_htm.startswith("http") else pdf_or_htm
                
                doc_response = self.session.get(doc_url, timeout=10)
                doc_response.raise_for_status()
                
                # Save to disk
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(doc_response.content)
                
                logger.info(f"Downloaded {len(doc_response.content)} bytes to {output_path}")
                
                # Add a small delay to respect SEC rate limits
                time.sleep(REQUEST_DELAY)
                
                return True
            
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < RETRY_MAX - 1:
                    time.sleep(RETRY_DELAY)
        
        logger.error(f"Failed to download {accession_number} after {RETRY_MAX} attempts")
        return False
    
    # ========================================================================
    # XBRL DATA
    # ========================================================================
    
    def get_xbrl_data_url(self, accession_number: str) -> Optional[str]:
        """
        Get URL to XBRL data for a filing (if available).
        
        Args:
            accession_number: Filing ID
        
        Returns:
            URL to XBRL file, or None if not available
        
        Note:
            Not all companies file XBRL; need to check if it exists
        """
        
        # SEC XBRL files are typically at:
        # https://www.sec.gov/cgi-bin/viewer?action=view&cik=1045810&accession_number=0001045810-25-000023&xbrl_type=v
        
        # TODO: Implement XBRL existence check
        # For now, return URL structure (will be validated in parser)
        
        accession_clean = accession_number.replace("-", "")
        cik_from_accession = accession_clean[:10]
        
        return f"{SEC_BASE_URL}/cgi-bin/viewer?action=view&cik={int(cik_from_accession)}&accession_number={accession_number}&xbrl_type=v"


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def validate_nyse_ticker(ticker: str) -> bool:
    """
    Simple validation that ticker looks like NYSE format.
    
    Not foolproof, but catches obvious mistakes.
    """
    if not ticker:
        return False
    if len(ticker) > 5:
        return False
    if not ticker.isalpha():
        return False
    return True


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

if __name__ == "__main__":
    
    # Example 1: Fetch NVDA filings
    print("=" * 60)
    print("Example: Fetch NVDA 10-K and 10-Q filings")
    print("=" * 60)
    
    client = SECClient()
    
    try:
        # Get CIK
        cik = client.get_cik_from_ticker("NVDA")
        print(f"NVDA CIK: {cik}\n")
        
        # Get filings
        filings = client.get_filings(cik, ["10-K", "10-Q"], years=3)
        
        print(f"Found {len(filings)} filings:")
        for filing in filings[:5]:  # Show first 5
            print(f"  {filing['form_type']} ({filing['fiscal_period_end']}) - {filing['filing_date']}")
        
        # Download first filing
        if filings:
            first_filing = filings[0]
            output_path = Path(f"/tmp/{first_filing['accession_number']}.pdf")
            
            print(f"\nDownloading {first_filing['form_type']}...")
            success = client.download_filing_pdf(
                first_filing['accession_number'],
                output_path
            )
            
            if success:
                print(f"✅ Downloaded to {output_path}")
            else:
                print(f"❌ Download failed")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
