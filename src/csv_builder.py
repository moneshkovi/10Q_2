"""
CSV Builder for SEC Filing Parser - Phase 5 Extension

This module generates CSV output files from financial data for easy
analysis in Excel, pandas, or other tools.

CSV outputs:
- Financial metrics (wide format: periods as columns)
- Calculated metrics (margins and ratios)
- Validation summary

Author: SEC Filing Parser Team
Date: March 7, 2026
"""

import logging
import csv
from typing import Dict, List
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class CSVBuilder:
    """
    Builds CSV files from financial data.

    Creates three CSV files:
    1. metrics.csv - All financial metrics in wide format
    2. calculated_metrics.csv - Margins and ratios
    3. validation_summary.csv - Data quality report
    """

    def __init__(self):
        """Initialize CSV Builder."""
        self.version = "1.0"

    def export_to_csv(self, ticker: str, xbrl_metrics: Dict,
                      validation_report: Dict, output_dir: Path) -> Dict[str, bool]:
        """
        Export all data to CSV files.

        Args:
            ticker: Stock ticker symbol
            xbrl_metrics: XBRL metrics from Phase 3
            validation_report: Validation results from Phase 4
            output_dir: Directory to save CSV files

        Returns:
            Dictionary with success status for each file
        """
        results = {}

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Export financial metrics
        metrics_path = output_dir / f"{ticker.upper()}_metrics.csv"
        results['metrics'] = self._export_financial_metrics(
            xbrl_metrics, metrics_path
        )

        # Export calculated metrics
        calc_path = output_dir / f"{ticker.upper()}_calculated_metrics.csv"
        results['calculated'] = self._export_calculated_metrics(
            xbrl_metrics, calc_path
        )

        # Export validation summary
        validation_path = output_dir / f"{ticker.upper()}_validation_summary.csv"
        results['validation'] = self._export_validation_summary(
            validation_report, validation_path
        )

        return results

    def _export_financial_metrics(self, xbrl_metrics: Dict,
                                   output_path: Path) -> bool:
        """
        Export financial metrics to CSV in wide format.

        Format:
        Metric | Unit | 2026-Q1 | 2025-Q4 | 2025-Q3 | ...
        Revenue | USD  | 130.5B  | 100.0B  | 90.0B   | ...
        """
        try:
            metrics = xbrl_metrics.get("metrics", {})

            # Collect all unique periods
            all_periods = set()
            for metric_data in metrics.values():
                for value_entry in metric_data.get("values", []):
                    period_key = f"{value_entry.get('end')}_{value_entry.get('form', '')}"
                    all_periods.add(period_key)

            # Sort periods (most recent first)
            sorted_periods = sorted(all_periods, reverse=True)

            # Write CSV
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Header row
                header = ['Metric', 'Unit', 'Confidence'] + sorted_periods
                writer.writerow(header)

                # Data rows
                for metric_key in sorted(metrics.keys()):
                    metric_data = metrics[metric_key]
                    metric_name = metric_data.get("name")
                    unit = metric_data.get("unit", "")
                    confidence = metric_data.get("confidence", 0)

                    # Build period values map
                    period_values = {}
                    for value_entry in metric_data.get("values", []):
                        period_key = f"{value_entry.get('end')}_{value_entry.get('form', '')}"
                        period_values[period_key] = value_entry.get("val")

                    # Build row
                    row = [metric_name, unit, confidence]
                    for period in sorted_periods:
                        value = period_values.get(period, "")
                        if value != "":
                            # Format large numbers
                            if isinstance(value, (int, float)):
                                if abs(value) >= 1e9:
                                    row.append(f"{value/1e9:.2f}B")
                                elif abs(value) >= 1e6:
                                    row.append(f"{value/1e6:.2f}M")
                                else:
                                    row.append(f"{value:.2f}")
                            else:
                                row.append(value)
                        else:
                            row.append("")

                    writer.writerow(row)

            logger.info(f"Financial metrics CSV saved to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export financial metrics CSV: {e}", exc_info=True)
            return False

    def _export_calculated_metrics(self, xbrl_metrics: Dict,
                                    output_path: Path) -> bool:
        """
        Export calculated metrics (margins and ratios) to CSV.

        Format:
        Metric Type | Metric | Value | Percentage
        Margin      | Gross  | 0.7107 | 71.07%
        Ratio       | Current| 3.91   | N/A
        """
        try:
            metrics = xbrl_metrics.get("metrics", {})

            # Get latest annual period data
            latest_annual = self._get_latest_annual_period(metrics)

            if not latest_annual:
                logger.warning("No annual period data for calculated metrics")
                return False

            # Calculate metrics
            margins = self._calculate_margins(latest_annual)
            ratios = self._calculate_ratios(latest_annual)

            # Write CSV
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Header
                writer.writerow(['Type', 'Metric', 'Value', 'Display', 'Period'])

                period_end = latest_annual.get("period_end", "Unknown")

                # Write margins
                for name, value in margins.items():
                    writer.writerow([
                        'Margin',
                        name.replace('Margin', ' Margin'),
                        f"{value:.4f}",
                        f"{value*100:.2f}%",
                        period_end
                    ])

                # Write ratios
                for name, value in ratios.items():
                    display_name = name.replace('Current', 'Current ') \
                                      .replace('DebtTo', 'Debt-to-') \
                                      .replace('ReturnOn', 'Return on ')
                    writer.writerow([
                        'Ratio',
                        display_name,
                        f"{value:.4f}",
                        f"{value:.2f}",
                        period_end
                    ])

            logger.info(f"Calculated metrics CSV saved to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export calculated metrics CSV: {e}", exc_info=True)
            return False

    def _export_validation_summary(self, validation_report: Dict,
                                    output_path: Path) -> bool:
        """
        Export validation summary to CSV.

        Includes:
        - Overall quality metrics
        - Flag counts by level
        - Top critical issues
        """
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Overall metrics
                writer.writerow(['VALIDATION SUMMARY'])
                writer.writerow([])
                writer.writerow(['Metric', 'Value'])
                writer.writerow(['Ticker', validation_report.get('ticker', '')])
                writer.writerow(['Entity', validation_report.get('entity_name', '')])
                writer.writerow(['Quality Score', validation_report.get('quality_score', 0)])
                writer.writerow(['Metrics Validated', validation_report.get('metrics_validated', 0)])
                writer.writerow([])

                # Flag summary
                writer.writerow(['FLAG SUMMARY'])
                writer.writerow([])
                writer.writerow(['Level', 'Count'])

                flag_summary = validation_report.get('flag_summary', {})
                by_level = flag_summary.get('by_level', {})

                writer.writerow(['Critical', by_level.get('CRITICAL', 0)])
                writer.writerow(['Error', by_level.get('ERROR', 0)])
                writer.writerow(['Warning', by_level.get('WARNING', 0)])
                writer.writerow(['Info', by_level.get('INFO', 0)])
                writer.writerow(['TOTAL', flag_summary.get('total', 0)])
                writer.writerow([])

                # Critical issues
                flags = validation_report.get('flags', [])
                critical_flags = [
                    f for f in flags
                    if f.get('level') in ['CRITICAL', 'ERROR']
                ]

                if critical_flags:
                    writer.writerow(['CRITICAL/ERROR ISSUES'])
                    writer.writerow([])
                    writer.writerow(['Level', 'Metric', 'Message', 'Value'])

                    for flag in critical_flags[:20]:  # Limit to 20
                        writer.writerow([
                            flag.get('level', ''),
                            flag.get('metric', ''),
                            flag.get('message', ''),
                            flag.get('value', '')
                        ])

                writer.writerow([])
                writer.writerow(['Export Date', datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')])

            logger.info(f"Validation summary CSV saved to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export validation summary CSV: {e}", exc_info=True)
            return False

    def _get_latest_annual_period(self, metrics: Dict) -> Dict:
        """Extract the most recent annual (10-K) period data."""
        annual_periods = {}

        for metric_data in metrics.values():
            for value_entry in metric_data.get("values", []):
                form = value_entry.get("form", "")
                if form == "10-K":
                    period_end = value_entry.get("end")
                    if period_end not in annual_periods:
                        annual_periods[period_end] = {"period_end": period_end}

                    metric_name = metric_data.get("name")
                    annual_periods[period_end][metric_name] = value_entry.get("val")

        if not annual_periods:
            return {}

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

        assets = period_data.get("Assets")
        current_assets = period_data.get("AssetsCurrent")
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

    def create_pivot_table_csv(self, ticker: str, xbrl_metrics: Dict,
                               output_path: Path) -> bool:
        """
        Create a pivot-table friendly CSV format.

        Format:
        Period | Metric | Value | Unit
        2026-Q1 | Revenue | 130500000000 | USD
        2026-Q1 | NetIncome | 60922000000 | USD
        """
        try:
            metrics = xbrl_metrics.get("metrics", {})

            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Header
                writer.writerow(['Period', 'Form', 'Filing_Date', 'Metric', 'Value', 'Unit', 'Confidence'])

                # Collect all data
                rows = []
                for metric_key, metric_data in metrics.items():
                    metric_name = metric_data.get("name")
                    unit = metric_data.get("unit", "")
                    confidence = metric_data.get("confidence", 0)

                    for value_entry in metric_data.get("values", []):
                        rows.append([
                            value_entry.get("end", ""),
                            value_entry.get("form", ""),
                            value_entry.get("filed", ""),
                            metric_name,
                            value_entry.get("val", ""),
                            unit,
                            confidence
                        ])

                # Sort by period (most recent first)
                rows.sort(key=lambda x: x[0], reverse=True)

                # Write rows
                for row in rows:
                    writer.writerow(row)

            logger.info(f"Pivot table CSV saved to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to create pivot table CSV: {e}", exc_info=True)
            return False
