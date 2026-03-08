"""
Unit tests for Phase 5: XML Builder

Tests xml_builder.py module functionality including:
- XML structure generation
- Metadata inclusion
- Data quality section
- Financial metrics organization
- Calculated metrics (margins, ratios)
- Audit trail generation
- XML validation
"""

import pytest
import xml.etree.ElementTree as ET
from pathlib import Path
import tempfile
import json

from src.xml_builder import XMLBuilder


@pytest.fixture
def sample_xbrl_metrics():
    """Sample XBRL metrics data for testing."""
    return {
        "cik": "0001045810",
        "entity_name": "NVIDIA CORP",
        "filings_processed": 12,
        "metrics_extracted": 286,
        "lookback_years": 3,
        "extraction_date": "2026-03-07T20:00:00.000000",
        "metrics": {
            "Revenues:USD": {
                "name": "Revenues",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {
                        "val": 130500000000,
                        "end": "2026-01-25",
                        "form": "10-K",
                        "filed": "2026-02-25",
                        "fy": 2026,
                        "fp": "FY"
                    }
                ]
            },
            "CostOfRevenue:USD": {
                "name": "CostOfRevenue",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {
                        "val": 29050000000,
                        "end": "2026-01-25",
                        "form": "10-K",
                        "filed": "2026-02-25",
                        "fy": 2026,
                        "fp": "FY"
                    }
                ]
            },
            "GrossProfit:USD": {
                "name": "GrossProfit",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {
                        "val": 101450000000,
                        "end": "2026-01-25",
                        "form": "10-K",
                        "filed": "2026-02-25",
                        "fy": 2026,
                        "fp": "FY"
                    }
                ]
            },
            "OperatingIncomeLoss:USD": {
                "name": "OperatingIncomeLoss",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {
                        "val": 81250000000,
                        "end": "2026-01-25",
                        "form": "10-K",
                        "filed": "2026-02-25",
                        "fy": 2026,
                        "fp": "FY"
                    }
                ]
            },
            "NetIncomeLoss:USD": {
                "name": "NetIncomeLoss",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {
                        "val": 60922000000,
                        "end": "2026-01-25",
                        "form": "10-K",
                        "filed": "2026-02-25",
                        "fy": 2026,
                        "fp": "FY"
                    }
                ]
            },
            "Assets:USD": {
                "name": "Assets",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {
                        "val": 309900000000,
                        "end": "2026-01-25",
                        "form": "10-K",
                        "filed": "2026-02-25",
                        "fy": 2026,
                        "fp": "FY"
                    }
                ]
            },
            "AssetsCurrent:USD": {
                "name": "AssetsCurrent",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {
                        "val": 100000000000,
                        "end": "2026-01-25",
                        "form": "10-K",
                        "filed": "2026-02-25",
                        "fy": 2026,
                        "fp": "FY"
                    }
                ]
            },
            "LiabilitiesCurrent:USD": {
                "name": "LiabilitiesCurrent",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {
                        "val": 25000000000,
                        "end": "2026-01-25",
                        "form": "10-K",
                        "filed": "2026-02-25",
                        "fy": 2026,
                        "fp": "FY"
                    }
                ]
            },
            "StockholdersEquity:USD": {
                "name": "StockholdersEquity",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {
                        "val": 231400000000,
                        "end": "2026-01-25",
                        "form": "10-K",
                        "filed": "2026-02-25",
                        "fy": 2026,
                        "fp": "FY"
                    }
                ]
            },
            "LongTermDebt:USD": {
                "name": "LongTermDebt",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {
                        "val": 10500000000,
                        "end": "2026-01-25",
                        "form": "10-K",
                        "filed": "2026-02-25",
                        "fy": 2026,
                        "fp": "FY"
                    }
                ]
            }
        }
    }


@pytest.fixture
def sample_validation_report():
    """Sample validation report for testing."""
    return {
        "ticker": "NVDA",
        "cik": "0001045810",
        "entity_name": "NVIDIA CORP",
        "validation_date": "2026-03-07T20:00:00.000000",
        "quality_score": 95,
        "metrics_validated": 286,
        "flag_summary": {
            "total": 5,
            "by_level": {
                "INFO": 0,
                "WARNING": 4,
                "ERROR": 1,
                "CRITICAL": 0
            }
        },
        "flags": [
            {
                "level": "ERROR",
                "metric": "TestMetric",
                "message": "Test error message",
                "value": 12345
            }
        ],
        "checks_performed": [
            "metric_value_validation",
            "yoy_growth_validation",
            "cross_metric_validation"
        ]
    }


class TestXMLBuilderBasics:
    """Test basic XML builder functionality."""

    def test_xml_builder_initialization(self):
        """Test XML builder can be initialized."""
        builder = XMLBuilder()
        assert builder is not None
        assert builder.version == "1.0"

    def test_build_filing_xml_returns_element(self, sample_xbrl_metrics,
                                              sample_validation_report):
        """Test build_filing_xml returns an XML Element."""
        builder = XMLBuilder()
        xml_root = builder.build_filing_xml(
            ticker="NVDA",
            xbrl_metrics=sample_xbrl_metrics,
            validation_report=sample_validation_report
        )

        assert xml_root is not None
        assert isinstance(xml_root, ET.Element)
        assert xml_root.tag == "CompanyFinancials"


class TestXMLStructure:
    """Test XML structure and required sections."""

    def test_xml_has_required_sections(self, sample_xbrl_metrics,
                                       sample_validation_report):
        """Test XML contains all required sections."""
        builder = XMLBuilder()
        xml_root = builder.build_filing_xml(
            ticker="NVDA",
            xbrl_metrics=sample_xbrl_metrics,
            validation_report=sample_validation_report
        )

        # Check for required sections
        assert xml_root.find("Metadata") is not None
        assert xml_root.find("DataQuality") is not None
        assert xml_root.find("FinancialMetrics") is not None
        assert xml_root.find("CalculatedMetrics") is not None
        assert xml_root.find("AuditTrail") is not None

    def test_metadata_section_complete(self, sample_xbrl_metrics,
                                       sample_validation_report):
        """Test metadata section contains required fields."""
        builder = XMLBuilder()
        xml_root = builder.build_filing_xml(
            ticker="NVDA",
            xbrl_metrics=sample_xbrl_metrics,
            validation_report=sample_validation_report
        )

        metadata = xml_root.find("Metadata")

        assert metadata.find("Ticker").text == "NVDA"
        assert metadata.find("CIK").text == "0001045810"
        assert metadata.find("EntityName").text == "NVIDIA CORP"
        assert metadata.find("FilingsProcessed").text == "12"
        assert metadata.find("MetricsExtracted").text == "286"

    def test_data_quality_section_complete(self, sample_xbrl_metrics,
                                           sample_validation_report):
        """Test data quality section contains validation results."""
        builder = XMLBuilder()
        xml_root = builder.build_filing_xml(
            ticker="NVDA",
            xbrl_metrics=sample_xbrl_metrics,
            validation_report=sample_validation_report
        )

        data_quality = xml_root.find("DataQuality")

        assert data_quality.find("QualityScore").text == "95"
        assert data_quality.find("MetricsValidated").text == "286"

        flags = data_quality.find("ValidationFlags")
        assert flags.find("Total").text == "5"
        assert flags.find("Error").text == "1"
        assert flags.find("Warning").text == "4"


class TestFinancialMetrics:
    """Test financial metrics organization in XML."""

    def test_financial_metrics_by_period(self, sample_xbrl_metrics,
                                         sample_validation_report):
        """Test financial metrics are organized by fiscal period."""
        builder = XMLBuilder()
        xml_root = builder.build_filing_xml(
            ticker="NVDA",
            xbrl_metrics=sample_xbrl_metrics,
            validation_report=sample_validation_report
        )

        metrics_section = xml_root.find("FinancialMetrics")
        periods = metrics_section.findall("FiscalPeriod")

        assert len(periods) >= 1

        # Check first period structure
        period = periods[0]
        assert period.get("end") is not None
        assert period.get("form") is not None
        assert period.find("FilingDate") is not None
        assert period.find("Metrics") is not None

    def test_metrics_have_required_fields(self, sample_xbrl_metrics,
                                          sample_validation_report):
        """Test each metric has value, unit, and confidence."""
        builder = XMLBuilder()
        xml_root = builder.build_filing_xml(
            ticker="NVDA",
            xbrl_metrics=sample_xbrl_metrics,
            validation_report=sample_validation_report
        )

        metrics_section = xml_root.find("FinancialMetrics")
        period = metrics_section.find("FiscalPeriod")
        metrics = period.find("Metrics")
        metric = metrics.find("Metric")

        assert metric.get("name") is not None
        assert metric.find("Value") is not None
        assert metric.find("Unit") is not None
        assert metric.find("Confidence") is not None


class TestCalculatedMetrics:
    """Test calculated metrics (margins and ratios)."""

    def test_margins_calculated(self, sample_xbrl_metrics,
                               sample_validation_report):
        """Test profit margins are calculated."""
        builder = XMLBuilder()
        xml_root = builder.build_filing_xml(
            ticker="NVDA",
            xbrl_metrics=sample_xbrl_metrics,
            validation_report=sample_validation_report
        )

        calculated = xml_root.find("CalculatedMetrics")
        margins = calculated.find("Margins")

        # Should have calculated gross, operating, and net margins
        margin_names = [m.get("name") for m in margins.findall("Margin")]
        assert "GrossMargin" in margin_names
        assert "OperatingMargin" in margin_names
        assert "NetMargin" in margin_names

    def test_gross_margin_calculation(self, sample_xbrl_metrics,
                                      sample_validation_report):
        """Test gross margin is calculated correctly."""
        builder = XMLBuilder()
        xml_root = builder.build_filing_xml(
            ticker="NVDA",
            xbrl_metrics=sample_xbrl_metrics,
            validation_report=sample_validation_report
        )

        calculated = xml_root.find("CalculatedMetrics")
        margins = calculated.find("Margins")

        gross_margin = None
        for margin in margins.findall("Margin"):
            if margin.get("name") == "GrossMargin":
                gross_margin = float(margin.find("Value").text)
                break

        # GrossMargin = (Revenue - COGS) / Revenue
        # (130.5B - 29.05B) / 130.5B = 0.7773
        assert gross_margin is not None
        assert 0.77 < gross_margin < 0.78  # Allow small rounding

    def test_ratios_calculated(self, sample_xbrl_metrics,
                               sample_validation_report):
        """Test financial ratios are calculated."""
        builder = XMLBuilder()
        xml_root = builder.build_filing_xml(
            ticker="NVDA",
            xbrl_metrics=sample_xbrl_metrics,
            validation_report=sample_validation_report
        )

        calculated = xml_root.find("CalculatedMetrics")
        ratios = calculated.find("Ratios")

        ratio_names = [r.get("name") for r in ratios.findall("Ratio")]
        assert "CurrentRatio" in ratio_names
        assert "DebtToEquity" in ratio_names
        assert "ReturnOnAssets" in ratio_names
        assert "ReturnOnEquity" in ratio_names

    def test_current_ratio_calculation(self, sample_xbrl_metrics,
                                       sample_validation_report):
        """Test current ratio is calculated correctly."""
        builder = XMLBuilder()
        xml_root = builder.build_filing_xml(
            ticker="NVDA",
            xbrl_metrics=sample_xbrl_metrics,
            validation_report=sample_validation_report
        )

        calculated = xml_root.find("CalculatedMetrics")
        ratios = calculated.find("Ratios")

        current_ratio = None
        for ratio in ratios.findall("Ratio"):
            if ratio.get("name") == "CurrentRatio":
                current_ratio = float(ratio.find("Value").text)
                break

        # CurrentRatio = CurrentAssets / CurrentLiabilities
        # 100B / 25B = 4.0
        assert current_ratio is not None
        assert 3.9 < current_ratio < 4.1


class TestAuditTrail:
    """Test audit trail generation."""

    def test_audit_trail_has_sources(self, sample_xbrl_metrics,
                                     sample_validation_report):
        """Test audit trail includes data sources."""
        builder = XMLBuilder()
        xml_root = builder.build_filing_xml(
            ticker="NVDA",
            xbrl_metrics=sample_xbrl_metrics,
            validation_report=sample_validation_report
        )

        audit = xml_root.find("AuditTrail")
        sources = audit.find("DataSources")

        assert sources.find("Primary").text == "SEC Edgar XBRL API"
        assert "companyfacts" in sources.find("API").text

    def test_audit_trail_has_processing_steps(self, sample_xbrl_metrics,
                                              sample_validation_report):
        """Test audit trail includes processing steps."""
        builder = XMLBuilder()
        xml_root = builder.build_filing_xml(
            ticker="NVDA",
            xbrl_metrics=sample_xbrl_metrics,
            validation_report=sample_validation_report
        )

        audit = xml_root.find("AuditTrail")
        steps = audit.find("ProcessingSteps")

        step_list = steps.findall("Step")
        assert len(step_list) >= 3  # Extraction, Validation, XML Generation


class TestXMLSaveAndValidation:
    """Test XML saving and validation."""

    def test_save_xml_to_file(self, sample_xbrl_metrics,
                              sample_validation_report):
        """Test XML can be saved to file."""
        builder = XMLBuilder()
        xml_root = builder.build_filing_xml(
            ticker="NVDA",
            xbrl_metrics=sample_xbrl_metrics,
            validation_report=sample_validation_report
        )

        # Save to temp file
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.xml"
            success = builder.save_xml(xml_root, output_path)

            assert success
            assert output_path.exists()
            assert output_path.stat().st_size > 0

    def test_saved_xml_is_valid(self, sample_xbrl_metrics,
                                sample_validation_report):
        """Test saved XML can be parsed."""
        builder = XMLBuilder()
        xml_root = builder.build_filing_xml(
            ticker="NVDA",
            xbrl_metrics=sample_xbrl_metrics,
            validation_report=sample_validation_report
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.xml"
            builder.save_xml(xml_root, output_path)

            # Parse the saved file
            tree = ET.parse(output_path)
            root = tree.getroot()

            assert root.tag == "CompanyFinancials"
            assert root.find("Metadata") is not None

    def test_xml_validation(self, sample_xbrl_metrics,
                           sample_validation_report):
        """Test XML validation function."""
        builder = XMLBuilder()
        xml_root = builder.build_filing_xml(
            ticker="NVDA",
            xbrl_metrics=sample_xbrl_metrics,
            validation_report=sample_validation_report
        )

        errors = builder.validate_xml(xml_root)

        # Should have no validation errors
        assert len(errors) == 0

    def test_xml_validation_detects_missing_sections(self):
        """Test XML validation detects missing required sections."""
        builder = XMLBuilder()

        # Create incomplete XML
        root = ET.Element("CompanyFinancials")
        ET.SubElement(root, "Metadata")
        # Missing DataQuality, FinancialMetrics, AuditTrail

        errors = builder.validate_xml(root)

        assert len(errors) > 0
        assert any("DataQuality" in err for err in errors)
        assert any("FinancialMetrics" in err for err in errors)
