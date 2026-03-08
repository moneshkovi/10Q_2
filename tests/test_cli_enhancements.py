"""Tests for CLI Enhancements - Phase 6

Tests for progress tracking, performance stats, and comparison reports.

Author: SEC Filing Parser Team
Date: March 7, 2026
"""

import unittest
import tempfile
import csv
from pathlib import Path
from io import StringIO
import sys

from src.cli_enhancements import (
    Colors, ProgressTracker, PerformanceStats,
    ComparisonReportGenerator, print_banner, print_phase_header
)


class TestColors(unittest.TestCase):
    """Test color code definitions."""

    def test_color_codes_defined(self):
        """Test that all color codes are defined."""
        self.assertTrue(hasattr(Colors, 'HEADER'))
        self.assertTrue(hasattr(Colors, 'OKGREEN'))
        self.assertTrue(hasattr(Colors, 'WARNING'))
        self.assertTrue(hasattr(Colors, 'FAIL'))
        self.assertTrue(hasattr(Colors, 'ENDC'))
        self.assertTrue(hasattr(Colors, 'BOLD'))

    def test_color_codes_are_strings(self):
        """Test that color codes are ANSI escape strings."""
        self.assertIsInstance(Colors.HEADER, str)
        self.assertIn('\033', Colors.HEADER)
        self.assertIsInstance(Colors.ENDC, str)
        self.assertIn('\033', Colors.ENDC)


class TestProgressTracker(unittest.TestCase):
    """Test progress tracker functionality."""

    def test_initialization(self):
        """Test tracker initialization."""
        tracker = ProgressTracker(total=5, desc="Testing")
        self.assertEqual(tracker.total, 5)
        self.assertEqual(tracker.current, 0)
        self.assertEqual(tracker.desc, "Testing")

    def test_update(self):
        """Test progress update."""
        tracker = ProgressTracker(total=3, desc="Processing")
        tracker.update("NVDA", "Extracting...")
        self.assertEqual(tracker.current, 1)

        tracker.update("AAPL", "Complete")
        self.assertEqual(tracker.current, 2)

    def test_finish(self):
        """Test progress finish (should not raise)."""
        tracker = ProgressTracker(total=2, desc="Testing")
        tracker.update("NVDA")
        tracker.update("AAPL")
        tracker.finish()  # Should complete without error
        self.assertEqual(tracker.current, 2)


class TestPerformanceStats(unittest.TestCase):
    """Test performance statistics tracking."""

    def test_initialization(self):
        """Test stats initialization."""
        stats = PerformanceStats()
        self.assertEqual(len(stats.ticker_stats), 0)
        self.assertIsNone(stats.total_start)

    def test_start_total(self):
        """Test total timer start."""
        stats = PerformanceStats()
        stats.start_total()
        self.assertIsNotNone(stats.total_start)

    def test_ticker_tracking(self):
        """Test ticker-level tracking."""
        stats = PerformanceStats()
        stats.start_ticker("NVDA")

        self.assertIn("NVDA", stats.ticker_stats)
        self.assertIn("start", stats.ticker_stats["NVDA"])
        self.assertIn("phases", stats.ticker_stats["NVDA"])

    def test_phase_recording(self):
        """Test phase timing recording."""
        stats = PerformanceStats()
        stats.start_ticker("NVDA")
        stats.record_phase("NVDA", "Phase 2", 1.5)
        stats.record_phase("NVDA", "Phase 3", 2.3)

        self.assertIn("Phase 2", stats.ticker_stats["NVDA"]["phases"])
        self.assertEqual(stats.ticker_stats["NVDA"]["phases"]["Phase 2"], 1.5)
        self.assertEqual(stats.ticker_stats["NVDA"]["phases"]["Phase 3"], 2.3)

    def test_finish_ticker(self):
        """Test ticker finish timing."""
        stats = PerformanceStats()
        stats.start_ticker("NVDA")
        stats.finish_ticker("NVDA")

        self.assertIn("total", stats.ticker_stats["NVDA"])
        self.assertGreater(stats.ticker_stats["NVDA"]["total"], 0)

    def test_get_total_time(self):
        """Test total elapsed time."""
        stats = PerformanceStats()
        stats.start_total()
        total_time = stats.get_total_time()
        self.assertGreater(total_time, 0)

    def test_print_summary(self):
        """Test print summary (should not raise)."""
        stats = PerformanceStats()
        stats.start_total()
        stats.start_ticker("NVDA")
        stats.record_phase("NVDA", "Phase 2", 1.0)
        stats.finish_ticker("NVDA")

        # Capture output
        old_stdout = sys.stdout
        sys.stdout = StringIO()

        stats.print_summary()

        output = sys.stdout.getvalue()
        sys.stdout = old_stdout

        self.assertIn("PERFORMANCE SUMMARY", output)
        self.assertIn("NVDA", output)


class TestComparisonReportGenerator(unittest.TestCase):
    """Test comparison report generation."""

    def setUp(self):
        """Set up test data."""
        self.generator = ComparisonReportGenerator()
        self.sample_results = {
            "NVDA": {
                "success": True,
                "cik": "0001045810",
                "filings_found": 12,
                "metrics_extracted": 286,
                "quality_score": 85,
                "validation_flags": 100,
                "critical_issues": 0,
                "xml_generated": True,
                "csv_generated": True,
                "errors": []
            },
            "AAPL": {
                "success": True,
                "cik": "0000320193",
                "filings_found": 12,
                "metrics_extracted": 211,
                "quality_score": 92,
                "validation_flags": 50,
                "critical_issues": 2,
                "xml_generated": True,
                "csv_generated": True,
                "errors": []
            }
        }

    def test_generate_comparison_csv(self):
        """Test CSV comparison generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "comparison.csv"

            success = self.generator.generate_comparison_csv(
                self.sample_results,
                output_path
            )

            self.assertTrue(success)
            self.assertTrue(output_path.exists())

            # Read and verify content
            with open(output_path, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)

            # Check header rows
            self.assertEqual(rows[0][0], 'TICKER COMPARISON REPORT')

            # Check data rows contain our tickers
            csv_content = '\n'.join([','.join(row) for row in rows])
            self.assertIn('NVDA', csv_content)
            self.assertIn('AAPL', csv_content)

    def test_generate_comparison_csv_with_errors(self):
        """Test CSV generation with error data."""
        results_with_errors = {
            "NVDA": {
                "success": False,
                "errors": ["Failed to retrieve CIK", "Network timeout"]
            }
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "comparison_errors.csv"

            success = self.generator.generate_comparison_csv(
                results_with_errors,
                output_path
            )

            self.assertTrue(success)

            # Verify errors are included
            with open(output_path, 'r') as f:
                content = f.read()

            self.assertIn('ERRORS', content)
            self.assertIn('Failed to retrieve CIK', content)

    def test_print_comparison_table(self):
        """Test comparison table printing."""
        # Capture output
        old_stdout = sys.stdout
        sys.stdout = StringIO()

        self.generator.print_comparison_table(self.sample_results)

        output = sys.stdout.getvalue()
        sys.stdout = old_stdout

        # Verify table content
        self.assertIn("TICKER COMPARISON", output)
        self.assertIn("NVDA", output)
        self.assertIn("AAPL", output)
        self.assertIn("Success", output)
        self.assertIn("Quality", output)


class TestPrintFunctions(unittest.TestCase):
    """Test print helper functions."""

    def test_print_banner(self):
        """Test banner printing."""
        old_stdout = sys.stdout
        sys.stdout = StringIO()

        print_banner()

        output = sys.stdout.getvalue()
        sys.stdout = old_stdout

        self.assertIn("SEC FILING PARSER", output)

    def test_print_phase_header(self):
        """Test phase header printing."""
        old_stdout = sys.stdout
        sys.stdout = StringIO()

        print_phase_header(3, "XBRL Extraction")

        output = sys.stdout.getvalue()
        sys.stdout = old_stdout

        self.assertIn("PHASE 3", output)
        self.assertIn("XBRL Extraction", output)


if __name__ == "__main__":
    unittest.main()
