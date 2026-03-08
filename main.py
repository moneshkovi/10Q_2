#!/usr/bin/env python3
"""Main entry point for SEC Filing Parser.

Usage:
    python main.py NVDA                    # Process single ticker
    python main.py AAPL MSFT GOOG         # Process multiple tickers

This script orchestrates the entire pipeline:
1. Validate ticker
2. Retrieve filing metadata from SEC
3. Identify XBRL data availability (PDFs blocked by SEC bot detection)
4. Parse financial data via XBRL API (Phase 3)
5. Reconcile sources (TODO: Phase 4)
6. Generate XML output (TODO: Phase 5)
"""

import sys
import logging
import time
from pathlib import Path
from typing import Dict, List

import config
from src.sec_client import SECClient, TickerNotFoundError, SECAPIError
from src.xbrl_parser import XBRLParser
from src.data_reconciler import DataReconciler
from src.xml_builder import XMLBuilder
from src.csv_builder import CSVBuilder
from src.cli_enhancements import (
    Colors, ProgressTracker, PerformanceStats,
    ComparisonReportGenerator, print_banner, print_phase_header
)
from src.dcf_calculator import DCFCalculator


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging(ticker: str) -> logging.Logger:
    """Configure logging for the application.

    Logs go to both console and a file in data/{TICKER}/logs/

    Args:
        ticker: Stock ticker symbol

    Returns:
        Configured logger instance
    """
    log_dir = config.DATA_DIR / ticker.upper() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("SECFilingParser")
    logger.setLevel(logging.DEBUG)

    # Remove any existing handlers to avoid duplicates
    logger.handlers.clear()

    # File handler
    log_file = log_dir / f"processing_{Path.home().name}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter(config.LOG_FORMAT)
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# ============================================================================
# MAIN PROCESSING LOGIC
# ============================================================================

def process_ticker(ticker: str, perf_stats: PerformanceStats = None) -> Dict:
    """Process a single ticker through the SEC filing parser pipeline.

    Orchestrates Phase 2 (and future phases):
    1. Validate ticker and convert to CIK
    2. Retrieve filing metadata for past N years
    3. Download PDF files locally
    4. (TODO) Parse financial data from PDFs/XBRL
    5. (TODO) Reconcile sources and validate data
    6. (TODO) Generate structured XML output

    Args:
        ticker: Stock ticker symbol (e.g., 'NVDA')

    Returns:
        Dictionary with processing results:
        {
            "success": bool,
            "ticker": str,
            "cik": str (if successful),
            "filings_found": int,
            "pdfs_downloaded": int,
            "pdfs_failed": int,
            "output_dir": str,
            "errors": List[str]
        }
    """
    result = {
        "success": False,
        "ticker": ticker.upper(),
        "cik": None,
        "filings_found": 0,
        "xbrl_available": 0,
        "xbrl_unavailable": 0,
        "metrics_extracted": 0,
        "quality_score": 0,
        "validation_flags": 0,
        "critical_issues": 0,
        "warnings": 0,
        "xml_generated": False,
        "csv_generated": False,
        "xml_warnings": 0,
        "dcf_generated": False,
        "dcf_fair_value": 0,
        "dcf_wacc": 0,
        "output_dir": str(config.DATA_DIR / ticker.upper()),
        "errors": []
    }

    logger = setup_logging(ticker)

    # Track performance if stats collector provided
    if perf_stats:
        perf_stats.start_ticker(ticker.upper())

    logger.info("=" * 70)
    logger.info(f"Starting SEC Filing Parser for ticker: {ticker}")
    logger.info("=" * 70)

    # ========================================================================
    # PHASE 2: SEC DATA RETRIEVAL
    # ========================================================================

    try:
        # Step 1: Initialize SEC client
        logger.info("Initializing SEC Edgar client...")
        client = SECClient()

        # Step 2: Validate ticker and get CIK
        logger.info(f"Converting ticker '{ticker}' to CIK...")
        try:
            cik = client.get_cik_from_ticker(ticker)
            result["cik"] = cik
            logger.info(f"✓ Found CIK: {cik} for ticker {ticker}")
        except TickerNotFoundError as e:
            logger.error(f"✗ Ticker validation failed: {e}")
            result["errors"].append(str(e))
            return result

        # Step 3: Create output directories
        data_dir = config.DATA_DIR / ticker.upper()
        raw_dir = data_dir / "raw"
        parsed_dir = data_dir / "parsed"
        logs_dir = data_dir / "logs"

        for directory in [raw_dir, parsed_dir, logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"✓ Created output directories in {data_dir}")

        # Step 4: Retrieve filing metadata
        logger.info(f"Retrieving {config.LOOKBACK_YEARS}-year filing history...")
        try:
            filings = client.get_filings(
                cik=cik,
                form_types=config.FILING_TYPES,
                years=config.LOOKBACK_YEARS
            )
            result["filings_found"] = len(filings)
            logger.info(f"✓ Retrieved {len(filings)} filings")
        except SECAPIError as e:
            logger.error(f"✗ Failed to retrieve filings: {e}")
            result["errors"].append(str(e))
            return result

        if not filings:
            logger.warning("No filings found for this ticker")
            result["errors"].append("No filings found")
            return result

        # Step 5: Identify XBRL data availability for each filing
        # NOTE: PDF downloads are blocked by SEC bot detection.
        # XBRL is the preferred data source and is available via API.
        logger.info("Checking XBRL data availability...")
        logger.info("-" * 70)

        for i, filing in enumerate(filings, 1):
            accession = filing["accession_number"]
            form_type = filing["form_type"]
            filing_date = filing["filing_date"]
            is_xbrl = filing.get("is_xbrl", False)

            logger.info(
                f"[{i}/{len(filings)}] {form_type} filed {filing_date}"
                f" (accession: {accession})"
            )

            if is_xbrl:
                # XBRL data is available - get the viewer URL
                xbrl_url = client.get_xbrl_url(accession)
                logger.info(f"  ✓ XBRL data available (will parse in Phase 3)")
                filing["xbrl_url"] = xbrl_url
                result["xbrl_available"] += 1
            else:
                # No XBRL for this filing - would need PDF parsing (fallback)
                logger.warning(f"  ⚠ No XBRL data available for this filing")
                filing["xbrl_url"] = None
                result["xbrl_unavailable"] += 1

        logger.info("-" * 70)
        logger.info(
            f"✓ Data check complete: {result['xbrl_available']} with XBRL, "
            f"{result['xbrl_unavailable']} without"
        )

        # ========================================================================
        # PHASE 3: DATA EXTRACTION (XBRL PARSING)
        # ========================================================================

        logger.info("=" * 70)
        logger.info("PHASE 3: XBRL Financial Data Extraction")
        logger.info("=" * 70)

        try:
            parser = XBRLParser()
            logger.info(f"Extracting XBRL metrics for {len(filings)} filings...")

            # Extract metrics for each filing
            metrics_data = parser.extract_metrics_for_filings(
                cik=cik,
                filings=filings,
                lookback_years=config.LOOKBACK_YEARS
            )

            if metrics_data and 'metrics' in metrics_data:
                # Save to JSON
                json_filename = f"{ticker.upper()}_xbrl_metrics.json"
                json_path = parsed_dir / json_filename
                success = parser.save_metrics_to_json(metrics_data, json_path)

                if success:
                    result["metrics_extracted"] = len(metrics_data.get('metrics', {}))
                    logger.info(f"✓ PHASE 3 COMPLETE: {result['metrics_extracted']} metrics extracted")
                else:
                    logger.warning("Phase 3: Failed to save metrics JSON")
                    result["metrics_extracted"] = 0
            else:
                logger.warning("Phase 3: No metrics extracted")
                result["metrics_extracted"] = 0

        except Exception as e:
            logger.error(f"Phase 3 error: {e}", exc_info=True)
            result["errors"].append(f"Phase 3 failed: {str(e)}")
            result["metrics_extracted"] = 0


        # ========================================================================
        # PHASE 4: DATA RECONCILIATION & VALIDATION
        # ========================================================================

        logger.info("=" * 70)
        logger.info("PHASE 4: Data Reconciliation & Validation")
        logger.info("=" * 70)

        try:
            # Only run validation if we have metrics from Phase 3
            if result["metrics_extracted"] > 0 and metrics_data:
                reconciler = DataReconciler()

                # Run validation
                validation_report = reconciler.reconcile_and_validate(
                    xbrl_metrics=metrics_data,
                    ticker=ticker.upper()
                )

                # Save validation report
                validation_filename = f"{ticker.upper()}_validation_report.json"
                validation_path = parsed_dir / validation_filename
                reconciler.save_validation_report(str(validation_path))

                # Add to results
                result["quality_score"] = validation_report.get("quality_score", 0)
                result["validation_flags"] = len(validation_report.get("flags", []))
                result["critical_issues"] = len(reconciler.get_critical_flags())
                result["warnings"] = len(reconciler.get_warnings())

                logger.info(f"✓ PHASE 4 COMPLETE: Quality score = {result['quality_score']}/100")
                logger.info(f"  Flags: {result['validation_flags']} total")
                logger.info(f"  Critical issues: {result['critical_issues']}")
                logger.info(f"  Warnings: {result['warnings']}")

                # Print summary to console
                reconciler.print_summary()

            else:
                logger.warning("Phase 4: Skipped (no metrics from Phase 3)")
                result["quality_score"] = 0
                result["validation_flags"] = 0

        except Exception as e:
            logger.error(f"Phase 4 error: {e}", exc_info=True)
            result["errors"].append(f"Phase 4 failed: {str(e)}")
            result["quality_score"] = 0
            result["validation_flags"] = 0

        # ========================================================================
        # PHASE 5: XML OUTPUT GENERATION
        # ========================================================================

        logger.info("=" * 70)
        logger.info("PHASE 5: XML Output Generation")
        logger.info("=" * 70)

        try:
            # Only generate XML if we have metrics and validation results
            if result["metrics_extracted"] > 0 and metrics_data and validation_report:
                xml_builder = XMLBuilder()

                # Build XML
                logger.info("Building XML structure...")
                xml_root = xml_builder.build_filing_xml(
                    ticker=ticker.upper(),
                    xbrl_metrics=metrics_data,
                    validation_report=validation_report
                )

                # Validate XML structure
                validation_errors = xml_builder.validate_xml(xml_root)
                if validation_errors:
                    logger.warning(f"XML validation warnings: {validation_errors}")
                    result["xml_warnings"] = len(validation_errors)
                else:
                    result["xml_warnings"] = 0

                # Save XML to file
                xml_filename = f"{ticker.upper()}_financial_data.xml"
                xml_path = parsed_dir / xml_filename

                success = xml_builder.save_xml(xml_root, xml_path)

                if success:
                    result["xml_generated"] = True
                    result["xml_path"] = str(xml_path)
                    logger.info(f"✓ XML generated at {xml_path}")
                else:
                    result["xml_generated"] = False
                    logger.warning("Phase 5: Failed to save XML file")

                # Generate CSV files
                logger.info("Generating CSV files...")
                csv_builder = CSVBuilder()
                csv_results = csv_builder.export_to_csv(
                    ticker=ticker.upper(),
                    xbrl_metrics=metrics_data,
                    validation_report=validation_report,
                    output_dir=parsed_dir
                )

                # Also create pivot table format
                pivot_path = parsed_dir / f"{ticker.upper()}_pivot.csv"
                csv_builder.create_pivot_table_csv(
                    ticker=ticker.upper(),
                    xbrl_metrics=metrics_data,
                    output_path=pivot_path
                )

                result["csv_generated"] = all(csv_results.values())
                csv_count = sum(1 for v in csv_results.values() if v) + 1  # +1 for pivot
                logger.info(f"✓ PHASE 5 COMPLETE: {csv_count} CSV files generated")
                logger.info(f"  - Financial metrics CSV")
                logger.info(f"  - Calculated metrics CSV")
                logger.info(f"  - Validation summary CSV")
                logger.info(f"  - Pivot table CSV")

            else:
                logger.warning("Phase 5: Skipped (no metrics or validation data)")
                result["xml_generated"] = False

        except Exception as e:
            logger.error(f"Phase 5 error: {e}", exc_info=True)
            result["errors"].append(f"Phase 5 failed: {str(e)}")
            result["xml_generated"] = False

        # ========================================================================
        # PHASE 7: DCF VALUATION
        # ========================================================================

        logger.info("=" * 70)
        logger.info("PHASE 7: DCF Valuation Model")
        logger.info("=" * 70)

        try:
            if result["metrics_extracted"] > 0 and metrics_data:
                dcf_calculator = DCFCalculator()

                # Run DCF model
                dcf_result = dcf_calculator.run_dcf(
                    ticker=ticker.upper(),
                    xbrl_metrics=metrics_data
                )

                if dcf_result.get("success"):
                    # Save DCF JSON
                    dcf_json_path = parsed_dir / f"{ticker.upper()}_dcf_valuation.json"
                    dcf_calculator.save_dcf_json(dcf_result, dcf_json_path)

                    # Save DCF CSVs (summary, forecast, sensitivity)
                    dcf_csv_results = dcf_calculator.save_dcf_csv(dcf_result, parsed_dir)

                    # Print console summary
                    dcf_calculator.print_dcf_summary(dcf_result)

                    # Add to results
                    result["dcf_generated"] = True
                    result["dcf_fair_value"] = dcf_result.get("equity_value", {}).get("fair_value_per_share", 0)
                    result["dcf_wacc"] = dcf_result.get("wacc", {}).get("wacc", 0)
                    result["dcf_roic"] = dcf_result.get("key_metrics", {}).get("roic", 0)

                    dcf_csv_count = sum(1 for v in dcf_csv_results.values() if v)
                    logger.info(f"✓ PHASE 7 COMPLETE: DCF valuation generated")
                    logger.info(f"  Fair Value: ${result['dcf_fair_value']:.2f}/share")
                    logger.info(f"  WACC: {result['dcf_wacc']:.2%}")
                    logger.info(f"  Files: 1 JSON + {dcf_csv_count} CSVs")
                else:
                    result["dcf_generated"] = False
                    logger.warning(f"Phase 7: DCF failed - {dcf_result.get('error', 'Unknown')}")
            else:
                logger.warning("Phase 7: Skipped (no metrics data)")
                result["dcf_generated"] = False

        except Exception as e:
            logger.error(f"Phase 7 error: {e}", exc_info=True)
            result["errors"].append(f"Phase 7 failed: {str(e)}")
            result["dcf_generated"] = False

        # Final Summary
        logger.info("=" * 70)
        logger.info("PIPELINE COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Ticker:         {ticker.upper()}")
        logger.info(f"CIK:            {cik}")
        logger.info(f"Filings found:  {result['filings_found']}")
        logger.info(f"Metrics:        {result['metrics_extracted']}")
        logger.info(f"Quality Score:  {result.get('quality_score', 0)}/100")
        if result.get('dcf_generated'):
            logger.info(f"DCF Fair Value: ${result.get('dcf_fair_value', 0):.2f}/share")
        logger.info(f"Output:         {data_dir}")
        logger.info("")

        result["success"] = True

        # Record completion timing
        if perf_stats:
            perf_stats.finish_ticker(ticker.upper())

        return result

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        result["errors"].append(str(e))

        # Record completion even on error
        if perf_stats:
            perf_stats.finish_ticker(ticker.upper())

        return result


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """Main CLI entry point with Phase 6 enhancements."""
    if len(sys.argv) < 2:
        print(f"""
{Colors.HEADER}SEC Filing Parser - Production-Grade Financial Data Pipeline{Colors.ENDC}

{Colors.BOLD}Usage:{Colors.ENDC}
    python main.py TICKER [TICKER2] [TICKER3] ...

{Colors.BOLD}Examples:{Colors.ENDC}
    python main.py NVDA                    # Process NVIDIA
    python main.py AAPL MSFT GOOG TSLA     # Process multiple tickers

{Colors.BOLD}Pipeline:{Colors.ENDC}
  {Colors.OKCYAN}Phase 2{Colors.ENDC}: Retrieve filing metadata from SEC Edgar
  {Colors.OKCYAN}Phase 3{Colors.ENDC}: Extract XBRL financial metrics
  {Colors.OKCYAN}Phase 4{Colors.ENDC}: Validate and reconcile data
  {Colors.OKCYAN}Phase 5{Colors.ENDC}: Generate XML and CSV outputs
  {Colors.OKCYAN}Phase 6{Colors.ENDC}: Enhanced reporting and statistics
  {Colors.OKCYAN}Phase 7{Colors.ENDC}: DCF valuation model (industry standard)

{Colors.BOLD}Output:{Colors.ENDC}
  - JSON with 615+ XBRL metrics
  - XML financial data file
  - 4 CSV files per ticker (metrics, calculated, pivot, validation)
  - DCF valuation (summary, forecast, sensitivity CSVs)
  - Comparison reports (multi-ticker runs)
  - Performance statistics
  - Processing logs

{Colors.BOLD}Data Location:{Colors.ENDC}
  {config.DATA_DIR}/
        """)
        sys.exit(1)

    tickers = sys.argv[1:]

    # Show banner
    print_banner()

    print(f"{Colors.BOLD}Processing {len(tickers)} ticker(s):{Colors.ENDC} {', '.join(tickers)}\n")

    # Initialize performance tracking
    perf_stats = PerformanceStats()
    perf_stats.start_total()

    # Initialize progress tracker
    progress = ProgressTracker(total=len(tickers), desc="Processing tickers") if len(tickers) > 1 else None

    # Process each ticker
    all_results = {}
    for i, ticker in enumerate(tickers):
        # Update progress
        if progress:
            progress.update(ticker.upper(), "Starting...")

        # Process ticker
        result = process_ticker(ticker, perf_stats)
        all_results[ticker.upper()] = result

        # Update progress
        if progress:
            status = f"✓ {result.get('metrics_extracted', 0)} metrics" if result['success'] else "✗ Failed"
            # Update one more time to show completion
            # (this is a hack since update increments current, but we want to show the status)
            progress.current -= 1
            progress.update(ticker.upper(), status)

        # Print individual results (only if single ticker or errors)
        if len(tickers) == 1 or not result['success']:
            print(f"\n{Colors.BOLD}{ticker.upper()} Results:{Colors.ENDC}")
            if result['success']:
                print(f"  {Colors.OKGREEN}✓ Success{Colors.ENDC}")
                print(f"  CIK: {result['cik']}")
                print(f"  Filings found: {result['filings_found']}")
                print(f"  Metrics extracted: {result['metrics_extracted']}")
                print(f"  Quality score: {result.get('quality_score', 0)}/100")

                if result.get('xml_generated', False):
                    print(f"  {Colors.OKGREEN}✓{Colors.ENDC} XML generated")
                if result.get('csv_generated', False):
                    print(f"  {Colors.OKGREEN}✓{Colors.ENDC} CSV files generated (4 files)")

                if result.get('dcf_generated', False):
                    print(f"  {Colors.OKGREEN}✓{Colors.ENDC} DCF Valuation: "
                          f"${result.get('dcf_fair_value', 0):.2f}/share")

                if result.get('critical_issues', 0) > 0:
                    print(f"  {Colors.WARNING}⚠{Colors.ENDC}  Critical issues: {result['critical_issues']}")
            else:
                print(f"  {Colors.FAIL}✗ Failed{Colors.ENDC}")
                if result['errors']:
                    for error in result['errors']:
                        print(f"    {Colors.FAIL}- {error}{Colors.ENDC}")

    # Finish progress
    if progress:
        progress.finish()

    # Show comparison table for multiple tickers
    if len(tickers) > 1:
        report_gen = ComparisonReportGenerator()
        report_gen.print_comparison_table(all_results)

        # Generate comparison CSV files
        comparison_dir = config.DATA_DIR / "comparisons"
        comparison_dir.mkdir(parents=True, exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        comparison_csv = comparison_dir / f"comparison_{timestamp}.csv"

        if report_gen.generate_comparison_csv(all_results, comparison_csv):
            print(f"{Colors.OKGREEN}✓{Colors.ENDC} Comparison report saved: {comparison_csv}")

        # Generate metrics comparison if we have successful results
        successful_tickers = [t for t, r in all_results.items() if r['success']]
        if len(successful_tickers) > 1:
            metrics_comparison_csv = comparison_dir / f"metrics_comparison_{timestamp}.csv"
            if report_gen.generate_metrics_comparison_csv(config.DATA_DIR, successful_tickers, metrics_comparison_csv):
                print(f"{Colors.OKGREEN}✓{Colors.ENDC} Metrics comparison saved: {metrics_comparison_csv}")

    # Performance summary
    perf_stats.print_summary()

    # Final summary
    print(f"\n{Colors.HEADER}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.HEADER}FINAL SUMMARY{Colors.ENDC}")
    print(f"{Colors.HEADER}{'=' * 70}{Colors.ENDC}\n")

    successful = sum(1 for r in all_results.values() if r['success'])
    total_xbrl = sum(r['xbrl_available'] for r in all_results.values())
    total_metrics = sum(r.get('metrics_extracted', 0) for r in all_results.values())
    avg_quality = sum(r.get('quality_score', 0) for r in all_results.values()) / len(all_results) if all_results else 0
    total_critical = sum(r.get('critical_issues', 0) for r in all_results.values())
    xml_generated = sum(1 for r in all_results.values() if r.get('xml_generated', False))
    csv_generated = sum(1 for r in all_results.values() if r.get('csv_generated', False))
    dcf_generated = sum(1 for r in all_results.values() if r.get('dcf_generated', False))

    success_color = Colors.OKGREEN if successful == len(tickers) else Colors.WARNING
    print(f"{Colors.BOLD}Tickers processed:{Colors.ENDC} {success_color}{successful}/{len(tickers)}{Colors.ENDC}")
    print(f"{Colors.BOLD}Filings with XBRL:{Colors.ENDC} {total_xbrl}")
    print(f"{Colors.BOLD}Metrics extracted:{Colors.ENDC} {total_metrics}")
    print(f"{Colors.BOLD}XML files:{Colors.ENDC} {xml_generated}/{len(tickers)}")
    print(f"{Colors.BOLD}CSV files:{Colors.ENDC} {csv_generated}/{len(tickers)} ({csv_generated * 4} total files)")
    print(f"{Colors.BOLD}DCF valuations:{Colors.ENDC} {dcf_generated}/{len(tickers)}")

    # Show DCF fair values
    for t, r in sorted(all_results.items()):
        if r.get('dcf_generated'):
            print(f"  {Colors.OKCYAN}{t}{Colors.ENDC}: ${r.get('dcf_fair_value', 0):.2f}/share "
                  f"(WACC={r.get('dcf_wacc', 0):.2%})")

    quality_color = Colors.OKGREEN if avg_quality >= 80 else Colors.WARNING if avg_quality >= 50 else Colors.FAIL
    print(f"{Colors.BOLD}Avg quality score:{Colors.ENDC} {quality_color}{avg_quality:.1f}/100{Colors.ENDC}")

    if total_critical > 0:
        print(f"{Colors.WARNING}⚠  Total critical issues: {total_critical}{Colors.ENDC}")

    print(f"{Colors.BOLD}Data location:{Colors.ENDC} {config.DATA_DIR}/")

    if len(tickers) > 1:
        print(f"{Colors.BOLD}Comparison reports:{Colors.ENDC} {config.DATA_DIR}/comparisons/")

    print(f"\n{Colors.HEADER}{'=' * 70}{Colors.ENDC}\n")

    sys.exit(0 if successful == len(tickers) else 1)


if __name__ == "__main__":
    main()
