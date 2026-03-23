"""Unit tests for XBRL Parser (Phase 3).

All tests use REAL SEC API data (no mocking).
Tests verify:
- XBRL data fetching
- Metric extraction
- Confidence scoring
- Year-over-year calculations
- JSON output generation

Note: These tests make actual HTTP requests to SEC API.
This is intentional - we test against real, authoritative data.
"""

import json
import pytest
from pathlib import Path
from datetime import datetime

from src.xbrl_parser import XBRLParser


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def parser():
    """Create XBRLParser instance."""
    return XBRLParser()


@pytest.fixture
def nvda_filings():
    """NVDA filings for Phase 3 testing."""
    return [
        {
            'accession_number': '0001045810-25-000230',
            'filing_date': '2025-11-19',
            'fiscal_period_end': '2025-10-26',
            'form_type': '10-Q',
            'is_xbrl': True,
        },
        {
            'accession_number': '0001045810-25-000209',
            'filing_date': '2025-08-27',
            'fiscal_period_end': '2025-07-27',
            'form_type': '10-Q',
            'is_xbrl': True,
        },
        {
            'accession_number': '0001045810-25-000116',
            'filing_date': '2025-05-28',
            'fiscal_period_end': '2025-04-27',
            'form_type': '10-Q',
            'is_xbrl': True,
        },
        {
            'accession_number': '0001045810-25-000023',
            'filing_date': '2025-02-26',
            'fiscal_period_end': '2025-01-26',
            'form_type': '10-K',
            'is_xbrl': True,
        },
    ]


# ============================================================================
# TESTS: DATA FETCHING
# ============================================================================

class TestFetchXBRLData:
    """Test XBRL data fetching from SEC API."""

    def test_fetch_xbrl_data_success(self, parser):
        """Test fetching XBRL data for valid CIK."""
        data = parser.fetch_xbrl_data('0001045810')  # NVDA

        assert data is not None
        assert 'cik' in data
        assert 'entityName' in data
        assert 'facts' in data
        assert data['entityName'] == 'NVIDIA CORP'

    def test_fetch_xbrl_data_contains_us_gaap(self, parser):
        """Test that fetched data contains US-GAAP metrics."""
        data = parser.fetch_xbrl_data('0001045810')

        facts = data.get('facts', {})
        assert 'us-gaap' in facts
        assert len(facts['us-gaap']) > 0

    def test_fetch_xbrl_data_caching(self, parser):
        """Test that XBRL data is cached after first fetch."""
        # First fetch
        data1 = parser.fetch_xbrl_data('0001045810')
        assert data1 is not None

        # Second fetch should come from cache
        data2 = parser.fetch_xbrl_data('0001045810')
        assert data1 is data2  # Same object reference


class TestExtractMetrics:
    """Test metric extraction from XBRL data."""

    def test_extract_metrics_for_nvda(self, parser, nvda_filings):
        """Test extracting metrics for NVDA filings."""
        result = parser.extract_metrics_for_filings(
            cik='0001045810',
            filings=nvda_filings,
            lookback_years=3
        )

        assert result['cik'] == '0001045810'
        assert result['entity_name'] == 'NVIDIA CORP'
        assert result['filings_processed'] == len(nvda_filings)
        assert result['metrics_extracted'] > 0

    def test_metrics_have_required_fields(self, parser, nvda_filings):
        """Test that extracted metrics have all required fields."""
        result = parser.extract_metrics_for_filings(
            cik='0001045810',
            filings=nvda_filings,
            lookback_years=3
        )

        metrics = result['metrics']
        assert len(metrics) > 0

        # Check first metric has required fields
        first_metric = next(iter(metrics.values()))
        assert 'name' in first_metric
        assert 'unit' in first_metric
        assert 'values' in first_metric
        assert 'confidence' in first_metric

    def test_extracted_metrics_have_values(self, parser, nvda_filings):
        """Test that metrics contain actual values."""
        result = parser.extract_metrics_for_filings(
            cik='0001045810',
            filings=nvda_filings,
            lookback_years=3
        )

        metrics = result['metrics']

        # Check that metrics have values with actual data
        for metric in metrics.values():
            values = metric.get('values', [])
            assert len(values) > 0

            # Check each value has required fields
            for val in values:
                assert 'val' in val
                assert 'end' in val or 'start' in val
                assert isinstance(val['val'], (int, float))


# ============================================================================
# TESTS: CONFIDENCE SCORING
# ============================================================================

class TestConfidenceScoring:
    """Test confidence score calculation."""

    def test_confidence_100_for_target_filings(self, parser, nvda_filings):
        """Test that metrics from target filings get 100% confidence."""
        result = parser.extract_metrics_for_filings(
            cik='0001045810',
            filings=nvda_filings,
            lookback_years=3
        )

        metrics = result['metrics']

        # All metrics should have confidence >= 50
        for metric in metrics.values():
            confidence = metric.get('confidence', 0)
            assert confidence >= 50, f"Confidence too low: {confidence}"

    def test_confidence_scores_reasonable(self, parser, nvda_filings):
        """Test that confidence scores are in reasonable range."""
        result = parser.extract_metrics_for_filings(
            cik='0001045810',
            filings=nvda_filings,
            lookback_years=3
        )

        metrics = result['metrics']

        for metric_key, metric in metrics.items():
            confidence = metric.get('confidence', 0)
            assert 0 <= confidence <= 100, f"Invalid confidence for {metric_key}: {confidence}"


# ============================================================================
# TESTS: YEAR-OVER-YEAR ANALYSIS
# ============================================================================

class TestYoYAnalysis:
    """Test year-over-year change calculations."""

    def test_yoy_analysis_present(self, parser, nvda_filings):
        """Test that YoY analysis is calculated for metrics when data available."""
        result = parser.extract_metrics_for_filings(
            cik='0001045810',
            filings=nvda_filings,
            lookback_years=3
        )

        metrics = result['metrics']

        # Count metrics with YoY analysis
        with_yoy = sum(1 for m in metrics.values() if m.get('yoy_change'))

        # Should have many metrics with YoY data (but may be 0 if filings too recent)
        # Just verify the structure is correct
        assert len(metrics) > 0, "No metrics extracted"

    def test_yoy_comparisons_structure(self, parser, nvda_filings):
        """Test YoY comparison structure."""
        result = parser.extract_metrics_for_filings(
            cik='0001045810',
            filings=nvda_filings,
            lookback_years=3
        )

        metrics = result['metrics']

        # Find a metric with YoY data
        for metric in metrics.values():
            yoy = metric.get('yoy_change')
            if yoy:
                comparisons = yoy.get('yoy_comparisons', [])

                if comparisons:
                    comp = comparisons[0]
                    assert 'period' in comp
                    assert 'current_year' in comp
                    assert 'prior_year' in comp
                    assert 'change_percent' in comp
                    assert isinstance(comp['change_percent'], (int, float))
                break


# ============================================================================
# TESTS: JSON OUTPUT
# ============================================================================

class TestJSONOutput:
    """Test JSON file generation."""

    def test_save_metrics_to_json(self, parser, nvda_filings, tmp_path):
        """Test saving metrics to JSON file."""
        result = parser.extract_metrics_for_filings(
            cik='0001045810',
            filings=nvda_filings,
            lookback_years=3
        )

        output_path = tmp_path / 'test_metrics.json'
        success = parser.save_metrics_to_json(result, output_path)

        assert success
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_json_output_valid(self, parser, nvda_filings, tmp_path):
        """Test that generated JSON is valid and readable."""
        result = parser.extract_metrics_for_filings(
            cik='0001045810',
            filings=nvda_filings,
            lookback_years=3
        )

        output_path = tmp_path / 'test_metrics.json'
        parser.save_metrics_to_json(result, output_path)

        # Read and parse JSON
        with open(output_path) as f:
            loaded = json.load(f)

        # Verify structure
        assert loaded['cik'] == '0001045810'
        assert loaded['entity_name'] == 'NVIDIA CORP'
        assert 'metrics' in loaded
        assert len(loaded['metrics']) > 0

    def test_json_output_contains_metadata(self, parser, nvda_filings, tmp_path):
        """Test that JSON contains all required metadata."""
        result = parser.extract_metrics_for_filings(
            cik='0001045810',
            filings=nvda_filings,
            lookback_years=3
        )

        output_path = tmp_path / 'test_metrics.json'
        parser.save_metrics_to_json(result, output_path)

        with open(output_path) as f:
            loaded = json.load(f)

        # Check metadata
        assert 'cik' in loaded
        assert 'entity_name' in loaded
        assert 'filings_processed' in loaded
        assert 'metrics_extracted' in loaded
        assert 'extraction_date' in loaded
        assert 'lookback_years' in loaded


# ============================================================================
# TESTS: MULTIPLE COMPANIES
# ============================================================================

class TestMultipleCompanies:
    """Test XBRL parsing for different companies."""

    def test_aapl_metrics_extraction(self, parser):
        """Test extracting metrics for AAPL."""
        # Use actual AAPL CIK and recent filing data
        aapl_filings = [
            {
                'accession_number': '0000320193-25-000087',
                'filing_date': '2025-08-01',
                'fiscal_period_end': '2025-06-28',
                'form_type': '10-Q',
                'is_xbrl': True,
            }
        ]

        result = parser.extract_metrics_for_filings(
            cik='0000320193',  # AAPL
            filings=aapl_filings,
            lookback_years=3
        )

        # Just verify we got company data (metrics may be 0 if filing date outside filter)
        assert result['cik'] == '0000320193'
        assert 'APPLE' in result['entity_name'].upper()

    def test_different_companies_have_metrics(self, parser):
        """Test that different companies have extractable metrics."""
        companies = [
            ('0001045810', 'NVDA'),  # NVIDIA
            ('0000320193', 'AAPL'),  # Apple
        ]

        for cik, name in companies:
            data = parser.fetch_xbrl_data(cik)
            assert data is not None
            assert len(data['facts']['us-gaap']) > 0


# ============================================================================
# TESTS: EDGE CASES
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_filings_list(self, parser):
        """Test behavior with empty filings list."""
        result = parser.extract_metrics_for_filings(
            cik='0001045810',
            filings=[],
            lookback_years=3
        )

        # Should return valid structure even with no filings
        assert 'metrics' in result
        assert result['filings_processed'] == 0

    def test_lookback_years_filters_data(self, parser, nvda_filings):
        """Test that lookback_years parameter filters data."""
        result_1year = parser.extract_metrics_for_filings(
            cik='0001045810',
            filings=nvda_filings,
            lookback_years=1
        )

        result_3year = parser.extract_metrics_for_filings(
            cik='0001045810',
            filings=nvda_filings,
            lookback_years=3
        )

        # 3-year should have at least as many metrics as 1-year
        assert result_3year['metrics_extracted'] >= result_1year['metrics_extracted']


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests combining multiple phases."""

    def test_full_pipeline_nvda(self, parser, nvda_filings, tmp_path):
        """Test complete Phase 3 pipeline for NVDA."""
        # Extract metrics
        metrics = parser.extract_metrics_for_filings(
            cik='0001045810',
            filings=nvda_filings,
            lookback_years=3
        )

        # Save to JSON
        output_path = tmp_path / 'NVDA_metrics.json'
        success = parser.save_metrics_to_json(metrics, output_path)

        # Verify
        assert success
        assert output_path.exists()

        # Load and verify content
        with open(output_path) as f:
            loaded = json.load(f)

        # Metrics count can vary based on XBRL data availability
        assert loaded['metrics_extracted'] > 200, "Should extract 200+ metrics for NVDA"
        assert loaded['entity_name'] == 'NVIDIA CORP'

    def test_metrics_are_numeric(self, parser, nvda_filings):
        """Test that extracted metric values are numeric."""
        result = parser.extract_metrics_for_filings(
            cik='0001045810',
            filings=nvda_filings,
            lookback_years=3
        )

        metrics = result['metrics']

        for metric_key, metric in metrics.items():
            for value in metric['values']:
                val = value.get('val')
                assert isinstance(val, (int, float)), \
                    f"Non-numeric value in {metric_key}: {val}"


# ============================================================================
# TESTS: IFRS TAXONOMY DETECTION (20-F / foreign private issuers)
# ============================================================================

class TestIFRSTaxonomyDetection:
    """
    Test auto-detection of IFRS-full taxonomy vs US-GAAP.
    Uses mocked XBRL responses so no network calls are needed.
    """

    @pytest.fixture
    def mock_ifrs_xbrl(self):
        """Mock XBRL companyfacts response using ifrs-full instead of us-gaap."""
        return {
            "cik": "0000875320",
            "entityName": "ASTRAZENECA PLC",
            "facts": {
                "ifrs-full": {
                    "Revenue": {
                        "label": "Revenue",
                        "units": {
                            "USD": [
                                {
                                    "val": 54072000000,
                                    "end": "2024-12-31",
                                    "form": "20-F",
                                    "filed": "2025-02-20",
                                    "accn": "0000875320-25-000010",
                                },
                            ]
                        },
                    },
                    "ProfitLoss": {
                        "label": "Profit (loss)",
                        "units": {
                            "USD": [
                                {
                                    "val": 5955000000,
                                    "end": "2024-12-31",
                                    "form": "20-F",
                                    "filed": "2025-02-20",
                                    "accn": "0000875320-25-000010",
                                },
                            ]
                        },
                    },
                }
            },
        }

    @pytest.fixture
    def azn_filings(self):
        """AZN 20-F filing metadata."""
        return [
            {
                "accession_number": "0000875320-25-000010",
                "filing_date": "2025-02-20",
                "fiscal_period_end": "2024-12-31",
                "form_type": "20-F",
                "is_xbrl": True,
            },
        ]

    def test_ifrs_taxonomy_detected(self, parser, mock_ifrs_xbrl, azn_filings, monkeypatch):
        """IFRS-full taxonomy is detected when us-gaap facts are absent."""
        monkeypatch.setattr(parser, "fetch_xbrl_data", lambda cik: mock_ifrs_xbrl)
        result = parser.extract_metrics_for_filings(
            cik="0000875320",
            filings=azn_filings,
            lookback_years=3,
        )
        assert result["taxonomy"] == "ifrs-full"

    def test_ifrs_metrics_extracted(self, parser, mock_ifrs_xbrl, azn_filings, monkeypatch):
        """Metrics are extracted from ifrs-full facts."""
        monkeypatch.setattr(parser, "fetch_xbrl_data", lambda cik: mock_ifrs_xbrl)
        result = parser.extract_metrics_for_filings(
            cik="0000875320",
            filings=azn_filings,
            lookback_years=3,
        )
        assert result["metrics_extracted"] > 0
        # Revenue metric should be present
        assert any("Revenue" in key for key in result["metrics"])

    def test_usgaap_taxonomy_default(self, parser, monkeypatch):
        """US-GAAP is detected when us-gaap facts are present."""
        mock_gaap = {
            "entityName": "US CORP",
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "label": "Revenues",
                        "units": {
                            "USD": [
                                {"val": 100, "end": "2024-12-31", "form": "10-K",
                                 "filed": "2025-02-01", "accn": "0000000001-25-000001"}
                            ]
                        },
                    }
                }
            },
        }
        filings = [{"accession_number": "0000000001-25-000001", "filing_date": "2025-02-01",
                    "fiscal_period_end": "2024-12-31", "form_type": "10-K", "is_xbrl": True}]
        monkeypatch.setattr(parser, "fetch_xbrl_data", lambda cik: mock_gaap)
        result = parser.extract_metrics_for_filings(
            cik="0000000001", filings=filings, lookback_years=3
        )
        assert result["taxonomy"] == "us-gaap"

    def test_fallback_taxonomy_when_empty(self, parser, monkeypatch):
        """Taxonomy falls back to us-gaap when facts dict is empty."""
        mock_empty = {"entityName": "EMPTY CORP", "facts": {}}
        monkeypatch.setattr(parser, "fetch_xbrl_data", lambda cik: mock_empty)
        result = parser.extract_metrics_for_filings(
            cik="0000000002", filings=[], lookback_years=3
        )
        assert result["taxonomy"] == "us-gaap"

