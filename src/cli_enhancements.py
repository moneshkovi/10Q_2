"""
CLI Enhancements for SEC Filing Parser - Phase 6

This module provides enhanced CLI features including:
- Progress bars for visual feedback
- Colored output for better readability
- Performance statistics
- Comparison reports across tickers

Author: SEC Filing Parser Team
Date: March 7, 2026
"""

import time
from typing import Dict, List
from pathlib import Path
import csv
from datetime import datetime


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class ProgressTracker:
    """
    Tracks and displays progress for multi-ticker processing.

    Simple progress indicator without external dependencies.
    """

    def __init__(self, total: int, desc: str = "Processing"):
        self.total = total
        self.current = 0
        self.desc = desc
        self.start_time = time.time()

    def update(self, ticker: str, status: str = ""):
        """Update progress for current ticker."""
        self.current += 1
        elapsed = time.time() - self.start_time

        # Calculate progress
        pct = (self.current / self.total) * 100
        bar_length = 40
        filled = int(bar_length * self.current / self.total)
        bar = '█' * filled + '░' * (bar_length - filled)

        # Estimate remaining time
        if self.current > 0:
            avg_time = elapsed / self.current
            remaining = avg_time * (self.total - self.current)
            eta = f"ETA: {remaining:.1f}s"
        else:
            eta = "ETA: --"

        # Print progress
        print(f"\r{self.desc}: [{bar}] {pct:.0f}% ({self.current}/{self.total}) "
              f"| {ticker:6s} {status:20s} | {eta}", end='', flush=True)

    def finish(self):
        """Mark as complete."""
        elapsed = time.time() - self.start_time
        print(f"\n{Colors.OKGREEN}✓ Completed in {elapsed:.2f}s{Colors.ENDC}")


class PerformanceStats:
    """Track performance statistics for the pipeline."""

    def __init__(self):
        self.ticker_stats = {}
        self.total_start = None

    def start_total(self):
        """Start total timer."""
        self.total_start = time.time()

    def start_ticker(self, ticker: str):
        """Start timer for a ticker."""
        self.ticker_stats[ticker] = {
            'start': time.time(),
            'phases': {}
        }

    def record_phase(self, ticker: str, phase: str, duration: float):
        """Record phase timing."""
        if ticker in self.ticker_stats:
            self.ticker_stats[ticker]['phases'][phase] = duration

    def finish_ticker(self, ticker: str):
        """Finish ticker timing."""
        if ticker in self.ticker_stats:
            start = self.ticker_stats[ticker]['start']
            self.ticker_stats[ticker]['total'] = time.time() - start

    def get_total_time(self) -> float:
        """Get total elapsed time."""
        if self.total_start:
            return time.time() - self.total_start
        return 0

    def print_summary(self):
        """Print performance summary."""
        print(f"\n{Colors.HEADER}{'='*70}{Colors.ENDC}")
        print(f"{Colors.HEADER}PERFORMANCE SUMMARY{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*70}{Colors.ENDC}\n")

        for ticker, stats in self.ticker_stats.items():
            total = stats.get('total', 0)
            print(f"{Colors.BOLD}{ticker}{Colors.ENDC}: {total:.2f}s total")

            phases = stats.get('phases', {})
            for phase, duration in phases.items():
                pct = (duration / total * 100) if total > 0 else 0
                print(f"  - {phase}: {duration:.2f}s ({pct:.0f}%)")
            print()

        total_time = self.get_total_time()
        print(f"{Colors.OKGREEN}Total pipeline time: {total_time:.2f}s{Colors.ENDC}\n")


class ComparisonReportGenerator:
    """
    Generates comparison reports across multiple tickers.
    """

    def __init__(self):
        pass

    def generate_comparison_csv(self, results: Dict[str, Dict],
                                output_path: Path) -> bool:
        """
        Generate comparison CSV across all tickers.

        Args:
            results: Dictionary of ticker -> result data
            output_path: Path to save comparison CSV

        Returns:
            True if successful
        """
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Header
                writer.writerow(['TICKER COMPARISON REPORT'])
                writer.writerow(['Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')])
                writer.writerow([])

                # Summary table
                writer.writerow([
                    'Ticker',
                    'Success',
                    'CIK',
                    'Filings',
                    'Metrics',
                    'Quality Score',
                    'Flags',
                    'Critical Issues',
                    'XML Generated',
                    'CSV Generated'
                ])

                # Data rows
                for ticker, result in sorted(results.items()):
                    writer.writerow([
                        ticker,
                        'Yes' if result.get('success') else 'No',
                        result.get('cik', ''),
                        result.get('filings_found', 0),
                        result.get('metrics_extracted', 0),
                        result.get('quality_score', 0),
                        result.get('validation_flags', 0),
                        result.get('critical_issues', 0),
                        'Yes' if result.get('xml_generated') else 'No',
                        'Yes' if result.get('csv_generated') else 'No'
                    ])

                writer.writerow([])

                # Errors section
                has_errors = any(result.get('errors') for result in results.values())
                if has_errors:
                    writer.writerow(['ERRORS'])
                    writer.writerow([])
                    writer.writerow(['Ticker', 'Error'])

                    for ticker, result in sorted(results.items()):
                        errors = result.get('errors', [])
                        for error in errors:
                            writer.writerow([ticker, error])

            return True

        except Exception as e:
            print(f"{Colors.FAIL}Failed to generate comparison report: {e}{Colors.ENDC}")
            return False

    def generate_metrics_comparison_csv(self, data_dir: Path,
                                        tickers: List[str],
                                        output_path: Path) -> bool:
        """
        Generate side-by-side comparison of calculated metrics.

        Args:
            data_dir: Base data directory
            tickers: List of tickers to compare
            output_path: Path to save comparison

        Returns:
            True if successful
        """
        try:
            # Collect all calculated metrics
            all_metrics = {}

            for ticker in tickers:
                calc_path = data_dir / ticker / "parsed" / f"{ticker}_calculated_metrics.csv"
                if calc_path.exists():
                    with open(calc_path, 'r') as f:
                        reader = csv.DictReader(f)
                        all_metrics[ticker] = {
                            row['Metric']: row['Display']
                            for row in reader
                        }

            if not all_metrics:
                return False

            # Get all unique metrics
            all_metric_names = set()
            for metrics in all_metrics.values():
                all_metric_names.update(metrics.keys())

            # Write comparison
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Header
                header = ['Metric'] + list(sorted(all_metrics.keys()))
                writer.writerow(header)

                # Data rows
                for metric in sorted(all_metric_names):
                    row = [metric]
                    for ticker in sorted(all_metrics.keys()):
                        value = all_metrics[ticker].get(metric, 'N/A')
                        row.append(value)
                    writer.writerow(row)

            return True

        except Exception as e:
            print(f"{Colors.FAIL}Failed to generate metrics comparison: {e}{Colors.ENDC}")
            return False

    def print_comparison_table(self, results: Dict[str, Dict]):
        """
        Print a formatted comparison table to console.

        Args:
            results: Dictionary of ticker -> result data
        """
        print(f"\n{Colors.HEADER}{'='*100}{Colors.ENDC}")
        print(f"{Colors.HEADER}TICKER COMPARISON{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*100}{Colors.ENDC}\n")

        # Header
        print(f"{'Ticker':<8} {'Success':<8} {'Filings':<8} {'Metrics':<8} "
              f"{'Quality':<8} {'Flags':<8} {'Critical':<10} {'Output':<10}")
        print("-" * 100)

        # Rows
        for ticker in sorted(results.keys()):
            result = results[ticker]

            success_icon = f"{Colors.OKGREEN}✓{Colors.ENDC}" if result.get('success') else f"{Colors.FAIL}✗{Colors.ENDC}"
            quality = result.get('quality_score', 0)
            quality_color = Colors.OKGREEN if quality >= 80 else Colors.WARNING if quality >= 50 else Colors.FAIL
            critical = result.get('critical_issues', 0)
            critical_str = f"{Colors.FAIL}{critical}{Colors.ENDC}" if critical > 0 else "0"

            output_status = "XML+CSV" if result.get('xml_generated') and result.get('csv_generated') else \
                           "XML" if result.get('xml_generated') else \
                           "CSV" if result.get('csv_generated') else "None"

            print(f"{ticker:<8} {success_icon:<15} "
                  f"{result.get('filings_found', 0):<8} "
                  f"{result.get('metrics_extracted', 0):<8} "
                  f"{quality_color}{quality:<8}{Colors.ENDC} "
                  f"{result.get('validation_flags', 0):<8} "
                  f"{critical_str:<17} "
                  f"{output_status:<10}")

        print()


def print_banner():
    """Print application banner."""
    banner = f"""
{Colors.HEADER}{'='*70}
   SEC FILING PARSER v1.0
   Production-Grade Financial Data Extraction Pipeline
{'='*70}{Colors.ENDC}
    """
    print(banner)


def print_phase_header(phase_num: int, phase_name: str):
    """Print phase header with formatting."""
    print(f"\n{Colors.OKCYAN}{'='*70}")
    print(f"PHASE {phase_num}: {phase_name}")
    print(f"{'='*70}{Colors.ENDC}")
