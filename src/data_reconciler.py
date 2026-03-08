"""
Data Reconciler for SEC Filing Parser - Phase 4

This module reconciles data from multiple sources (XBRL vs PDF),
validates quality, and generates comprehensive quality reports.

Author: SEC Filing Parser Team
Date: March 7, 2026
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json

from src.validator import MetricValidator, ValidationFlag, FlagLevel

logger = logging.getLogger(__name__)


class DataReconciler:
    """
    Reconciles and validates financial data from XBRL extraction.

    This class:
    - Validates individual metric values
    - Checks year-over-year growth rates
    - Performs cross-metric validation
    - Generates quality scores (0-100)
    - Produces comprehensive validation reports
    """

    def __init__(self):
        self.validator = MetricValidator()
        self.validation_report = {
            "validation_date": datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
            "flags": [],
            "quality_score": 0,
            "metrics_validated": 0,
            "checks_performed": []
        }

    def reconcile_and_validate(self, xbrl_metrics: Dict,
                                ticker: str) -> Dict:
        """
        Main reconciliation and validation pipeline.

        Args:
            xbrl_metrics: XBRL metrics dictionary from Phase 3
            ticker: Stock ticker symbol

        Returns:
            Dictionary with validation results and quality score
        """
        logger.info(f"Starting data reconciliation for {ticker}...")

        self.validator.clear_flags()
        self.validation_report["ticker"] = ticker
        self.validation_report["cik"] = xbrl_metrics.get("cik")
        self.validation_report["entity_name"] = xbrl_metrics.get("entity_name")

        metrics = xbrl_metrics.get("metrics", {})

        # Step 1: Validate individual metric values
        logger.info("Validating individual metric values...")
        self._validate_metric_values(metrics)
        self.validation_report["checks_performed"].append("metric_value_validation")

        # Step 2: Validate year-over-year growth rates
        logger.info("Validating YoY growth rates...")
        self._validate_growth_rates(metrics)
        self.validation_report["checks_performed"].append("yoy_growth_validation")

        # Step 3: Cross-metric validation (for each fiscal period)
        logger.info("Performing cross-metric validation...")
        self._cross_metric_validation(metrics)
        self.validation_report["checks_performed"].append("cross_metric_validation")

        # Step 4: Time series consistency
        logger.info("Validating time series consistency...")
        self._validate_time_series(metrics)
        self.validation_report["checks_performed"].append("time_series_validation")

        # Step 5: Calculate overall quality score
        logger.info("Calculating data quality score...")
        quality_score = self._calculate_quality_score()
        self.validation_report["quality_score"] = quality_score

        # Step 6: Compile validation report
        self.validation_report["flags"] = [f.to_dict() for f in self.validator.flags]
        self.validation_report["metrics_validated"] = len(metrics)
        self.validation_report["flag_summary"] = self.validator.get_flags_summary()

        logger.info(f"Validation complete. Quality score: {quality_score}/100")
        logger.info(f"Flags: {len(self.validator.flags)} total")

        return self.validation_report

    def _validate_metric_values(self, metrics: Dict):
        """Validate individual metric values for reasonableness."""
        for metric_key, metric_data in metrics.items():
            metric_name = metric_data.get("name")
            values = metric_data.get("values", [])

            for value_entry in values:
                value = value_entry.get("val")
                fiscal_period = value_entry.get("fp", "")
                fiscal_year = value_entry.get("fy", "")
                period_id = f"{fiscal_period}_{fiscal_year}"

                if value is not None:
                    flags = self.validator.validate_metric_value(
                        metric_name, value, period_id
                    )
                    self.validator.flags.extend(flags)

    def _validate_growth_rates(self, metrics: Dict):
        """Validate year-over-year growth rates."""
        for metric_key, metric_data in metrics.items():
            metric_name = metric_data.get("name")
            values = metric_data.get("values", [])

            # Need at least 2 data points for YoY comparison
            if len(values) < 2:
                continue

            # Sort by fiscal period end date
            sorted_values = sorted(values, key=lambda x: x.get("end", ""))

            # Compare consecutive periods
            for i in range(1, len(sorted_values)):
                current = sorted_values[i]
                prior = sorted_values[i - 1]

                current_val = current.get("val")
                prior_val = prior.get("val")

                if current_val is not None and prior_val is not None:
                    current_period = f"{current.get('fp')}_{current.get('fy')}"
                    prior_period = f"{prior.get('fp')}_{prior.get('fy')}"

                    flags = self.validator.validate_yoy_growth(
                        metric_name, current_val, prior_val,
                        current_period, prior_period
                    )
                    self.validator.flags.extend(flags)

    def _cross_metric_validation(self, metrics: Dict):
        """Perform cross-metric validation for each fiscal period."""
        # Organize metrics by fiscal period
        periods = {}

        for metric_key, metric_data in metrics.items():
            metric_name = metric_data.get("name")
            values = metric_data.get("values", [])

            for value_entry in values:
                period_end = value_entry.get("end")
                value = value_entry.get("val")

                if period_end and value is not None:
                    if period_end not in periods:
                        periods[period_end] = {}
                    periods[period_end][metric_name] = value

        # Validate each period's metrics
        for period_end, period_metrics in periods.items():
            flags = self.validator.validate_cross_metrics(period_metrics, period_end)
            self.validator.flags.extend(flags)

    def _validate_time_series(self, metrics: Dict):
        """Validate time series consistency for each metric."""
        for metric_key, metric_data in metrics.items():
            metric_name = metric_data.get("name")
            values = metric_data.get("values", [])

            flags = self.validator.validate_time_series(metric_name, values)
            self.validator.flags.extend(flags)

    def _calculate_quality_score(self) -> int:
        """
        Calculate overall data quality score (0-100).

        Scoring:
        - Start at 100
        - Deduct points for each flag based on severity:
          - INFO: -0.5 points
          - WARNING: -1 point
          - ERROR: -5 points
          - CRITICAL: -20 points
        - Floor at 0

        Returns:
            Quality score (0-100)
        """
        score = 100.0

        flag_summary = self.validator.get_flags_summary()

        # Deduct points based on flag severity
        score -= flag_summary["by_level"]["INFO"] * 0.5
        score -= flag_summary["by_level"]["WARNING"] * 1.0
        score -= flag_summary["by_level"]["ERROR"] * 5.0
        score -= flag_summary["by_level"]["CRITICAL"] * 20.0

        # Floor at 0
        score = max(0, score)

        return int(score)

    def save_validation_report(self, output_path: str):
        """
        Save validation report to JSON file.

        Args:
            output_path: Path to save the report
        """
        with open(output_path, 'w') as f:
            json.dump(self.validation_report, f, indent=2)

        logger.info(f"Validation report saved to {output_path}")

    def get_critical_flags(self) -> List[Dict]:
        """
        Get only critical and error-level flags.

        Returns:
            List of critical/error flags
        """
        critical_flags = [
            f.to_dict() for f in self.validator.flags
            if f.level in (FlagLevel.CRITICAL, FlagLevel.ERROR)
        ]
        return critical_flags

    def get_warnings(self) -> List[Dict]:
        """
        Get warning-level flags.

        Returns:
            List of warning flags
        """
        warnings = [
            f.to_dict() for f in self.validator.flags
            if f.level == FlagLevel.WARNING
        ]
        return warnings

    def has_critical_issues(self) -> bool:
        """
        Check if there are any critical issues.

        Returns:
            True if critical or error flags exist
        """
        for flag in self.validator.flags:
            if flag.level in (FlagLevel.CRITICAL, FlagLevel.ERROR):
                return True
        return False

    def print_summary(self):
        """Print a human-readable validation summary."""
        summary = self.validator.get_flags_summary()

        print("\n" + "=" * 70)
        print("DATA VALIDATION SUMMARY")
        print("=" * 70)
        print(f"Ticker:          {self.validation_report.get('ticker')}")
        print(f"Entity:          {self.validation_report.get('entity_name')}")
        print(f"Quality Score:   {self.validation_report.get('quality_score')}/100")
        print(f"Metrics Checked: {self.validation_report.get('metrics_validated')}")
        print(f"\nFlags Summary:")
        print(f"  CRITICAL:      {summary['by_level']['CRITICAL']}")
        print(f"  ERROR:         {summary['by_level']['ERROR']}")
        print(f"  WARNING:       {summary['by_level']['WARNING']}")
        print(f"  INFO:          {summary['by_level']['INFO']}")
        print(f"  TOTAL:         {summary['total']}")

        if self.has_critical_issues():
            print("\n⚠️  CRITICAL ISSUES FOUND - MANUAL REVIEW REQUIRED")
            critical = self.get_critical_flags()
            for i, flag in enumerate(critical[:5], 1):  # Show first 5
                print(f"\n  {i}. {flag['metric']}")
                print(f"     {flag['message']}")
                if flag.get('details'):
                    print(f"     Details: {flag['details']}")
        else:
            print("\n✅ No critical issues found")

        print("=" * 70 + "\n")
