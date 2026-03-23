"""
Alpaca Market Data Client

Fetches live and historical market data from the Alpaca API (free tier).

Provides:
- Latest stock price (snapshot)
- Historical daily bars (OHLCV)
- OLS beta calculation vs SPY (252-day lookback)

Free tier uses IEX feed (~1-min delay, 200 req/min).
Market data URL: https://data.alpaca.markets/v2 (NOT paper-api).

All public methods return None / [] on any failure so the pipeline
never crashes due to market data unavailability.

Source: https://docs.alpaca.markets/reference/stocksnapshotsingle
"""

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import requests

import config

logger = logging.getLogger(__name__)


class AlpacaClient:
    """
    Client for Alpaca Markets Data API v2.

    Attributes:
        enabled: False if API keys are not configured — all methods return
                 None / [] silently so the pipeline degrades gracefully.
    """

    def __init__(self):
        """Initialize client; mark disabled if credentials are absent."""
        self.enabled = bool(config.ALPACA_API_KEY and config.ALPACA_SECRET_KEY)
        self._base = config.ALPACA_DATA_URL.rstrip("/")
        self._session = requests.Session()
        if self.enabled:
            self._session.headers.update({
                "APCA-API-KEY-ID": config.ALPACA_API_KEY,
                "APCA-API-SECRET-KEY": config.ALPACA_SECRET_KEY,
            })

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    def get_latest_price(self, ticker: str) -> Optional[float]:
        """
        Return the most recent trade price for a US-listed ticker.

        Uses the snapshot endpoint which returns the latest trade, quote,
        and daily bar in one call.

        Args:
            ticker: NYSE / NASDAQ ticker (e.g. "NVDA", "AZN" for ADR).

        Returns:
            Latest trade price as float, or None if unavailable.
        """
        snapshot = self.get_snapshot(ticker)
        if not snapshot:
            return None
        try:
            return float(snapshot["latestTrade"]["p"])
        except (KeyError, TypeError, ValueError):
            return None

    def get_snapshot(self, ticker: str) -> Optional[Dict]:
        """
        Return full market snapshot for a ticker.

        Response includes latestTrade (price, size), latestQuote (bid/ask),
        dailyBar (OHLCV today), prevDailyBar (OHLCV yesterday).

        Args:
            ticker: Stock ticker symbol.

        Returns:
            Snapshot dict, or None if ticker is not available on Alpaca.
        """
        if not self.enabled:
            return None
        try:
            url = f"{self._base}/stocks/{ticker.upper()}/snapshot"
            resp = self._session.get(url, timeout=10)
            if resp.status_code == 404:
                logger.debug(f"Alpaca: {ticker} not found (404) — not on Alpaca feed")
                return None
            resp.raise_for_status()
            data = resp.json()
            return data.get("snapshot") or data
        except Exception as e:
            logger.debug(f"Alpaca snapshot failed for {ticker}: {e}")
            return None

    def get_historical_bars(self, ticker: str,
                            lookback_days: int = 365) -> List[Dict]:
        """
        Fetch daily OHLCV bars for a ticker.

        Args:
            ticker: Stock ticker symbol.
            lookback_days: Number of calendar days to look back.

        Returns:
            List of bar dicts with keys: t (timestamp), o, h, l, c, v, vw.
            Empty list on failure.
        """
        if not self.enabled:
            return []
        try:
            start = (datetime.now(timezone.utc) - timedelta(days=lookback_days))
            params = {
                "timeframe": "1Day",
                "start": start.strftime("%Y-%m-%dT00:00:00Z"),
                "adjustment": "split",
                "limit": 1000,
            }
            bars: List[Dict] = []
            url = f"{self._base}/stocks/{ticker.upper()}/bars"
            while url:
                resp = self._session.get(url, params=params, timeout=15)
                if resp.status_code == 404:
                    logger.debug(f"Alpaca: {ticker} bars not found (404)")
                    return []
                resp.raise_for_status()
                data = resp.json()
                page_bars = data.get("bars", [])
                bars.extend(page_bars)
                next_token = data.get("next_page_token")
                if next_token:
                    params = {"page_token": next_token}
                else:
                    break
            logger.debug(f"Alpaca: fetched {len(bars)} daily bars for {ticker}")
            return bars
        except Exception as e:
            logger.debug(f"Alpaca bars failed for {ticker}: {e}")
            return []

    def calculate_beta(self, ticker: str,
                       lookback_days: int = 252) -> Optional[float]:
        """
        Compute OLS beta for ticker vs SPY over the last lookback_days trading days.

        Formula: beta = Cov(stock_returns, spy_returns) / Var(spy_returns)

        Uses daily log returns: r_t = ln(close_t / close_{t-1})

        Args:
            ticker: Stock ticker symbol.
            lookback_days: Calendar days of history to use (252 ≈ 1 trading year).

        Returns:
            Beta as float (e.g. 1.65 for NVDA), or None if insufficient data
            (<30 overlapping trading days) or ticker unavailable.
        """
        if not self.enabled:
            return None
        try:
            # Fetch slightly more history to ensure enough trading days
            calendar_days = lookback_days + 120
            stock_bars = self.get_historical_bars(ticker, calendar_days)
            spy_bars = self.get_historical_bars("SPY", calendar_days)

            if not stock_bars or not spy_bars:
                return None

            # Build close price maps keyed by date string (YYYY-MM-DD)
            stock_closes = {b["t"][:10]: b["c"] for b in stock_bars}
            spy_closes = {b["t"][:10]: b["c"] for b in spy_bars}

            # Find common dates, sorted ascending
            common_dates = sorted(set(stock_closes) & set(spy_closes))
            if len(common_dates) < 31:  # need at least 30 return pairs
                logger.debug(f"Alpaca: insufficient overlapping dates for {ticker} beta")
                return None

            # Compute daily log returns on common dates
            stock_returns = []
            spy_returns = []
            for i in range(1, len(common_dates)):
                d_cur = common_dates[i]
                d_prev = common_dates[i - 1]
                s0, s1 = stock_closes[d_prev], stock_closes[d_cur]
                m0, m1 = spy_closes[d_prev], spy_closes[d_cur]
                if s0 > 0 and s1 > 0 and m0 > 0 and m1 > 0:
                    stock_returns.append(math.log(s1 / s0))
                    spy_returns.append(math.log(m1 / m0))

            if len(stock_returns) < 30:
                return None

            n = len(stock_returns)
            mean_s = sum(stock_returns) / n
            mean_m = sum(spy_returns) / n

            cov = sum((s - mean_s) * (m - mean_m)
                      for s, m in zip(stock_returns, spy_returns)) / (n - 1)
            var_m = sum((m - mean_m) ** 2 for m in spy_returns) / (n - 1)

            if var_m == 0:
                return None

            beta = cov / var_m
            # Sanity-clamp: betas outside [-1, 5] are almost certainly data artefacts
            beta = max(-1.0, min(5.0, beta))
            logger.info(f"Alpaca: computed beta for {ticker} = {beta:.3f} "
                        f"({n} trading days)")
            return round(beta, 3)

        except Exception as e:
            logger.debug(f"Alpaca beta calculation failed for {ticker}: {e}")
            return None
