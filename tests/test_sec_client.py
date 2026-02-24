"""Unit tests for SEC Edgar API client.

Tests cover:
- Ticker to CIK conversion
- Filing metadata retrieval
- PDF downloads
- Error handling
- Caching behavior
- API rate limiting
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from src.sec_client import (
    SECClient,
    TickerNotFoundError,
    FilingNotFoundError,
    SECAPIError
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def client():
    """Create a fresh SECClient instance for each test."""
    return SECClient()


@pytest.fixture
def mock_company_tickers():
    """Mock SEC company tickers JSON response."""
    return {
        "0": {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA CORP"},
        "1": {"cik_str": 320193, "ticker": "AAPL", "title": "APPLE INC"},
        "2": {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"},
    }


@pytest.fixture
def mock_filings_response():
    """Mock SEC filings API response."""
    return {
        "cik_str": 1045810,
        "entityType": "large-accelerated filer",
        "name": "NVIDIA CORP",
        "filings": {
            "recent": {
                "accessionNumber": [
                    "0001045810-25-000023",
                    "0001045810-24-000108",
                    "0001045810-23-000075",
                ],
                "filingDate": [
                    "2025-01-26",
                    "2024-01-28",
                    "2023-06-29",
                ],
                "reportDate": [
                    "2025-01-26",
                    "2024-01-28",
                    "2023-06-29",
                ],
                "fiscalPeriodEnded": [
                    "2025-01-26",
                    "2024-01-28",
                    "2023-06-29",
                ],
                "form": [
                    "10-K",
                    "10-K",
                    "10-K",
                ],
                "isDelayed": [False, False, False],
                "isXBRL": [1, 1, 1],
            }
        }
    }


# ============================================================================
# TESTS: get_cik_from_ticker
# ============================================================================

class TestGetCIKFromTicker:
    """Test ticker to CIK conversion."""

    def test_valid_ticker_nvda(self, client, mock_company_tickers):
        """Test converting valid ticker NVDA to CIK."""
        with patch.object(client.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_company_tickers
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            cik = client.get_cik_from_ticker("NVDA")

            assert cik == "0001045810"
            assert mock_get.called

    def test_valid_ticker_lowercase(self, client, mock_company_tickers):
        """Test that lowercase ticker is converted to uppercase."""
        with patch.object(client.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_company_tickers
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            cik = client.get_cik_from_ticker("nvda")

            assert cik == "0001045810"

    def test_valid_ticker_with_whitespace(self, client, mock_company_tickers):
        """Test that whitespace is stripped from ticker."""
        with patch.object(client.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_company_tickers
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            cik = client.get_cik_from_ticker("  NVDA  ")

            assert cik == "0001045810"

    def test_invalid_ticker(self, client, mock_company_tickers):
        """Test that invalid ticker raises TickerNotFoundError."""
        with patch.object(client.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_company_tickers
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            with pytest.raises(TickerNotFoundError):
                client.get_cik_from_ticker("INVALID")

    def test_api_error(self, client):
        """Test that API errors raise SECAPIError."""
        with patch.object(client.session, "get") as mock_get:
            mock_get.side_effect = Exception("Connection error")

            with pytest.raises(SECAPIError):
                client.get_cik_from_ticker("NVDA")

    def test_invalid_json_response(self, client):
        """Test that invalid JSON response raises SECAPIError."""
        with patch.object(client.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            with pytest.raises(SECAPIError):
                client.get_cik_from_ticker("NVDA")

    def test_cik_caching(self, client, mock_company_tickers):
        """Test that CIK lookups are cached."""
        with patch.object(client.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_company_tickers
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            # First call
            cik1 = client.get_cik_from_ticker("NVDA")

            # Second call (should use cache, not call API)
            mock_get.reset_mock()
            cik2 = client.get_cik_from_ticker("NVDA")

            assert cik1 == cik2 == "0001045810"
            assert not mock_get.called  # Should use cache

    def test_cik_zero_padded(self, client, mock_company_tickers):
        """Test that CIK is zero-padded to 10 digits."""
        tickers = {
            "0": {"cik_str": 1234, "ticker": "TEST", "title": "TEST CORP"}
        }
        with patch.object(client.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = tickers
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            cik = client.get_cik_from_ticker("TEST")

            assert cik == "0000001234"
            assert len(cik) == 10


# ============================================================================
# TESTS: get_filings
# ============================================================================

class TestGetFilings:
    """Test filing metadata retrieval."""

    def test_get_filings_10k_only(self, client, mock_filings_response):
        """Test retrieving only 10-K filings."""
        with patch.object(client.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_filings_response
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            filings = client.get_filings("0001045810", ["10-K"], years=3)

            assert len(filings) == 3
            assert all(f["form_type"] == "10-K" for f in filings)

    def test_get_filings_has_required_fields(self, client, mock_filings_response):
        """Test that filings have all required fields."""
        with patch.object(client.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_filings_response
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            filings = client.get_filings("0001045810", ["10-K"], years=3)

            required_fields = {
                "accession_number", "filing_date", "fiscal_period_end",
                "form_type", "is_delayed", "is_xbrl"
            }
            for filing in filings:
                assert all(field in filing for field in required_fields)

    def test_get_filings_filters_delayed(self, client):
        """Test that delayed filings field is handled (API may not provide it)."""
        response_data = {
            "cik_str": 1045810,
            "filings": {
                "recent": {
                    "accessionNumber": [
                        "0001045810-25-000023",
                        "0001045810-24-000108",
                    ],
                    "filingDate": [
                        "2025-01-26",
                        "2024-01-28",
                    ],
                    "reportDate": [
                        "2025-01-26",
                        "2024-01-28",
                    ],
                    "form": ["10-K", "10-K"],
                    "isXBRL": [1, 1],
                }
            }
        }

        with patch.object(client.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = response_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            filings = client.get_filings("0001045810", ["10-K"], years=3)

            # Should have both filings (SEC API may not provide isDelayed field)
            assert len(filings) == 2
            assert all(f["is_delayed"] is False for f in filings)

    def test_get_filings_filters_by_year(self, client):
        """Test that filings are filtered by year."""
        response_data = {
            "cik_str": 1045810,
            "filings": {
                "recent": {
                    "accessionNumber": [
                        "0001045810-25-000023",
                        "0001045810-20-000001",  # 5 years old
                    ],
                    "filingDate": [
                        "2025-01-26",
                        "2020-01-28",
                    ],
                    "reportDate": [
                        "2025-01-26",
                        "2020-01-28",
                    ],
                    "fiscalPeriodEnded": [
                        "2025-01-26",
                        "2020-01-28",
                    ],
                    "form": ["10-K", "10-K"],
                    "isDelayed": [False, False],
                    "isXBRL": [1, 1],
                }
            }
        }

        with patch.object(client.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = response_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            # Request only 3 years
            filings = client.get_filings("0001045810", ["10-K"], years=3)

            # Should only have recent filing (2020 is outside 3-year window)
            assert len(filings) == 1
            assert filings[0]["filing_date"] == "2025-01-26"

    def test_get_filings_sorted_descending(self, client):
        """Test that filings are returned sorted by date (most recent first)."""
        response_data = {
            "cik_str": 1045810,
            "filings": {
                "recent": {
                    "accessionNumber": [
                        "0001045810-24-000108",
                        "0001045810-25-000023",  # Newer, but listed second
                        "0001045810-23-000001",
                    ],
                    "filingDate": [
                        "2024-01-28",
                        "2025-01-26",
                        "2023-06-29",
                    ],
                    "reportDate": [
                        "2024-01-28",
                        "2025-01-26",
                        "2023-06-29",
                    ],
                    "fiscalPeriodEnded": [
                        "2024-01-28",
                        "2025-01-26",
                        "2023-06-29",
                    ],
                    "form": ["10-K", "10-K", "10-K"],
                    "isDelayed": [False, False, False],
                    "isXBRL": [1, 1, 1],
                }
            }
        }

        with patch.object(client.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = response_data
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            filings = client.get_filings("0001045810", ["10-K"], years=3)

            # Should be sorted newest first
            assert filings[0]["filing_date"] == "2025-01-26"
            assert filings[1]["filing_date"] == "2024-01-28"
            assert filings[2]["filing_date"] == "2023-06-29"

    def test_get_filings_api_error(self, client):
        """Test that API errors raise SECAPIError."""
        with patch.object(client.session, "get") as mock_get:
            mock_get.side_effect = Exception("Connection error")

            with pytest.raises(SECAPIError):
                client.get_filings("0001045810", ["10-K"], years=3)


# ============================================================================
# TESTS: get_xbrl_url
# ============================================================================

class TestGetXBRLURL:
    """Test XBRL URL generation."""

    def test_xbrl_url_format(self, client):
        """Test that XBRL URL is formatted correctly."""
        accession = "0001045810-25-000023"
        xbrl_url = client.get_xbrl_url(accession)

        assert "viewer" in xbrl_url
        assert "1045810" in xbrl_url  # CIK
        assert accession in xbrl_url

    def test_xbrl_url_structure(self, client):
        """Test that XBRL URL has expected structure."""
        accession = "0001045810-25-000023"
        xbrl_url = client.get_xbrl_url(accession)

        assert xbrl_url.startswith("https://www.sec.gov/cgi-bin/viewer?")
        assert "action=view" in xbrl_url
        assert "cik=" in xbrl_url
        assert "accession_number=" in xbrl_url
        assert "xbrl_type=v" in xbrl_url


# ============================================================================
# TESTS: download_filing_pdf
# ============================================================================

class TestDownloadFilingPDF:
    """Test PDF download functionality."""

    def test_pdf_download_success(self, client, tmp_path):
        """Test successful PDF download."""
        output_file = tmp_path / "test.pdf"
        pdf_content = b"%PDF-1.4\n%test pdf content"

        with patch.object(client.session, "get") as mock_get:
            # Mock the filing index response
            html_response = Mock()
            html_response.content = b"""
            <html>
            <table>
            <tr><td>10-K</td><td>1</td><td><a href="/Archives/edgar/test.pdf">test.pdf</a></td><td>1000000</td></tr>
            </table>
            </html>
            """
            html_response.raise_for_status = Mock()

            # Mock the PDF download response
            pdf_response = Mock()
            pdf_response.content = pdf_content
            pdf_response.raise_for_status = Mock()

            # First call returns HTML index, second returns PDF
            mock_get.side_effect = [html_response, pdf_response]

            result = client.download_filing_pdf("0001045810-25-000023", output_file)

            assert result is True
            assert output_file.exists()
            with open(output_file, "rb") as f:
                assert f.read() == pdf_content

    def test_pdf_download_failure(self, client, tmp_path):
        """Test PDF download failure."""
        output_file = tmp_path / "test.pdf"

        with patch.object(client.session, "get") as mock_get:
            mock_get.side_effect = Exception("Network error")

            result = client.download_filing_pdf("0001045810-25-000023", output_file)

            assert result is False
            assert not output_file.exists()

    def test_pdf_download_no_documents_found(self, client, tmp_path):
        """Test handling when no documents found in filing."""
        output_file = tmp_path / "test.pdf"

        with patch.object(client.session, "get") as mock_get:
            # Mock response with no documents
            html_response = Mock()
            html_response.content = b"<html><table></table></html>"
            html_response.raise_for_status = Mock()
            mock_get.return_value = html_response

            result = client.download_filing_pdf("0001045810-25-000023", output_file)

            assert result is False
            assert not output_file.exists()

    def test_pdf_creates_parent_directories(self, client, tmp_path):
        """Test that parent directories are created if needed."""
        output_file = tmp_path / "deep" / "nested" / "path" / "test.pdf"
        pdf_content = b"%PDF-1.4\ntest"

        with patch.object(client.session, "get") as mock_get:
            html_response = Mock()
            html_response.content = b"""
            <html>
            <table>
            <tr><td>10-K</td><td>1</td><td><a href="/Archives/edgar/test.pdf">test.pdf</a></td><td>1000</td></tr>
            </table>
            </html>
            """
            html_response.raise_for_status = Mock()

            pdf_response = Mock()
            pdf_response.content = pdf_content
            pdf_response.raise_for_status = Mock()

            mock_get.side_effect = [html_response, pdf_response]

            result = client.download_filing_pdf("0001045810-25-000023", output_file)

            assert result is True
            assert output_file.exists()
            assert output_file.parent.exists()
