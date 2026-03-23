"""
XML Builder for SEC Filing Parser - Phase 5

This module generates structured XML output from validated financial data.

The XML output includes:
- Filing metadata (ticker, CIK, dates)
- Data quality metrics (validation results)
- Financial statements (Income, Balance Sheet, Cash Flow)
- Calculated metrics (margins, ratios)
- Audit trail (data sources, extraction process)

Author: SEC Filing Parser Team
Date: March 7, 2026
"""

import logging
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

import config

logger = logging.getLogger(__name__)


class XMLBuilder:
    """
    Builds structured XML output from financial data.

    This class generates comprehensive XML files that include:
    - Metadata about the filing
    - Financial statement line items
    - Calculated financial ratios
    - Data quality indicators
    - Complete audit trail
    """

    def __init__(self):
        """Initialize XML Builder."""
        self.version = "1.0"

    def build_filing_xml(self, ticker: str, xbrl_metrics: Dict,
                        validation_report: Dict) -> ET.Element:
        """
        Build complete XML for a single company's filings.

        Args:
            ticker: Stock ticker symbol
            xbrl_metrics: XBRL metrics from Phase 3
            validation_report: Validation results from Phase 4

        Returns:
            XML Element tree root
        """
        # Create root element
        root = ET.Element("CompanyFinancials")
        root.set("version", self.version)
        root.set("generated", datetime.now().strftime('%Y-%m-%dT%H:%M:%S') + "Z")

        # Add metadata
        self._add_metadata(root, ticker, xbrl_metrics)

        # Add data quality section
        self._add_data_quality(root, validation_report)

        # Add financial metrics organized by period
        self._add_financial_metrics(root, xbrl_metrics)

        # Add calculated ratios and margins
        self._add_calculated_metrics(root, xbrl_metrics)

        # Add audit trail
        self._add_audit_trail(root, xbrl_metrics, validation_report)

        return root

    def _add_metadata(self, parent: ET.Element, ticker: str,
                     xbrl_metrics: Dict):
        """Add metadata section to XML."""
        metadata = ET.SubElement(parent, "Metadata")

        ET.SubElement(metadata, "Ticker").text = ticker.upper()
        ET.SubElement(metadata, "CIK").text = xbrl_metrics.get("cik", "")
        ET.SubElement(metadata, "CUSIP").text = xbrl_metrics.get("cusip") or ""
        ET.SubElement(metadata, "FIGI").text = xbrl_metrics.get("figi") or ""
        ET.SubElement(metadata, "EntityName").text = xbrl_metrics.get("entity_name", "")
        ET.SubElement(metadata, "FilingsProcessed").text = str(
            xbrl_metrics.get("filings_processed", 0)
        )
        ET.SubElement(metadata, "MetricsExtracted").text = str(
            xbrl_metrics.get("metrics_extracted", 0)
        )
        ET.SubElement(metadata, "LookbackYears").text = str(
            xbrl_metrics.get("lookback_years", 3)
        )
        ET.SubElement(metadata, "ExtractionDate").text = xbrl_metrics.get(
            "extraction_date", ""
        )

    def _add_data_quality(self, parent: ET.Element, validation_report: Dict):
        """Add data quality section to XML."""
        data_quality = ET.SubElement(parent, "DataQuality")

        ET.SubElement(data_quality, "QualityScore").text = str(
            validation_report.get("quality_score", 0)
        )
        ET.SubElement(data_quality, "MetricsValidated").text = str(
            validation_report.get("metrics_validated", 0)
        )

        # Flag summary
        flag_summary = validation_report.get("flag_summary", {})
        by_level = flag_summary.get("by_level", {})

        flags = ET.SubElement(data_quality, "ValidationFlags")
        ET.SubElement(flags, "Total").text = str(flag_summary.get("total", 0))
        ET.SubElement(flags, "Critical").text = str(by_level.get("CRITICAL", 0))
        ET.SubElement(flags, "Error").text = str(by_level.get("ERROR", 0))
        ET.SubElement(flags, "Warning").text = str(by_level.get("WARNING", 0))
        ET.SubElement(flags, "Info").text = str(by_level.get("INFO", 0))

        # Include critical flags details if any
        validation_flags = validation_report.get("flags", [])
        critical_flags = [
            f for f in validation_flags
            if f.get("level") in ["CRITICAL", "ERROR"]
        ]

        if critical_flags:
            critical_section = ET.SubElement(data_quality, "CriticalIssues")
            for i, flag in enumerate(critical_flags[:10], 1):  # Limit to 10
                issue = ET.SubElement(critical_section, "Issue")
                issue.set("id", str(i))
                ET.SubElement(issue, "Level").text = flag.get("level", "")
                ET.SubElement(issue, "Metric").text = flag.get("metric", "")
                ET.SubElement(issue, "Message").text = flag.get("message", "")
                if flag.get("value") is not None:
                    ET.SubElement(issue, "Value").text = str(flag.get("value"))

    def _add_financial_metrics(self, parent: ET.Element, xbrl_metrics: Dict):
        """Add financial metrics organized by period."""
        metrics_section = ET.SubElement(parent, "FinancialMetrics")

        metrics = xbrl_metrics.get("metrics", {})

        # Organize metrics by fiscal period
        periods = {}
        for metric_key, metric_data in metrics.items():
            for value_entry in metric_data.get("values", []):
                period_end = value_entry.get("end")
                form = value_entry.get("form", "")
                filing_date = value_entry.get("filed", "")

                if period_end:
                    period_key = f"{period_end}_{form}"
                    if period_key not in periods:
                        periods[period_key] = {
                            "period_end": period_end,
                            "form": form,
                            "filing_date": filing_date,
                            "metrics": {}
                        }

                    metric_name = metric_data.get("name")
                    unit = metric_data.get("unit")
                    confidence = metric_data.get("confidence", 0)

                    periods[period_key]["metrics"][metric_name] = {
                        "value": value_entry.get("val"),
                        "unit": unit,
                        "confidence": confidence
                    }

        # Add each period to XML
        for period_key in sorted(periods.keys(), reverse=True):  # Most recent first
            period_data = periods[period_key]
            period_elem = ET.SubElement(metrics_section, "FiscalPeriod")
            period_elem.set("end", period_data["period_end"])
            period_elem.set("form", period_data["form"])

            ET.SubElement(period_elem, "FilingDate").text = period_data["filing_date"]

            # Add metrics for this period
            metrics_elem = ET.SubElement(period_elem, "Metrics")
            for metric_name, metric_info in period_data["metrics"].items():
                metric_elem = ET.SubElement(metrics_elem, "Metric")
                metric_elem.set("name", metric_name)

                ET.SubElement(metric_elem, "Value").text = str(metric_info["value"])
                ET.SubElement(metric_elem, "Unit").text = str(metric_info["unit"])
                ET.SubElement(metric_elem, "Confidence").text = str(
                    metric_info["confidence"]
                )

    def _add_calculated_metrics(self, parent: ET.Element, xbrl_metrics: Dict):
        """Add calculated financial ratios and margins."""
        calculated = ET.SubElement(parent, "CalculatedMetrics")

        metrics = xbrl_metrics.get("metrics", {})

        # Get the most recent annual period data (10-K)
        latest_annual = self._get_latest_annual_period(metrics)

        if not latest_annual:
            logger.warning("No annual period data found for calculated metrics")
            return

        # Calculate margins
        margins = self._calculate_margins(latest_annual)
        if margins:
            margins_elem = ET.SubElement(calculated, "Margins")
            for name, value in margins.items():
                margin = ET.SubElement(margins_elem, "Margin")
                margin.set("name", name)
                ET.SubElement(margin, "Value").text = f"{value:.4f}"
                ET.SubElement(margin, "Percentage").text = f"{value * 100:.2f}%"

        # Calculate ratios
        ratios = self._calculate_ratios(latest_annual)
        if ratios:
            ratios_elem = ET.SubElement(calculated, "Ratios")
            for name, value in ratios.items():
                ratio = ET.SubElement(ratios_elem, "Ratio")
                ratio.set("name", name)
                ET.SubElement(ratio, "Value").text = f"{value:.4f}"

        # Add period info
        ET.SubElement(calculated, "BasedOnPeriod").text = latest_annual.get(
            "period_end", "Unknown"
        )

    def _add_audit_trail(self, parent: ET.Element, xbrl_metrics: Dict,
                        validation_report: Dict):
        """Add audit trail section."""
        audit = ET.SubElement(parent, "AuditTrail")

        # Data sources
        sources = ET.SubElement(audit, "DataSources")
        ET.SubElement(sources, "Primary").text = "SEC Edgar XBRL API"
        ET.SubElement(sources, "API").text = "https://data.sec.gov/api/xbrl/companyfacts/"

        # Processing steps
        steps = ET.SubElement(audit, "ProcessingSteps")

        step1 = ET.SubElement(steps, "Step")
        step1.set("sequence", "1")
        ET.SubElement(step1, "Action").text = "XBRL Data Extraction"
        ET.SubElement(step1, "Date").text = xbrl_metrics.get("extraction_date", "")
        ET.SubElement(step1, "Status").text = "COMPLETE"

        step2 = ET.SubElement(steps, "Step")
        step2.set("sequence", "2")
        ET.SubElement(step2, "Action").text = "Data Validation"
        ET.SubElement(step2, "Date").text = validation_report.get("validation_date", "")
        ET.SubElement(step2, "Status").text = "COMPLETE"

        step3 = ET.SubElement(steps, "Step")
        step3.set("sequence", "3")
        ET.SubElement(step3, "Action").text = "XML Generation"
        ET.SubElement(step3, "Date").text = datetime.now().strftime('%Y-%m-%dT%H:%M:%S') + "Z"
        ET.SubElement(step3, "Status").text = "COMPLETE"

        # Quality assurance
        qa = ET.SubElement(audit, "QualityAssurance")
        ET.SubElement(qa, "ValidationChecksPerformed").text = str(
            len(validation_report.get("checks_performed", []))
        )
        ET.SubElement(qa, "DataQualityScore").text = str(
            validation_report.get("quality_score", 0)
        )

    def _get_latest_annual_period(self, metrics: Dict) -> Optional[Dict]:
        """Extract the most recent annual (10-K) period data."""
        # Collect all annual periods
        annual_periods = {}

        for metric_key, metric_data in metrics.items():
            for value_entry in metric_data.get("values", []):
                form = value_entry.get("form", "")
                if form in config.ANNUAL_FORM_TYPES:
                    period_end = value_entry.get("end")
                    if period_end not in annual_periods:
                        annual_periods[period_end] = {"period_end": period_end}

                    metric_name = metric_data.get("name")
                    annual_periods[period_end][metric_name] = value_entry.get("val")

        if not annual_periods:
            return None

        # Get most recent period
        latest_period = sorted(annual_periods.keys(), reverse=True)[0]
        return annual_periods[latest_period]

    def _calculate_margins(self, period_data: Dict) -> Dict[str, float]:
        """Calculate profit margins."""
        margins = {}

        revenue = period_data.get("Revenues") or \
                 period_data.get("RevenueFromContractWithCustomerExcludingAssessedTax")
        gross_profit = period_data.get("GrossProfit")
        operating_income = period_data.get("OperatingIncomeLoss")
        net_income = period_data.get("NetIncomeLoss")

        if revenue and revenue > 0:
            if gross_profit is not None:
                margins["GrossMargin"] = gross_profit / revenue

            if operating_income is not None:
                margins["OperatingMargin"] = operating_income / revenue

            if net_income is not None:
                margins["NetMargin"] = net_income / revenue

        return margins

    def _calculate_ratios(self, period_data: Dict) -> Dict[str, float]:
        """Calculate financial ratios."""
        ratios = {}

        # Balance sheet items
        assets = period_data.get("Assets")
        current_assets = period_data.get("AssetsCurrent")
        liabilities = period_data.get("Liabilities")
        current_liabilities = period_data.get("LiabilitiesCurrent")
        equity = period_data.get("StockholdersEquity")

        # Current Ratio
        if current_assets and current_liabilities and current_liabilities > 0:
            ratios["CurrentRatio"] = current_assets / current_liabilities

        # Debt-to-Equity
        long_term_debt = period_data.get("LongTermDebt", 0)
        if equity and equity > 0:
            ratios["DebtToEquity"] = long_term_debt / equity

        # Return on Assets
        net_income = period_data.get("NetIncomeLoss")
        if assets and assets > 0 and net_income:
            ratios["ReturnOnAssets"] = net_income / assets

        # Return on Equity
        if equity and equity > 0 and net_income:
            ratios["ReturnOnEquity"] = net_income / equity

        return ratios

    def save_xml(self, root: ET.Element, output_path: Path) -> bool:
        """
        Save XML to file with pretty formatting.

        Args:
            root: XML Element tree root
            output_path: Path to save XML file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert to string with pretty printing
            xml_string = ET.tostring(root, encoding='unicode')
            dom = minidom.parseString(xml_string)
            pretty_xml = dom.toprettyxml(indent="  ")

            # Remove extra blank lines
            lines = [line for line in pretty_xml.split('\n') if line.strip()]
            pretty_xml = '\n'.join(lines)

            # Write to file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(pretty_xml)

            logger.info(f"XML saved to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save XML: {e}", exc_info=True)
            return False

    def validate_xml(self, root: ET.Element) -> List[str]:
        """
        Validate XML structure and content.

        Args:
            root: XML Element tree root

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check required sections
        required_sections = ["Metadata", "DataQuality", "FinancialMetrics", "AuditTrail"]
        for section in required_sections:
            if root.find(section) is None:
                errors.append(f"Missing required section: {section}")

        # Check metadata
        metadata = root.find("Metadata")
        if metadata is not None:
            required_fields = ["Ticker", "CIK", "EntityName"]
            for field in required_fields:
                if metadata.find(field) is None or not metadata.find(field).text:
                    errors.append(f"Missing or empty metadata field: {field}")

        return errors
