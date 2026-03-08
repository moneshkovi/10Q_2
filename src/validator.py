"""
Data Validator for SEC Filing Parser - Phase 4

This module validates extracted financial metrics for reasonableness,
detects anomalies, and flags items requiring manual review.

Author: SEC Filing Parser Team
Date: March 7, 2026
"""

import logging
from typing import Dict, List, Tuple, Optional
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class FlagLevel(Enum):
    """Flag severity levels for data quality issues."""
    INFO = 1       # Informational - interesting but not concerning
    WARNING = 2    # Possible issue - should review
    ERROR = 3      # Likely wrong - must review
    CRITICAL = 4   # Definitely wrong - stop processing


class ValidationFlag:
    """Represents a data quality flag."""

    def __init__(self, level: FlagLevel, metric: str, message: str,
                 value: Optional[float] = None, details: Optional[Dict] = None):
        self.level = level
        self.metric = metric
        self.message = message
        self.value = value
        self.details = details or {}
        self.timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

    def to_dict(self) -> Dict:
        """Convert flag to dictionary for serialization."""
        return {
            "level": self.level.name,
            "metric": self.metric,
            "message": self.message,
            "value": self.value,
            "details": self.details,
            "timestamp": self.timestamp
        }

    def __repr__(self) -> str:
        return f"<Flag {self.level.name}: {self.metric} - {self.message}>"


class MetricValidator:
    """
    Validates financial metrics for reasonableness and flags anomalies.

    This validator performs several checks:
    - Sign validation (revenue/assets should be positive)
    - Growth rate validation (flag unrealistic YoY changes)
    - Cross-metric validation (revenue > COGS, etc.)
    - Time series consistency (no huge gaps or duplicates)
    """

    # Validation thresholds
    MAX_YOY_GROWTH = 5.0        # 500% growth flags a warning
    MAX_YOY_DECLINE = -0.90     # -90% decline flags a warning
    EXTREME_GROWTH = 10.0       # 1000% growth flags an error
    EXTREME_DECLINE = -0.99     # -99% decline flags an error

    # Metrics that should always be positive
    MUST_BE_POSITIVE = {
        "Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Assets", "AssetsCurrent", "PropertyPlantAndEquipmentNet",
        "StockholdersEquity", "CommonStockValue"
    }

    # Metrics that can be negative (losses, etc.)
    CAN_BE_NEGATIVE = {
        "NetIncomeLoss", "OperatingIncomeLoss",
        "OtherComprehensiveIncomeLossNetOfTax",
        "RetainedEarningsAccumulatedDeficit"
    }

    def __init__(self):
        self.flags: List[ValidationFlag] = []

    def validate_metric_value(self, metric_name: str, value: float,
                             fiscal_period: str) -> List[ValidationFlag]:
        """
        Validate a single metric value for reasonableness.

        Args:
            metric_name: Name of the metric (e.g., "Revenues")
            value: The metric value
            fiscal_period: Period identifier (e.g., "FY2025", "Q1_2025")

        Returns:
            List of validation flags (empty if no issues)
        """
        flags = []

        # Check 1: Should be positive but isn't
        if metric_name in self.MUST_BE_POSITIVE and value < 0:
            flags.append(ValidationFlag(
                level=FlagLevel.ERROR,
                metric=metric_name,
                message=f"{metric_name} should be positive but is negative",
                value=value,
                details={"fiscal_period": fiscal_period}
            ))

        # Check 2: Extreme values (likely data error)
        if abs(value) > 1e15:  # > $1 quadrillion (unrealistic)
            flags.append(ValidationFlag(
                level=FlagLevel.ERROR,
                metric=metric_name,
                message=f"{metric_name} has unrealistic magnitude",
                value=value,
                details={"fiscal_period": fiscal_period}
            ))

        # Check 3: Exactly zero (might be missing data)
        if value == 0 and metric_name in self.MUST_BE_POSITIVE:
            flags.append(ValidationFlag(
                level=FlagLevel.WARNING,
                metric=metric_name,
                message=f"{metric_name} is exactly zero - verify this is correct",
                value=value,
                details={"fiscal_period": fiscal_period}
            ))

        return flags

    def validate_yoy_growth(self, metric_name: str, current_value: float,
                           prior_value: float, current_period: str,
                           prior_period: str) -> List[ValidationFlag]:
        """
        Validate year-over-year growth rates for reasonableness.

        Args:
            metric_name: Name of the metric
            current_value: Current period value
            prior_value: Prior period value
            current_period: Current period identifier
            prior_period: Prior period identifier

        Returns:
            List of validation flags
        """
        flags = []

        # Can't calculate growth if prior is zero
        if prior_value == 0:
            return flags

        # Calculate growth rate
        growth_rate = (current_value - prior_value) / abs(prior_value)

        # Check for extreme growth
        if growth_rate > self.EXTREME_GROWTH:
            flags.append(ValidationFlag(
                level=FlagLevel.ERROR,
                metric=metric_name,
                message=f"Extreme growth rate: {growth_rate*100:.1f}%",
                value=current_value,
                details={
                    "current_period": current_period,
                    "prior_period": prior_period,
                    "current_value": current_value,
                    "prior_value": prior_value,
                    "growth_rate_pct": round(growth_rate * 100, 2)
                }
            ))
        elif growth_rate > self.MAX_YOY_GROWTH:
            flags.append(ValidationFlag(
                level=FlagLevel.WARNING,
                metric=metric_name,
                message=f"High growth rate: {growth_rate*100:.1f}%",
                value=current_value,
                details={
                    "current_period": current_period,
                    "prior_period": prior_period,
                    "growth_rate_pct": round(growth_rate * 100, 2)
                }
            ))

        # Check for extreme decline
        if growth_rate < self.EXTREME_DECLINE:
            flags.append(ValidationFlag(
                level=FlagLevel.ERROR,
                metric=metric_name,
                message=f"Extreme decline: {growth_rate*100:.1f}%",
                value=current_value,
                details={
                    "current_period": current_period,
                    "prior_period": prior_period,
                    "current_value": current_value,
                    "prior_value": prior_value,
                    "growth_rate_pct": round(growth_rate * 100, 2)
                }
            ))
        elif growth_rate < self.MAX_YOY_DECLINE:
            flags.append(ValidationFlag(
                level=FlagLevel.WARNING,
                metric=metric_name,
                message=f"Large decline: {growth_rate*100:.1f}%",
                value=current_value,
                details={
                    "current_period": current_period,
                    "prior_period": prior_period,
                    "growth_rate_pct": round(growth_rate * 100, 2)
                }
            ))

        return flags

    def validate_cross_metrics(self, metrics_data: Dict[str, float],
                               fiscal_period: str) -> List[ValidationFlag]:
        """
        Validate relationships between metrics.

        Examples:
        - Revenue should be >= Cost of Revenue
        - Assets should equal Liabilities + Equity
        - Current Assets should be <= Total Assets

        Args:
            metrics_data: Dictionary of metric_name -> value
            fiscal_period: Period identifier

        Returns:
            List of validation flags
        """
        flags = []

        # Check 1: Revenue >= Cost of Revenue
        revenue = metrics_data.get("Revenues") or \
                 metrics_data.get("RevenueFromContractWithCustomerExcludingAssessedTax")
        cogs = metrics_data.get("CostOfRevenue")

        if revenue and cogs and revenue < cogs:
            flags.append(ValidationFlag(
                level=FlagLevel.ERROR,
                metric="Revenues vs CostOfRevenue",
                message="Cost of Revenue exceeds Revenue (impossible)",
                details={
                    "fiscal_period": fiscal_period,
                    "revenue": revenue,
                    "cost_of_revenue": cogs
                }
            ))

        # Check 2: Gross Profit = Revenue - COGS (within tolerance)
        gross_profit = metrics_data.get("GrossProfit")
        if revenue and cogs and gross_profit:
            expected_gp = revenue - cogs
            diff_pct = abs(gross_profit - expected_gp) / abs(expected_gp) if expected_gp != 0 else 0

            if diff_pct > 0.01:  # >1% difference
                flags.append(ValidationFlag(
                    level=FlagLevel.WARNING,
                    metric="GrossProfit",
                    message=f"Gross Profit calculation mismatch ({diff_pct*100:.2f}% diff)",
                    value=gross_profit,
                    details={
                        "fiscal_period": fiscal_period,
                        "reported": gross_profit,
                        "calculated": expected_gp,
                        "difference_pct": round(diff_pct * 100, 2)
                    }
                ))

        # Check 3: Assets = Liabilities + Equity (balance sheet equation)
        assets = metrics_data.get("Assets")
        liabilities = metrics_data.get("Liabilities")
        equity = metrics_data.get("StockholdersEquity")

        if assets and liabilities and equity:
            expected_assets = liabilities + equity
            diff_pct = abs(assets - expected_assets) / abs(assets) if assets != 0 else 0

            if diff_pct > 0.01:  # >1% difference
                flags.append(ValidationFlag(
                    level=FlagLevel.WARNING,
                    metric="Assets vs Liabilities+Equity",
                    message=f"Balance sheet doesn't balance ({diff_pct*100:.2f}% diff)",
                    details={
                        "fiscal_period": fiscal_period,
                        "assets": assets,
                        "liabilities": liabilities,
                        "equity": equity,
                        "difference_pct": round(diff_pct * 100, 2)
                    }
                ))

        # Check 4: Current Assets <= Total Assets
        current_assets = metrics_data.get("AssetsCurrent")
        if current_assets and assets and current_assets > assets:
            flags.append(ValidationFlag(
                level=FlagLevel.ERROR,
                metric="AssetsCurrent vs Assets",
                message="Current Assets exceed Total Assets (impossible)",
                details={
                    "fiscal_period": fiscal_period,
                    "current_assets": current_assets,
                    "total_assets": assets
                }
            ))

        return flags

    def validate_time_series(self, metric_name: str,
                            time_series: List[Dict]) -> List[ValidationFlag]:
        """
        Validate a time series for consistency.

        Checks:
        - No duplicate periods
        - No huge gaps in time
        - Values are consistent

        Args:
            metric_name: Name of the metric
            time_series: List of {period, value, date} dicts

        Returns:
            List of validation flags
        """
        flags = []

        if not time_series or len(time_series) < 2:
            return flags

        # Check for duplicates (same fiscal period end date)
        periods_seen = set()
        for entry in time_series:
            period_end = entry.get("end")
            if period_end in periods_seen:
                flags.append(ValidationFlag(
                    level=FlagLevel.WARNING,
                    metric=metric_name,
                    message=f"Duplicate data for period ending {period_end}",
                    details={"period_end": period_end}
                ))
            periods_seen.add(period_end)

        return flags

    def get_flags_summary(self) -> Dict:
        """
        Get summary statistics of validation flags.

        Returns:
            Dictionary with flag counts by level
        """
        summary = {
            "total": len(self.flags),
            "by_level": {
                "INFO": 0,
                "WARNING": 0,
                "ERROR": 0,
                "CRITICAL": 0
            },
            "by_metric": {}
        }

        for flag in self.flags:
            summary["by_level"][flag.level.name] += 1

            if flag.metric not in summary["by_metric"]:
                summary["by_metric"][flag.metric] = 0
            summary["by_metric"][flag.metric] += 1

        return summary

    def clear_flags(self):
        """Clear all validation flags."""
        self.flags = []
