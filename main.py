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
from pathlib import Path
from typing import Dict, List

import config
from src.sec_client import SECClient, TickerNotFoundError, SECAPIError
from src.xbrl_parser import XBRLParser


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

def process_ticker(ticker: str) -> Dict:
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
        "output_dir": str(config.DATA_DIR / ticker.upper()),
        "errors": []
    }

    logger = setup_logging(ticker)
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

        # Step 6: Summary
        logger.info("=" * 70)
        logger.info("PHASE 2 COMPLETE: SEC Data Retrieval")
        logger.info("=" * 70)
        logger.info(f"Ticker:         {ticker.upper()}")
        logger.info(f"CIK:            {cik}")
        logger.info(f"Filings found:  {result['filings_found']}")
        logger.info(f"XBRL available: {result['xbrl_available']}")
        logger.info(f"Output directory: {data_dir}")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Phase 3: Parse XBRL data via SEC API (/api/xbrl/companyfacts/)")
        logger.info("  2. Phase 4: Validate and reconcile data quality")
        logger.info("  3. Phase 5: Generate structured XML output")
        logger.info("  4. Phase 6: CLI interface and final integration")
        logger.info("")

        result["success"] = True
        return result

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        result["errors"].append(str(e))
        return result


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("""
SEC Filing Parser - Phases 2 & 3: Data Retrieval & Extraction

Usage:
    python main.py TICKER [TICKER2] [TICKER3] ...

Examples:
    python main.py NVDA                    # Process NVIDIA
    python main.py AAPL MSFT GOOG TSLA     # Process multiple tickers

This will:
1. Validate the ticker symbol
2. Retrieve CIK from SEC Edgar
3. Fetch 10-K/10-Q filing metadata for past 3 years
4. Identify which filings have XBRL data available
5. Extract all XBRL financial metrics from SEC API
6. Calculate year-over-year changes
7. Assign confidence scores to all metrics

Output:
- Filing metadata with XBRL URLs
- All financial metrics (615 metrics available)
- JSON file with metrics, confidence scores, and YoY analysis
- Processing logs stored in data/{TICKER}/logs/
- Metrics JSON stored in data/{TICKER}/parsed/
        """)
        sys.exit(1)

    tickers = sys.argv[1:]

    print(f"\n{'=' * 70}")
    print(f"SEC Filing Parser")
    print(f"{'=' * 70}")
    print(f"Processing {len(tickers)} ticker(s): {', '.join(tickers)}")
    print(f"{'=' * 70}\n")

    # Process each ticker
    all_results = {}
    for ticker in tickers:
        result = process_ticker(ticker)
        all_results[ticker.upper()] = result

        # Print summary
        print(f"\n{ticker.upper()} Results:")
        print(f"  Success: {result['success']}")
        print(f"  CIK: {result['cik']}")
        print(f"  Filings found: {result['filings_found']}")
        print(f"  XBRL available: {result['xbrl_available']}")
        print(f"  Metrics extracted: {result['metrics_extracted']}")
        if result['xbrl_unavailable'] > 0:
            print(f"  XBRL unavailable: {result['xbrl_unavailable']}")
        if result['errors']:
            print(f"  Errors:")
            for error in result['errors']:
                print(f"    - {error}")

    # Final summary
    print(f"\n{'=' * 70}")
    print("FINAL SUMMARY")
    print(f"{'=' * 70}")

    successful = sum(1 for r in all_results.values() if r['success'])
    total_xbrl = sum(r['xbrl_available'] for r in all_results.values())
    total_metrics = sum(r.get('metrics_extracted', 0) for r in all_results.values())

    print(f"Tickers processed: {successful}/{len(tickers)}")
    print(f"Filings with XBRL data: {total_xbrl}")
    print(f"Metrics extracted: {total_metrics}")
    print(f"Data stored in: {config.DATA_DIR}/")
    print(f"{'=' * 70}\n")

    sys.exit(0 if successful == len(tickers) else 1)


if __name__ == "__main__":
    main()
