"""Tests for EmailReporter.

All tests mock smtplib — no real emails sent.
"""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile

import config


def _make_result(ticker: str, success: bool = True, fair_value: float = 150.0,
                 current_price: float = 120.0, wacc: float = 0.10) -> dict:
    """Build a minimal pipeline result dict."""
    if not success:
        return {"success": False, "errors": ["Phase 3 failed: timeout"]}
    premium = (fair_value - current_price) / current_price * 100
    return {
        "success": True,
        "cik": "0001234567",
        "dcf_generated": True,
        "dcf_fair_value": fair_value,
        "dcf_wacc": wacc,
        "current_price": current_price,
        "computed_beta": 1.20,
        "dcf_premium_pct": premium,
        "quality_score": 85,
        "metrics_extracted": 275,
        "errors": [],
    }


class TestEmailReporterDisabled(unittest.TestCase):
    """EmailReporter disabled when credentials not configured."""

    def test_disabled_when_no_credentials(self):
        with patch.object(config, "EMAIL_ADDRESS", ""), \
             patch.object(config, "EMAIL_APP_PASSWORD", ""):
            from src.email_reporter import EmailReporter
            reporter = EmailReporter()
            self.assertFalse(reporter.enabled)

    def test_send_report_returns_false_when_disabled(self):
        with patch.object(config, "EMAIL_ADDRESS", ""), \
             patch.object(config, "EMAIL_APP_PASSWORD", ""):
            from src.email_reporter import EmailReporter
            reporter = EmailReporter()
            result = reporter.send_dcf_report({"NVDA": _make_result("NVDA")}, Path("/tmp"))
            self.assertFalse(result)

    def test_send_alert_returns_false_when_disabled(self):
        with patch.object(config, "EMAIL_ADDRESS", ""), \
             patch.object(config, "EMAIL_APP_PASSWORD", ""):
            from src.email_reporter import EmailReporter
            reporter = EmailReporter()
            result = reporter.send_error_alert("NVDA", "Something broke")
            self.assertFalse(result)


class TestEmailReporterSend(unittest.TestCase):
    """Test SMTP send behaviour with mocked credentials."""

    def setUp(self):
        self.addr_patch = patch.object(config, "EMAIL_ADDRESS", "test@example.com")
        self.pass_patch = patch.object(config, "EMAIL_APP_PASSWORD", "app_password_123")
        self.addr_patch.start()
        self.pass_patch.start()
        from src.email_reporter import EmailReporter
        self.reporter = EmailReporter()

    def tearDown(self):
        self.addr_patch.stop()
        self.pass_patch.stop()

    @patch("smtplib.SMTP")
    def test_send_report_calls_smtp(self, mock_smtp_class):
        """send_dcf_report calls smtplib.SMTP and send_message."""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        result = self.reporter.send_dcf_report(
            {"NVDA": _make_result("NVDA")}, Path("/tmp")
        )
        self.assertTrue(result)
        mock_server.send_message.assert_called_once()

    @patch("smtplib.SMTP")
    def test_send_alert_subject_contains_failed(self, mock_smtp_class):
        """send_error_alert uses 'FAILED' in subject."""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        self.reporter.send_error_alert("AZN", "DCF pipeline crashed")
        mock_server.send_message.assert_called_once()
        msg = mock_server.send_message.call_args[0][0]
        self.assertIn("FAILED", msg["Subject"])
        self.assertIn("AZN", msg["Subject"])

    @patch("smtplib.SMTP")
    def test_missing_attachment_skipped_gracefully(self, mock_smtp_class):
        """send_dcf_report succeeds even when CSV attachment file doesn't exist."""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        # Pass a nonexistent base dir — attachment collection returns []
        result = self.reporter.send_dcf_report(
            {"NVDA": _make_result("NVDA")},
            Path("/nonexistent/path/that/does/not/exist")
        )
        self.assertTrue(result)  # should still send (just without attachment)

    @patch("smtplib.SMTP")
    def test_failed_ticker_included_in_report(self, mock_smtp_class):
        """Failed tickers are included in the report body."""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        results = {
            "NVDA": _make_result("NVDA", success=True),
            "FAKE": _make_result("FAKE", success=False),
        }
        result = self.reporter.send_dcf_report(results, Path("/tmp"))
        self.assertTrue(result)
        msg = mock_server.send_message.call_args[0][0]
        # Subject should list both tickers
        self.assertIn("FAKE", msg["Subject"])
        self.assertIn("NVDA", msg["Subject"])

    @patch("smtplib.SMTP")
    def test_attachment_included_when_file_exists(self, mock_smtp_class):
        """A real CSV file is attached when it exists and is small enough."""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create the expected directory + file structure
            parsed_dir = Path(tmpdir) / "NVDA" / "parsed"
            parsed_dir.mkdir(parents=True)
            csv_path = parsed_dir / "NVDA_calculated_metrics.csv"
            csv_path.write_text("Type,Metric,Value\nMargin,Gross,0.71\n")

            result = self.reporter.send_dcf_report(
                {"NVDA": _make_result("NVDA")}, Path(tmpdir)
            )
            self.assertTrue(result)
            msg = mock_server.send_message.call_args[0][0]
            # Message should have 2 parts: body + attachment
            payload = msg.get_payload()
            self.assertGreaterEqual(len(payload), 2)


if __name__ == "__main__":
    unittest.main()
