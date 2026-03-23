"""Tests for AlpacaClient.

All tests mock the Alpaca API — no real network calls.
"""

import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone

import config


def _make_bar(date_str: str, close: float) -> dict:
    """Helper: create a minimal bar dict."""
    return {"t": f"{date_str}T00:00:00Z", "o": close, "h": close,
            "l": close, "c": close, "v": 1000000, "vw": close}


def _generate_bars(n: int, start_price: float = 100.0,
                   daily_change: float = 0.001) -> list:
    """Generate n synthetic daily bars starting from today-n days."""
    bars = []
    base = datetime.now(timezone.utc) - timedelta(days=n + 30)
    price = start_price
    for i in range(n):
        day = (base + timedelta(days=i)).strftime("%Y-%m-%d")
        bars.append(_make_bar(day, price))
        price *= (1 + daily_change)
    return bars


class TestAlpacaClientDisabled(unittest.TestCase):
    """AlpacaClient disabled when keys not configured."""

    def test_disabled_when_no_keys(self):
        with patch.object(config, "ALPACA_API_KEY", ""), \
             patch.object(config, "ALPACA_SECRET_KEY", ""):
            from src.alpaca_client import AlpacaClient
            client = AlpacaClient()
            self.assertFalse(client.enabled)

    def test_get_latest_price_returns_none_when_disabled(self):
        with patch.object(config, "ALPACA_API_KEY", ""), \
             patch.object(config, "ALPACA_SECRET_KEY", ""):
            from src.alpaca_client import AlpacaClient
            client = AlpacaClient()
            self.assertIsNone(client.get_latest_price("NVDA"))

    def test_get_historical_bars_returns_empty_when_disabled(self):
        with patch.object(config, "ALPACA_API_KEY", ""), \
             patch.object(config, "ALPACA_SECRET_KEY", ""):
            from src.alpaca_client import AlpacaClient
            client = AlpacaClient()
            self.assertEqual(client.get_historical_bars("NVDA"), [])

    def test_calculate_beta_returns_none_when_disabled(self):
        with patch.object(config, "ALPACA_API_KEY", ""), \
             patch.object(config, "ALPACA_SECRET_KEY", ""):
            from src.alpaca_client import AlpacaClient
            client = AlpacaClient()
            self.assertIsNone(client.calculate_beta("NVDA"))


class TestAlpacaGetLatestPrice(unittest.TestCase):
    """Tests for get_latest_price()."""

    def setUp(self):
        # Ensure keys look populated
        self.key_patch = patch.object(config, "ALPACA_API_KEY", "FAKE_KEY")
        self.secret_patch = patch.object(config, "ALPACA_SECRET_KEY", "FAKE_SECRET")
        self.key_patch.start()
        self.secret_patch.start()
        from src.alpaca_client import AlpacaClient
        self.client = AlpacaClient()

    def tearDown(self):
        self.key_patch.stop()
        self.secret_patch.stop()

    def test_get_latest_price_success(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "snapshot": {
                "latestTrade": {"p": 134.50, "s": 100, "t": "2026-03-20T16:00:00Z"},
                "latestQuote": {"ap": 134.55, "bp": 134.45},
                "dailyBar": {"o": 133.0, "h": 135.0, "l": 132.5, "c": 134.50, "v": 5000000},
            }
        }
        self.client._session.get = MagicMock(return_value=mock_resp)
        price = self.client.get_latest_price("NVDA")
        self.assertAlmostEqual(price, 134.50)

    def test_get_latest_price_returns_none_on_404(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        self.client._session.get = MagicMock(return_value=mock_resp)
        self.assertIsNone(self.client.get_latest_price("UNKNOWN"))

    def test_get_latest_price_returns_none_on_exception(self):
        self.client._session.get = MagicMock(side_effect=Exception("network error"))
        self.assertIsNone(self.client.get_latest_price("NVDA"))

    def test_get_snapshot_returns_dict(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "snapshot": {"latestTrade": {"p": 200.0}}
        }
        self.client._session.get = MagicMock(return_value=mock_resp)
        snap = self.client.get_snapshot("AAPL")
        self.assertIsNotNone(snap)
        self.assertIn("latestTrade", snap)


class TestAlpacaHistoricalBars(unittest.TestCase):
    """Tests for get_historical_bars()."""

    def setUp(self):
        self.key_patch = patch.object(config, "ALPACA_API_KEY", "FAKE_KEY")
        self.secret_patch = patch.object(config, "ALPACA_SECRET_KEY", "FAKE_SECRET")
        self.key_patch.start()
        self.secret_patch.start()
        from src.alpaca_client import AlpacaClient
        self.client = AlpacaClient()

    def tearDown(self):
        self.key_patch.stop()
        self.secret_patch.stop()

    def test_get_historical_bars_success(self):
        bars = _generate_bars(50)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"bars": bars, "next_page_token": None}
        self.client._session.get = MagicMock(return_value=mock_resp)
        result = self.client.get_historical_bars("NVDA", lookback_days=60)
        self.assertEqual(len(result), 50)
        self.assertIn("c", result[0])

    def test_get_historical_bars_returns_empty_on_404(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        self.client._session.get = MagicMock(return_value=mock_resp)
        self.assertEqual(self.client.get_historical_bars("UNKNOWN"), [])

    def test_get_historical_bars_returns_empty_on_exception(self):
        self.client._session.get = MagicMock(side_effect=Exception("timeout"))
        self.assertEqual(self.client.get_historical_bars("NVDA"), [])


class TestAlpacaBeta(unittest.TestCase):
    """Tests for calculate_beta()."""

    def setUp(self):
        self.key_patch = patch.object(config, "ALPACA_API_KEY", "FAKE_KEY")
        self.secret_patch = patch.object(config, "ALPACA_SECRET_KEY", "FAKE_SECRET")
        self.key_patch.start()
        self.secret_patch.start()
        from src.alpaca_client import AlpacaClient
        self.client = AlpacaClient()

    def tearDown(self):
        self.key_patch.stop()
        self.secret_patch.stop()

    def test_calculate_beta_success(self):
        """Beta should be a reasonable float when given enough data."""
        stock_bars = _generate_bars(260, start_price=500.0, daily_change=0.002)
        spy_bars = _generate_bars(260, start_price=450.0, daily_change=0.001)

        def mock_get_bars(ticker, lookback_days=365):
            return stock_bars if ticker != "SPY" else spy_bars

        self.client.get_historical_bars = mock_get_bars
        beta = self.client.calculate_beta("NVDA")
        self.assertIsNotNone(beta)
        self.assertGreater(beta, 0.0)
        self.assertLess(beta, 5.0)

    def test_calculate_beta_returns_none_insufficient_data(self):
        """Returns None when fewer than 30 overlapping trading days."""
        # Only 10 bars — not enough
        short_bars = _generate_bars(10)
        self.client.get_historical_bars = lambda ticker, lookback_days=365: short_bars
        self.assertIsNone(self.client.calculate_beta("NVDA"))

    def test_calculate_beta_returns_none_when_bars_unavailable(self):
        """Returns None when bars fetch returns empty list."""
        self.client.get_historical_bars = lambda ticker, lookback_days=365: []
        self.assertIsNone(self.client.calculate_beta("NVDA"))


if __name__ == "__main__":
    unittest.main()
