"""
Unit tests for Phase 4: Data Validator

Tests validator.py module functionality including:
- Metric value validation
- YoY growth validation
- Cross-metric validation
- Time series validation
"""

import pytest
from src.validator import MetricValidator, ValidationFlag, FlagLevel


class TestMetricValueValidation:
    """Test individual metric value validation."""

    def test_negative_revenue_flagged(self):
        """Revenue should not be negative."""
        validator = MetricValidator()

        flags = validator.validate_metric_value(
            metric_name="Revenues",
            value=-1000000,
            fiscal_period="FY2025"
        )

        assert len(flags) == 1
        assert flags[0].level == FlagLevel.ERROR
        assert "should be positive" in flags[0].message

    def test_positive_revenue_accepted(self):
        """Positive revenue should pass validation."""
        validator = MetricValidator()

        flags = validator.validate_metric_value(
            metric_name="Revenues",
            value=130500000000,
            fiscal_period="FY2025"
        )

        assert len(flags) == 0

    def test_negative_net_income_allowed(self):
        """Net income can be negative (losses)."""
        validator = MetricValidator()

        flags = validator.validate_metric_value(
            metric_name="NetIncomeLoss",
            value=-500000000,
            fiscal_period="FY2025"
        )

        # Should have 0 ERROR flags (negative is allowed for NetIncomeLoss)
        error_flags = [f for f in flags if f.level == FlagLevel.ERROR]
        assert len(error_flags) == 0

    def test_zero_revenue_flagged(self):
        """Zero revenue should trigger warning."""
        validator = MetricValidator()

        flags = validator.validate_metric_value(
            metric_name="Revenues",
            value=0,
            fiscal_period="FY2025"
        )

        assert len(flags) == 1
        assert flags[0].level == FlagLevel.WARNING
        assert "exactly zero" in flags[0].message

    def test_extreme_value_flagged(self):
        """Unrealistically large values should be flagged."""
        validator = MetricValidator()

        flags = validator.validate_metric_value(
            metric_name="Revenues",
            value=9e15,  # > $1 quadrillion
            fiscal_period="FY2025"
        )

        assert len(flags) >= 1
        error_flags = [f for f in flags if f.level == FlagLevel.ERROR]
        assert len(error_flags) > 0


class TestYoYGrowthValidation:
    """Test year-over-year growth validation."""

    def test_normal_growth_accepted(self):
        """Normal growth rates should pass."""
        validator = MetricValidator()

        flags = validator.validate_yoy_growth(
            metric_name="Revenues",
            current_value=130500000000,
            prior_value=100000000000,
            current_period="FY2025",
            prior_period="FY2024"
        )

        # 30.5% growth is normal, should have no flags
        assert len(flags) == 0

    def test_extreme_growth_flagged(self):
        """Extreme growth >1000% should be flagged as ERROR."""
        validator = MetricValidator()

        flags = validator.validate_yoy_growth(
            metric_name="Revenues",
            current_value=120000000000,
            prior_value=10000000000,
            current_period="FY2025",
            prior_period="FY2024"
        )

        # 1100% growth (>1000% threshold)
        assert len(flags) >= 1
        assert flags[0].level == FlagLevel.ERROR
        assert "Extreme growth" in flags[0].message

    def test_high_growth_warning(self):
        """High growth >500% should trigger warning."""
        validator = MetricValidator()

        flags = validator.validate_yoy_growth(
            metric_name="Revenues",
            current_value=70000000000,
            prior_value=10000000000,
            current_period="FY2025",
            prior_period="FY2024"
        )

        # 600% growth
        assert len(flags) >= 1
        assert flags[0].level == FlagLevel.WARNING
        assert "High growth" in flags[0].message

    def test_extreme_decline_flagged(self):
        """Extreme decline >99% should be flagged as ERROR."""
        validator = MetricValidator()

        flags = validator.validate_yoy_growth(
            metric_name="Revenues",
            current_value=10000000,
            prior_value=10000000000,
            current_period="FY2025",
            prior_period="FY2024"
        )

        # -99.9% decline
        assert len(flags) >= 1
        assert flags[0].level == FlagLevel.ERROR
        assert "Extreme decline" in flags[0].message

    def test_zero_prior_value_handled(self):
        """Should handle zero prior value gracefully."""
        validator = MetricValidator()

        flags = validator.validate_yoy_growth(
            metric_name="Revenues",
            current_value=100000000,
            prior_value=0,
            current_period="FY2025",
            prior_period="FY2024"
        )

        # Can't calculate growth from zero, should return no flags
        assert len(flags) == 0


class TestCrossMetricValidation:
    """Test cross-metric relationship validation."""

    def test_revenue_exceeds_cogs_passes(self):
        """Revenue > Cost of Revenue should pass."""
        validator = MetricValidator()

        metrics = {
            "Revenues": 130500000000,
            "CostOfRevenue": 29050000000
        }

        flags = validator.validate_cross_metrics(metrics, "FY2025")

        # Should have no ERROR flags for this relationship
        error_flags = [f for f in flags if f.level == FlagLevel.ERROR
                      and "exceeds Revenue" in f.message]
        assert len(error_flags) == 0

    def test_cogs_exceeds_revenue_flagged(self):
        """Cost of Revenue > Revenue should be flagged."""
        validator = MetricValidator()

        metrics = {
            "Revenues": 100000000000,
            "CostOfRevenue": 150000000000  # Impossible!
        }

        flags = validator.validate_cross_metrics(metrics, "FY2025")

        assert len(flags) >= 1
        error_flags = [f for f in flags if f.level == FlagLevel.ERROR]
        assert len(error_flags) > 0
        assert any("exceeds Revenue" in f.message for f in flags)

    def test_gross_profit_calculation_checked(self):
        """Gross Profit should equal Revenue - COGS."""
        validator = MetricValidator()

        metrics = {
            "Revenues": 130500000000,
            "CostOfRevenue": 29050000000,
            "GrossProfit": 101450000000  # Correct: 130.5B - 29.05B
        }

        flags = validator.validate_cross_metrics(metrics, "FY2025")

        # Should pass with no warnings about GrossProfit
        gp_flags = [f for f in flags if "GrossProfit" in f.message]
        assert len(gp_flags) == 0

    def test_gross_profit_mismatch_flagged(self):
        """Incorrect Gross Profit calculation should be flagged."""
        validator = MetricValidator()

        metrics = {
            "Revenues": 130500000000,
            "CostOfRevenue": 29050000000,
            "GrossProfit": 80000000000  # Very wrong! Should be ~101.45B
        }

        flags = validator.validate_cross_metrics(metrics, "FY2025")

        # Should flag the mismatch (21% difference)
        gp_flags = [f for f in flags if "Gross" in f.message and "mismatch" in f.message]
        assert len(gp_flags) >= 1

    def test_balance_sheet_equation_checked(self):
        """Assets should equal Liabilities + Equity."""
        validator = MetricValidator()

        metrics = {
            "Assets": 309900000000,
            "Liabilities": 78500000000,
            "StockholdersEquity": 231400000000  # 78.5B + 231.4B = 309.9B ✓
        }

        flags = validator.validate_cross_metrics(metrics, "FY2025")

        # Should pass
        balance_flags = [f for f in flags if "balance" in f.message.lower()]
        assert len(balance_flags) == 0

    def test_balance_sheet_mismatch_flagged(self):
        """Unbalanced balance sheet should be flagged."""
        validator = MetricValidator()

        metrics = {
            "Assets": 309900000000,
            "Liabilities": 100000000000,
            "StockholdersEquity": 200000000000  # Doesn't balance!
        }

        flags = validator.validate_cross_metrics(metrics, "FY2025")

        # Should flag the imbalance
        balance_flags = [f for f in flags if "balance" in f.message.lower()]
        assert len(balance_flags) >= 1

    def test_current_assets_exceed_total_flagged(self):
        """Current Assets > Total Assets should be flagged."""
        validator = MetricValidator()

        metrics = {
            "Assets": 100000000000,
            "AssetsCurrent": 150000000000  # Impossible!
        }

        flags = validator.validate_cross_metrics(metrics, "FY2025")

        assert len(flags) >= 1
        error_flags = [f for f in flags if f.level == FlagLevel.ERROR]
        assert len(error_flags) > 0


class TestTimeSeriesValidation:
    """Test time series consistency validation."""

    def test_no_duplicates_passes(self):
        """Time series with no duplicates should pass."""
        validator = MetricValidator()

        time_series = [
            {"end": "2025-01-26", "val": 130500000000},
            {"end": "2024-01-28", "val": 100000000000},
            {"end": "2023-01-29", "val": 80000000000}
        ]

        flags = validator.validate_time_series("Revenues", time_series)

        assert len(flags) == 0

    def test_duplicate_periods_flagged(self):
        """Duplicate fiscal periods should be flagged."""
        validator = MetricValidator()

        time_series = [
            {"end": "2025-01-26", "val": 130500000000},
            {"end": "2025-01-26", "val": 130500000000},  # Duplicate!
            {"end": "2024-01-28", "val": 100000000000}
        ]

        flags = validator.validate_time_series("Revenues", time_series)

        assert len(flags) >= 1
        assert any("Duplicate" in f.message for f in flags)

    def test_single_data_point_accepted(self):
        """Single data point should not trigger errors."""
        validator = MetricValidator()

        time_series = [
            {"end": "2025-01-26", "val": 130500000000}
        ]

        flags = validator.validate_time_series("Revenues", time_series)

        # Can't validate much with 1 data point, should return 0 flags
        assert len(flags) == 0


class TestFlagSummary:
    """Test flag summary and aggregation."""

    def test_get_flags_summary(self):
        """Test flag summary statistics."""
        validator = MetricValidator()

        # Add some test flags
        validator.flags = [
            ValidationFlag(FlagLevel.ERROR, "Revenues", "Test error"),
            ValidationFlag(FlagLevel.ERROR, "NetIncome", "Another error"),
            ValidationFlag(FlagLevel.WARNING, "Revenues", "Test warning"),
            ValidationFlag(FlagLevel.INFO, "Assets", "Test info")
        ]

        summary = validator.get_flags_summary()

        assert summary["total"] == 4
        assert summary["by_level"]["ERROR"] == 2
        assert summary["by_level"]["WARNING"] == 1
        assert summary["by_level"]["INFO"] == 1
        assert summary["by_level"]["CRITICAL"] == 0
        assert summary["by_metric"]["Revenues"] == 2
        assert summary["by_metric"]["NetIncome"] == 1
        assert summary["by_metric"]["Assets"] == 1

    def test_clear_flags(self):
        """Test clearing all flags."""
        validator = MetricValidator()

        validator.flags = [
            ValidationFlag(FlagLevel.ERROR, "Revenues", "Test"),
            ValidationFlag(FlagLevel.WARNING, "NetIncome", "Test")
        ]

        assert len(validator.flags) == 2

        validator.clear_flags()

        assert len(validator.flags) == 0
