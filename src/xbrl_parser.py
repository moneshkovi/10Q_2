"""XBRL data extraction and parsing module.

This module provides functionality to:
- Fetch XBRL financial data from SEC Edgar API
- Extract all available metrics
- Parse and structure the data
- Assign confidence scores
- Calculate year-over-year comparisons

All data is fetched from the live SEC API (no mocking).
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import requests

import config

logger = logging.getLogger(__name__)


# ============================================================================
# XBRL PARSER
# ============================================================================

class XBRLParser:
    """Parser for SEC Edgar XBRL financial data.

    Fetches and extracts financial metrics from the SEC's XBRL API,
    with confidence scoring and year-over-year analysis.

    Attributes:
        headers: HTTP headers for SEC API requests
        cache: In-memory cache of fetched XBRL data
    """

    def __init__(self):
        """Initialize XBRL parser with SEC API headers."""
        self.headers = {
            'User-Agent': config.USER_AGENT,
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate',
        }
        self.cache: Dict[str, Dict] = {}
        logger.info("XBRLParser initialized")

    def fetch_xbrl_data(self, cik: str) -> Optional[Dict]:
        """Fetch XBRL company facts from SEC API.

        Args:
            cik: Company CIK (10-digit zero-padded string)

        Returns:
            Company facts dict with all metrics, or None if fetch fails.

        Raises:
            No exceptions; logs errors and returns None.
        """
        # Check cache first
        if cik in self.cache:
            logger.debug(f"Using cached XBRL data for CIK {cik}")
            return self.cache[cik]

        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        logger.info(f"Fetching XBRL data from SEC API for CIK {cik}")

        try:
            response = requests.get(url, headers=self.headers, timeout=60)
            response.raise_for_status()

            data = response.json()
            self.cache[cik] = data
            logger.info(f"Retrieved XBRL data: {len(data.get('facts', {}))} taxonomies")
            return data

        except requests.RequestException as e:
            logger.error(f"Failed to fetch XBRL data: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse XBRL JSON: {e}")
            return None

    def extract_metrics_for_filings(
        self,
        cik: str,
        filings: List[Dict],
        lookback_years: int = 3
    ) -> Dict[str, Any]:
        """Extract all XBRL metrics for specific filings.

        Args:
            cik: Company CIK
            filings: List of filing dicts from Phase 2 (must have accession_number, fiscal_period_end)
            lookback_years: Number of years to include

        Returns:
            Dict with extracted metrics, confidence scores, and YoY comparisons.
        """
        # Fetch raw XBRL data
        xbrl_data = self.fetch_xbrl_data(cik)
        if not xbrl_data:
            logger.error(f"Could not fetch XBRL data for CIK {cik}")
            return {"error": "Failed to fetch XBRL data", "metrics": {}}

        entity_name = xbrl_data.get('entityName', 'Unknown')
        logger.info(f"Extracting metrics for {entity_name} ({len(filings)} filings)")

        # Get all facts
        facts = xbrl_data.get('facts', {})
        us_gaap = facts.get('us-gaap', {})

        logger.info(f"Processing {len(us_gaap)} US-GAAP metrics")

        # Build mapping of accession → filing data for quick lookup
        accession_map = {f['accession_number']: f for f in filings}

        # Extract all metrics
        all_metrics = {}
        extracted_count = 0

        for metric_name, metric_data in us_gaap.items():
            units = metric_data.get('units', {})

            # For each unit type, extract values
            for unit_type, values in units.items():
                if not values:
                    continue

                # Filter values to relevant filings and lookback period
                relevant_values = self._filter_metric_values(
                    values,
                    accession_map,
                    lookback_years
                )

                if relevant_values:
                    metric_key = f"{metric_name}:{unit_type}"
                    all_metrics[metric_key] = {
                        'name': metric_name,
                        'unit': unit_type,
                        'values': relevant_values,
                        'confidence': self._calculate_confidence(relevant_values),
                        'yoy_change': self._calculate_yoy_change(relevant_values)
                    }
                    extracted_count += 1

        logger.info(f"Extracted {extracted_count} metrics with values from filings")

        return {
            'cik': cik,
            'entity_name': entity_name,
            'filings_processed': len(filings),
            'metrics_extracted': extracted_count,
            'metrics': all_metrics,
            'extraction_date': datetime.now().isoformat(),
            'lookback_years': lookback_years
        }

    def _filter_metric_values(
        self,
        values: List[Dict],
        accession_map: Dict[str, Dict],
        lookback_years: int
    ) -> List[Dict]:
        """Filter metric values to relevant filings and timeframe.

        Args:
            values: List of all values for a metric
            accession_map: Dict mapping accession → filing info
            lookback_years: Number of years to include

        Returns:
            Filtered list of relevant values with enhanced metadata.
        """
        filtered = []
        cutoff_date = datetime.now().replace(year=datetime.now().year - lookback_years)

        for value in values:
            # Must have filing date or accession to verify relevance
            accn = value.get('accn')
            filed_date_str = value.get('filed')

            if not accn and not filed_date_str:
                continue

            # Parse filing date
            try:
                if filed_date_str:
                    filed_date = datetime.strptime(filed_date_str, '%Y-%m-%d')
                else:
                    # Estimate from accession number if needed
                    continue
            except (ValueError, TypeError):
                continue

            # Check if within lookback period
            if filed_date < cutoff_date:
                continue

            # Check if this is one of our target filings
            if accn in accession_map:
                filing_info = accession_map[accn]
                # Enhance value with filing context
                enhanced_value = {
                    **value,
                    'filing_type': filing_info.get('form_type'),
                    'filing_date': filing_info.get('filing_date'),
                    'in_target_filing': True
                }
                filtered.append(enhanced_value)

        return filtered

    def _calculate_confidence(self, values: List[Dict]) -> float:
        """Calculate confidence score for a metric based on data quality.

        Confidence scoring:
        - 100: Found in target filing (accession matches Phase 2)
        - 95:  Found but no accession match (from same period)
        - 50:  Calculated or inferred
        - 0:   Missing or invalid

        Args:
            values: List of values for the metric

        Returns:
            Confidence score (0-100).
        """
        if not values:
            return 0.0

        # All values from target filings = high confidence
        if all(v.get('in_target_filing') for v in values):
            return 100.0

        # Some values from target filings = good confidence
        target_count = sum(1 for v in values if v.get('in_target_filing'))
        if target_count > 0:
            return min(95.0, 50.0 + (target_count / len(values)) * 50)

        # Default
        return 50.0

    def _calculate_yoy_change(self, values: List[Dict]) -> Optional[Dict]:
        """Calculate year-over-year change in metric values.

        Args:
            values: List of values sorted by date

        Returns:
            Dict with YoY comparisons, or None if insufficient data.
        """
        if len(values) < 2:
            return None

        # Sort by filing date (most recent first)
        sorted_values = sorted(
            values,
            key=lambda x: x.get('filed', ''),
            reverse=True
        )

        # Find comparable periods (same quarter or full year)
        yoy_changes = []

        for i, current in enumerate(sorted_values):
            current_val = current.get('val')
            current_period = current.get('fp', '')  # FY, Q1, Q2, etc.
            current_fy = current.get('fy')

            if not current_val or current_val == 0:
                continue

            # Find prior year equivalent
            for prior in sorted_values[i+1:]:
                prior_val = prior.get('val')
                prior_period = prior.get('fp', '')
                prior_fy = prior.get('fy')

                # Match period type and check if one year prior
                if (prior_period == current_period and
                    prior_fy and current_fy and
                    current_fy - prior_fy == 1 and
                    prior_val and prior_val != 0):

                    change_pct = ((current_val - prior_val) / abs(prior_val)) * 100

                    yoy_changes.append({
                        'period': current_period,
                        'current_year': current_fy,
                        'prior_year': prior_fy,
                        'current_value': current_val,
                        'prior_value': prior_val,
                        'change_percent': round(change_pct, 2)
                    })
                    break

        return {'yoy_comparisons': yoy_changes} if yoy_changes else None

    def save_metrics_to_json(
        self,
        metrics_data: Dict[str, Any],
        output_path: Path
    ) -> bool:
        """Save extracted metrics to JSON file.

        Args:
            metrics_data: Dict with metrics and metadata
            output_path: Path where to save the JSON file

        Returns:
            True if successful, False otherwise.
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Pretty print the JSON
            with open(output_path, 'w') as f:
                json.dump(metrics_data, f, indent=2, default=str)

            file_size_kb = output_path.stat().st_size / 1024
            logger.info(f"Saved metrics to {output_path} ({file_size_kb:.1f} KB)")
            return True

        except Exception as e:
            logger.error(f"Failed to save metrics JSON: {e}")
            return False
