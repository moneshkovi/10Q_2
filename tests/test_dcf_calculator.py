"""Tests for DCF Calculator - Phase 7

Tests for DCF valuation model including FCF calculation, WACC,
terminal value, and sensitivity analysis.

Author: SEC Filing Parser Team
Date: March 2026
"""

import unittest
import tempfile
from pathlib import Path

from src.dcf_calculator import DCFCalculator


def build_mock_xbrl_metrics():
    """Build mock XBRL metrics simulating real SEC data for testing."""
    return {
        "entity_name": "TEST CORP",
        "metrics": {
            "Revenues:USD": {
                "name": "Revenues",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {"val": 130000000000, "end": "2026-01-25", "form": "10-K", "filed": "2026-02-25"},
                    {"val": 100000000000, "end": "2025-01-26", "form": "10-K", "filed": "2025-02-26"},
                    {"val": 70000000000, "end": "2024-01-28", "form": "10-K", "filed": "2024-02-21"},
                    {"val": 50000000000, "end": "2023-01-29", "form": "10-K", "filed": "2023-02-22"},
                    {"val": 40000000000, "end": "2022-01-30", "form": "10-K", "filed": "2022-02-23"},
                ],
            },
            "OperatingIncomeLoss:USD": {
                "name": "OperatingIncomeLoss",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {"val": 78000000000, "end": "2026-01-25", "form": "10-K", "filed": "2026-02-25"},
                    {"val": 55000000000, "end": "2025-01-26", "form": "10-K", "filed": "2025-02-26"},
                    {"val": 30000000000, "end": "2024-01-28", "form": "10-K", "filed": "2024-02-21"},
                    {"val": 18000000000, "end": "2023-01-29", "form": "10-K", "filed": "2023-02-22"},
                    {"val": 12000000000, "end": "2022-01-30", "form": "10-K", "filed": "2022-02-23"},
                ],
            },
            "NetIncomeLoss:USD": {
                "name": "NetIncomeLoss",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {"val": 65000000000, "end": "2026-01-25", "form": "10-K", "filed": "2026-02-25"},
                    {"val": 45000000000, "end": "2025-01-26", "form": "10-K", "filed": "2025-02-26"},
                    {"val": 25000000000, "end": "2024-01-28", "form": "10-K", "filed": "2024-02-21"},
                ],
            },
            "GrossProfit:USD": {
                "name": "GrossProfit",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {"val": 93000000000, "end": "2026-01-25", "form": "10-K", "filed": "2026-02-25"},
                    {"val": 70000000000, "end": "2025-01-26", "form": "10-K", "filed": "2025-02-26"},
                ],
            },
            "DepreciationDepletionAndAmortization:USD": {
                "name": "DepreciationDepletionAndAmortization",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {"val": 4000000000, "end": "2026-01-25", "form": "10-K", "filed": "2026-02-25"},
                    {"val": 3000000000, "end": "2025-01-26", "form": "10-K", "filed": "2025-02-26"},
                    {"val": 2500000000, "end": "2024-01-28", "form": "10-K", "filed": "2024-02-21"},
                ],
            },
            "PaymentsToAcquirePropertyPlantAndEquipment:USD": {
                "name": "PaymentsToAcquirePropertyPlantAndEquipment",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {"val": 8000000000, "end": "2026-01-25", "form": "10-K", "filed": "2026-02-25"},
                    {"val": 5000000000, "end": "2025-01-26", "form": "10-K", "filed": "2025-02-26"},
                    {"val": 3000000000, "end": "2024-01-28", "form": "10-K", "filed": "2024-02-21"},
                ],
            },
            "IncomeTaxExpenseBenefit:USD": {
                "name": "IncomeTaxExpenseBenefit",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {"val": 12000000000, "end": "2026-01-25", "form": "10-K", "filed": "2026-02-25"},
                    {"val": 8000000000, "end": "2025-01-26", "form": "10-K", "filed": "2025-02-26"},
                ],
            },
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest:USD": {
                "name": "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {"val": 77000000000, "end": "2026-01-25", "form": "10-K", "filed": "2026-02-25"},
                    {"val": 53000000000, "end": "2025-01-26", "form": "10-K", "filed": "2025-02-26"},
                ],
            },
            "Assets:USD": {
                "name": "Assets",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {"val": 300000000000, "end": "2026-01-25", "form": "10-K", "filed": "2026-02-25"},
                ],
            },
            "AssetsCurrent:USD": {
                "name": "AssetsCurrent",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {"val": 60000000000, "end": "2026-01-25", "form": "10-K", "filed": "2026-02-25"},
                    {"val": 50000000000, "end": "2025-01-26", "form": "10-K", "filed": "2025-02-26"},
                ],
            },
            "LiabilitiesCurrent:USD": {
                "name": "LiabilitiesCurrent",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {"val": 15000000000, "end": "2026-01-25", "form": "10-K", "filed": "2026-02-25"},
                    {"val": 12000000000, "end": "2025-01-26", "form": "10-K", "filed": "2025-02-26"},
                ],
            },
            "CashAndCashEquivalentsAtCarryingValue:USD": {
                "name": "CashAndCashEquivalentsAtCarryingValue",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {"val": 30000000000, "end": "2026-01-25", "form": "10-K", "filed": "2026-02-25"},
                    {"val": 25000000000, "end": "2025-01-26", "form": "10-K", "filed": "2025-02-26"},
                ],
            },
            "LongTermDebt:USD": {
                "name": "LongTermDebt",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {"val": 10000000000, "end": "2026-01-25", "form": "10-K", "filed": "2026-02-25"},
                ],
            },
            "StockholdersEquity:USD": {
                "name": "StockholdersEquity",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {"val": 85000000000, "end": "2026-01-25", "form": "10-K", "filed": "2026-02-25"},
                ],
            },
            "WeightedAverageNumberOfDilutedSharesOutstanding:shares": {
                "name": "WeightedAverageNumberOfDilutedSharesOutstanding",
                "unit": "shares",
                "confidence": 100.0,
                "values": [
                    {"val": 25000000000, "end": "2026-01-25", "form": "10-K", "filed": "2026-02-25"},
                ],
            },
            "InterestExpense:USD": {
                "name": "InterestExpense",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {"val": 500000000, "end": "2026-01-25", "form": "10-K", "filed": "2026-02-25"},
                ],
            },
            "NetCashProvidedByUsedInOperatingActivities:USD": {
                "name": "NetCashProvidedByUsedInOperatingActivities",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {"val": 70000000000, "end": "2026-01-25", "form": "10-K", "filed": "2026-02-25"},
                    {"val": 50000000000, "end": "2025-01-26", "form": "10-K", "filed": "2025-02-26"},
                ],
            },
        },
    }


class TestDCFHistoricals(unittest.TestCase):
    """Test historical data extraction."""

    def setUp(self):
        self.calc = DCFCalculator()
        self.metrics = build_mock_xbrl_metrics()

    def test_extract_historicals(self):
        """Test extraction of annual periods from XBRL data."""
        historicals = self.calc._extract_historicals(self.metrics)
        self.assertGreaterEqual(len(historicals), 4)
        # Most recent first
        self.assertEqual(historicals[0]["period_end"], "2026-01-25")

    def test_historicals_contain_revenue(self):
        """Test that revenue is extracted correctly."""
        historicals = self.calc._extract_historicals(self.metrics)
        self.assertEqual(historicals[0].get("Revenues"), 130000000000)


class TestDCFFreeCashFlow(unittest.TestCase):
    """Test FCF calculation."""

    def setUp(self):
        self.calc = DCFCalculator()
        self.metrics = build_mock_xbrl_metrics()

    def test_calculate_historical_fcf(self):
        """Test historical FCF calculation."""
        historicals = self.calc._extract_historicals(self.metrics)
        fcf_data = self.calc._calculate_historical_fcf(historicals)
        self.assertGreater(len(fcf_data), 0)

    def test_fcf_components(self):
        """Test that FCF contains all expected components."""
        historicals = self.calc._extract_historicals(self.metrics)
        fcf_data = self.calc._calculate_historical_fcf(historicals)
        latest = fcf_data[0]

        self.assertIn("revenue", latest)
        self.assertIn("ebit", latest)
        self.assertIn("fcff", latest)
        self.assertIn("operating_margin", latest)
        self.assertIn("effective_tax_rate", latest)

    def test_fcf_is_positive(self):
        """Test that FCF is positive for our profitable mock company."""
        historicals = self.calc._extract_historicals(self.metrics)
        fcf_data = self.calc._calculate_historical_fcf(historicals)
        latest = fcf_data[0]
        self.assertGreater(latest["fcff"], 0)

    def test_margins_calculated(self):
        """Test that margins are calculated correctly."""
        historicals = self.calc._extract_historicals(self.metrics)
        fcf_data = self.calc._calculate_historical_fcf(historicals)
        latest = fcf_data[0]

        # Operating margin = EBIT / Revenue = 78B / 130B = 60%
        self.assertAlmostEqual(latest["operating_margin"], 0.60, places=2)

    def test_effective_tax_rate(self):
        """Test effective tax rate calculation."""
        historicals = self.calc._extract_historicals(self.metrics)
        fcf_data = self.calc._calculate_historical_fcf(historicals)
        latest = fcf_data[0]

        # Tax rate = 12B / 77B ≈ 15.6%
        self.assertGreater(latest["effective_tax_rate"], 0.10)
        self.assertLess(latest["effective_tax_rate"], 0.25)


class TestDCFWACC(unittest.TestCase):
    """Test WACC calculation."""

    def setUp(self):
        self.calc = DCFCalculator()
        self.metrics = build_mock_xbrl_metrics()

    def test_wacc_calculation(self):
        """Test WACC is calculated within reasonable range."""
        historicals = self.calc._extract_historicals(self.metrics)
        wacc_result = self.calc._calculate_wacc("TEST", historicals)

        # WACC should be between 5% and 25%
        self.assertGreaterEqual(wacc_result["wacc"], 0.05)
        self.assertLessEqual(wacc_result["wacc"], 0.25)

    def test_wacc_components(self):
        """Test WACC contains all components."""
        historicals = self.calc._extract_historicals(self.metrics)
        wacc_result = self.calc._calculate_wacc("TEST", historicals)

        self.assertIn("cost_of_equity", wacc_result)
        self.assertIn("cost_of_debt", wacc_result)
        self.assertIn("beta", wacc_result)
        self.assertIn("weight_equity", wacc_result)
        self.assertIn("weight_debt", wacc_result)

    def test_known_beta_lookup(self):
        """Test beta lookup for known ticker."""
        historicals = self.calc._extract_historicals(self.metrics)
        wacc_result = self.calc._calculate_wacc("NVDA", historicals)
        self.assertEqual(wacc_result["beta"], 1.65)

    def test_default_beta(self):
        """Test default beta for unknown ticker."""
        historicals = self.calc._extract_historicals(self.metrics)
        wacc_result = self.calc._calculate_wacc("UNKNOWN_TICKER", historicals)
        self.assertEqual(wacc_result["beta"], 1.0)


class TestDCFForecast(unittest.TestCase):
    """Test FCF forecasting."""

    def setUp(self):
        self.calc = DCFCalculator()
        self.metrics = build_mock_xbrl_metrics()

    def test_forecast_length(self):
        """Test that forecast produces 5 years."""
        historicals = self.calc._extract_historicals(self.metrics)
        fcf_data = self.calc._calculate_historical_fcf(historicals)
        forecast = self.calc._forecast_fcf(historicals, fcf_data)

        self.assertEqual(len(forecast), 5)

    def test_forecast_revenue_grows(self):
        """Test that forecasted revenue increases."""
        historicals = self.calc._extract_historicals(self.metrics)
        fcf_data = self.calc._calculate_historical_fcf(historicals)
        forecast = self.calc._forecast_fcf(historicals, fcf_data)

        # Each year's revenue should be higher than the last
        for i in range(1, len(forecast)):
            self.assertGreater(forecast[i]["revenue"], forecast[i-1]["revenue"])

    def test_forecast_growth_tapers(self):
        """Test that growth rate tapers down over forecast period."""
        historicals = self.calc._extract_historicals(self.metrics)
        fcf_data = self.calc._calculate_historical_fcf(historicals)
        forecast = self.calc._forecast_fcf(historicals, fcf_data)

        # Growth should generally decrease
        self.assertGreater(forecast[0]["revenue_growth"],
                          forecast[-1]["revenue_growth"])

    def test_forecast_fcf_positive(self):
        """Test that forecasted FCF is positive."""
        historicals = self.calc._extract_historicals(self.metrics)
        fcf_data = self.calc._calculate_historical_fcf(historicals)
        forecast = self.calc._forecast_fcf(historicals, fcf_data)

        for year in forecast:
            self.assertGreater(year["fcff"], 0)


class TestDCFTerminalValue(unittest.TestCase):
    """Test Terminal Value calculation."""

    def setUp(self):
        self.calc = DCFCalculator()
        self.metrics = build_mock_xbrl_metrics()

    def test_terminal_value_positive(self):
        """Test that terminal value is positive."""
        historicals = self.calc._extract_historicals(self.metrics)
        fcf_data = self.calc._calculate_historical_fcf(historicals)
        forecast = self.calc._forecast_fcf(historicals, fcf_data)
        wacc = self.calc._calculate_wacc("TEST", historicals)

        tv = self.calc._calculate_terminal_value(forecast, historicals, wacc["wacc"])

        self.assertGreater(tv["gordon_growth"]["terminal_value"], 0)
        self.assertGreater(tv["exit_multiple"]["terminal_value"], 0)
        self.assertGreater(tv["blended_terminal_value"], 0)

    def test_both_methods_present(self):
        """Test that both TV methods are calculated."""
        historicals = self.calc._extract_historicals(self.metrics)
        fcf_data = self.calc._calculate_historical_fcf(historicals)
        forecast = self.calc._forecast_fcf(historicals, fcf_data)
        wacc = self.calc._calculate_wacc("TEST", historicals)

        tv = self.calc._calculate_terminal_value(forecast, historicals, wacc["wacc"])

        self.assertIn("gordon_growth", tv)
        self.assertIn("exit_multiple", tv)
        self.assertIn("blended_terminal_value", tv)


class TestDCFFullModel(unittest.TestCase):
    """Test complete DCF model end-to-end."""

    def setUp(self):
        self.calc = DCFCalculator()
        self.metrics = build_mock_xbrl_metrics()

    def test_run_dcf_success(self):
        """Test complete DCF run."""
        result = self.calc.run_dcf("TEST", self.metrics)

        self.assertTrue(result["success"])
        self.assertEqual(result["ticker"], "TEST")

    def test_fair_value_positive(self):
        """Test that fair value per share is positive."""
        result = self.calc.run_dcf("TEST", self.metrics)
        fair_value = result["equity_value"]["fair_value_per_share"]

        self.assertGreater(fair_value, 0)

    def test_sensitivity_analysis(self):
        """Test sensitivity analysis is generated."""
        result = self.calc.run_dcf("TEST", self.metrics)
        sensitivity = result["sensitivity_analysis"]

        self.assertIn("wacc_vs_growth", sensitivity)
        matrix = sensitivity["wacc_vs_growth"]["matrix"]
        self.assertGreater(len(matrix), 0)

    def test_scenario_analysis(self):
        """Test Bull/Base/Bear scenarios."""
        result = self.calc.run_dcf("TEST", self.metrics)
        scenarios = result["scenarios"]

        self.assertIn("bull", scenarios)
        self.assertIn("base", scenarios)
        self.assertIn("bear", scenarios)

        # Bull should be higher than bear
        self.assertGreater(
            scenarios["bull"]["fair_value_per_share"],
            scenarios["bear"]["fair_value_per_share"]
        )

    def test_key_metrics(self):
        """Test key metrics are calculated."""
        result = self.calc.run_dcf("TEST", self.metrics)
        km = result["key_metrics"]

        self.assertIn("roic", km)
        self.assertIn("wacc", km)
        self.assertIn("roic_wacc_spread", km)
        self.assertIn("fcf_yield", km)
        self.assertIn("implied_ev_ebitda", km)
        self.assertIn("value_creation", km)

    def test_roic_positive(self):
        """Test ROIC is positive for profitable company."""
        result = self.calc.run_dcf("TEST", self.metrics)
        self.assertGreater(result["key_metrics"]["roic"], 0)


class TestDCFOutput(unittest.TestCase):
    """Test DCF output generation."""

    def setUp(self):
        self.calc = DCFCalculator()
        self.metrics = build_mock_xbrl_metrics()
        self.dcf_result = self.calc.run_dcf("TEST", self.metrics)

    def test_save_dcf_json(self):
        """Test JSON output generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_dcf.json"
            success = self.calc.save_dcf_json(self.dcf_result, path)

            self.assertTrue(success)
            self.assertTrue(path.exists())
            self.assertGreater(path.stat().st_size, 0)

    def test_save_dcf_csv(self):
        """Test CSV output generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            results = self.calc.save_dcf_csv(self.dcf_result, tmpdir_path)

            self.assertTrue(results.get("summary"))
            self.assertTrue(results.get("forecast"))
            self.assertTrue(results.get("sensitivity"))

            # Check files exist
            self.assertTrue((tmpdir_path / "TEST_dcf_summary.csv").exists())
            self.assertTrue((tmpdir_path / "TEST_dcf_forecast.csv").exists())
            self.assertTrue((tmpdir_path / "TEST_dcf_sensitivity.csv").exists())

    def test_insufficient_data(self):
        """Test DCF with insufficient data returns error."""
        sparse_metrics = {"metrics": {
            "Revenues:USD": {
                "name": "Revenues", "unit": "USD", "confidence": 100,
                "values": [{"val": 100, "end": "2026-01-25", "form": "10-K", "filed": "2026-02-25"}],
            }
        }}

        result = self.calc.run_dcf("TEST", sparse_metrics)
        self.assertFalse(result["success"])


def build_mock_ifrs_metrics():
    """Build mock XBRL metrics using IFRS-full taxonomy names and 20-F form entries."""
    return {
        "entity_name": "FPI TEST CORP",
        "taxonomy": "ifrs-full",
        "metrics": {
            # IFRS revenue key
            "Revenue:USD": {
                "name": "Revenue",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {"val": 58000000000, "end": "2024-12-31", "form": "20-F", "filed": "2025-02-20"},
                    {"val": 44000000000, "end": "2023-12-31", "form": "20-F", "filed": "2024-02-21"},
                    {"val": 37000000000, "end": "2022-12-31", "form": "20-F", "filed": "2023-02-22"},
                ],
            },
            # IFRS operating income key
            "ProfitLossFromOperatingActivities:USD": {
                "name": "ProfitLossFromOperatingActivities",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {"val": 13000000000, "end": "2024-12-31", "form": "20-F", "filed": "2025-02-20"},
                    {"val": 9000000000,  "end": "2023-12-31", "form": "20-F", "filed": "2024-02-21"},
                ],
            },
            # IFRS net income key
            "ProfitLoss:USD": {
                "name": "ProfitLoss",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {"val": 5500000000, "end": "2024-12-31", "form": "20-F", "filed": "2025-02-20"},
                    {"val": 3700000000, "end": "2023-12-31", "form": "20-F", "filed": "2024-02-21"},
                ],
            },
            # IFRS D&A key
            "DepreciationDepletionAmortisationExpense:USD": {
                "name": "DepreciationDepletionAmortisationExpense",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {"val": 3000000000, "end": "2024-12-31", "form": "20-F", "filed": "2025-02-20"},
                    {"val": 2500000000, "end": "2023-12-31", "form": "20-F", "filed": "2024-02-21"},
                ],
            },
            # IFRS CapEx key
            "PurchaseOfPropertyPlantAndEquipment:USD": {
                "name": "PurchaseOfPropertyPlantAndEquipment",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {"val": 4000000000, "end": "2024-12-31", "form": "20-F", "filed": "2025-02-20"},
                    {"val": 3200000000, "end": "2023-12-31", "form": "20-F", "filed": "2024-02-21"},
                ],
            },
            # IFRS OCF key
            "CashFlowsFromUsedInOperatingActivities:USD": {
                "name": "CashFlowsFromUsedInOperatingActivities",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {"val": 14000000000, "end": "2024-12-31", "form": "20-F", "filed": "2025-02-20"},
                    {"val": 10000000000, "end": "2023-12-31", "form": "20-F", "filed": "2024-02-21"},
                ],
            },
            # IFRS equity key
            "EquityAttributableToOwnersOfParent:USD": {
                "name": "EquityAttributableToOwnersOfParent",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {"val": 40000000000, "end": "2024-12-31", "form": "20-F", "filed": "2025-02-20"},
                ],
            },
            # IFRS cash key
            "CashAndCashEquivalents:USD": {
                "name": "CashAndCashEquivalents",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {"val": 6000000000, "end": "2024-12-31", "form": "20-F", "filed": "2025-02-20"},
                ],
            },
            # IFRS debt key
            "NoncurrentBorrowings:USD": {
                "name": "NoncurrentBorrowings",
                "unit": "USD",
                "confidence": 100.0,
                "values": [
                    {"val": 15000000000, "end": "2024-12-31", "form": "20-F", "filed": "2025-02-20"},
                ],
            },
            # Shares (using a common IFRS/DEI tag name)
            "WeightedAverageNumberOfDilutedSharesOutstanding:shares": {
                "name": "WeightedAverageNumberOfDilutedSharesOutstanding",
                "unit": "shares",
                "confidence": 100.0,
                "values": [
                    {"val": 1550000000, "end": "2024-12-31", "form": "20-F", "filed": "2025-02-20"},
                ],
            },
        },
    }


class TestDCFIFRSSupport(unittest.TestCase):
    """Test DCF support for foreign private issuers (20-F + IFRS-full taxonomy)."""

    def setUp(self):
        self.calc = DCFCalculator()
        self.metrics = build_mock_ifrs_metrics()

    def test_20f_form_accepted_as_annual(self):
        """_extract_historicals must accept 20-F entries the same as 10-K."""
        historicals = self.calc._extract_historicals(self.metrics)
        # Should have entries from 20-F filings
        self.assertGreaterEqual(len(historicals), 2)

    def test_ifrs_revenue_extracted(self):
        """Revenue extracted via IFRS key 'Revenue' (not US-GAAP 'Revenues')."""
        historicals = self.calc._extract_historicals(self.metrics)
        latest = historicals[0]
        # IFRS key is 'Revenue', not 'Revenues'
        self.assertEqual(latest.get("Revenue"), 58000000000)

    def test_ifrs_fcf_calculated(self):
        """FCF is calculated for IFRS metrics without error."""
        historicals = self.calc._extract_historicals(self.metrics)
        fcf_data = self.calc._calculate_historical_fcf(historicals)
        self.assertGreater(len(fcf_data), 0)
        # OCF method should kick in (CashFlowsFromUsedInOperatingActivities)
        latest_fcf = fcf_data[0]
        self.assertIsNotNone(latest_fcf.get("operating_cf"))
        self.assertIsNotNone(latest_fcf.get("fcff"))

    def test_dcf_runs_end_to_end_with_20f(self):
        """Full DCF pipeline succeeds with IFRS / 20-F data."""
        result = self.calc.run_dcf("AZN", self.metrics)
        self.assertTrue(result["success"], msg=result.get("error", ""))
        fair_value = result["equity_value"]["fair_value_per_share"]
        self.assertGreater(fair_value, 0)


if __name__ == "__main__":
    unittest.main()
