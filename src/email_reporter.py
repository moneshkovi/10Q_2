"""
Email Reporter for SEC Filing Parser

Sends pipeline results via Gmail SMTP after each run:
- Success: HTML table with DCF fair value, current price, premium/discount
  per ticker + attached per-ticker calculated_metrics.csv files
- Failure: Alert email with ticker and error message

Uses Gmail app password (generate at myaccount.google.com/apppasswords).
SMTP: smtp.gmail.com:587, STARTTLS.

If EMAIL_ADDRESS or EMAIL_APP_PASSWORD are not configured, all methods
return False silently — pipeline runs without email.
"""

import logging
import smtplib
import ssl
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Optional

import config

logger = logging.getLogger(__name__)

# 1 MB attachment size limit per file
_MAX_ATTACHMENT_BYTES = 1 * 1024 * 1024


class EmailReporter:
    """
    Gmail SMTP email reporter.

    Attributes:
        enabled: True only when EMAIL_ADDRESS and EMAIL_APP_PASSWORD are set.
    """

    def __init__(self):
        self.enabled = bool(config.EMAIL_ADDRESS and config.EMAIL_APP_PASSWORD)
        if not self.enabled:
            logger.debug("EmailReporter: credentials not configured — email disabled")

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    def send_dcf_report(self, all_results: Dict, output_base_dir: Path) -> bool:
        """
        Send a DCF summary report after a successful pipeline run.

        Subject: "SEC Filing Parser — Results: NVDA, AAPL, MSFT"
        Body:    HTML table (Ticker | Fair Value | Current Price | Premium | WACC | Beta)
        Attachments: {ticker}_calculated_metrics.csv (skipped if > 1 MB or missing)

        Args:
            all_results: dict of ticker → result dict from main pipeline
            output_base_dir: config.DATA_DIR (parent of per-ticker directories)

        Returns:
            True if email sent successfully, False otherwise.
        """
        if not self.enabled:
            return False
        try:
            tickers = sorted(all_results.keys())
            subject = f"SEC Filing Parser — Results: {', '.join(tickers)}"
            body = self._build_report_html(all_results)

            attachments = self._collect_attachments(tickers, output_base_dir)
            return self._send(subject, body, attachments)

        except Exception as e:
            logger.error(f"EmailReporter: failed to send report — {e}", exc_info=True)
            return False

    def send_error_alert(self, ticker: str, error: str) -> bool:
        """
        Send a failure alert when the pipeline fails for a ticker.

        Subject: "SEC Filing Parser — FAILED: AZN"
        Body:    Ticker, error message, timestamp

        Args:
            ticker: Ticker that failed.
            error:  Error message / traceback summary.

        Returns:
            True if email sent successfully, False otherwise.
        """
        if not self.enabled:
            return False
        try:
            subject = f"SEC Filing Parser — FAILED: {ticker.upper()}"
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            body = f"""
<html><body style="font-family:sans-serif;color:#333;">
<h2 style="color:#c0392b;">Pipeline Failure Alert</h2>
<table cellpadding="6" style="border-collapse:collapse;">
  <tr><td><b>Ticker</b></td><td>{ticker.upper()}</td></tr>
  <tr><td><b>Timestamp</b></td><td>{timestamp}</td></tr>
  <tr><td style="vertical-align:top"><b>Error</b></td>
      <td><pre style="background:#f8f8f8;padding:8px;border-radius:4px;">{error}</pre></td></tr>
</table>
</body></html>
"""
            return self._send(subject, body)
        except Exception as e:
            logger.error(f"EmailReporter: failed to send alert — {e}", exc_info=True)
            return False

    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================

    def _build_report_html(self, all_results: Dict) -> str:
        """Build the HTML body for the DCF summary report."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        successful = sum(1 for r in all_results.values() if r.get("success"))
        total = len(all_results)

        rows = []
        for ticker, r in sorted(all_results.items()):
            if not r.get("success"):
                row = f"""
  <tr style="background:#fef9f9;">
    <td><b>{ticker}</b></td>
    <td colspan="6" style="color:#c0392b;">FAILED — {r.get('errors', ['Unknown'])[0]}</td>
  </tr>"""
                rows.append(row)
                continue

            fair_value = r.get("dcf_fair_value")
            current_price = r.get("current_price")
            premium_pct = r.get("dcf_premium_pct")
            wacc = r.get("dcf_wacc")
            beta = r.get("computed_beta")
            quality = r.get("quality_score", 0)

            fv_str = f"${fair_value:.2f}" if fair_value else "—"
            cp_str = f"${current_price:.2f}" if current_price else "—"

            if premium_pct is not None:
                sign = "+" if premium_pct >= 0 else ""
                label = "UNDERVALUED" if premium_pct > 0 else "OVERVALUED"
                color = "#27ae60" if premium_pct > 0 else "#c0392b"
                prem_str = f'<span style="color:{color};">{sign}{premium_pct:.1f}% {label}</span>'
            else:
                prem_str = "—"

            wacc_str = f"{wacc:.2%}" if wacc else "—"
            beta_str = f"{beta:.2f}" if beta else "—"
            quality_color = "#27ae60" if quality >= 80 else "#e67e22" if quality >= 50 else "#c0392b"

            row = f"""
  <tr>
    <td><b>{ticker}</b></td>
    <td>{fv_str}</td>
    <td>{cp_str}</td>
    <td>{prem_str}</td>
    <td>{wacc_str}</td>
    <td>{beta_str}</td>
    <td style="color:{quality_color};">{quality}/100</td>
  </tr>"""
            rows.append(row)

        rows_html = "\n".join(rows)

        return f"""
<html>
<body style="font-family:sans-serif;color:#333;max-width:900px;margin:0 auto;">
  <h2 style="color:#2c3e50;">SEC Filing Parser — DCF Results</h2>
  <p style="color:#7f8c8d;">{timestamp} &nbsp;|&nbsp; {successful}/{total} tickers successful</p>

  <table style="border-collapse:collapse;width:100%;font-size:14px;">
    <thead>
      <tr style="background:#2c3e50;color:white;">
        <th style="padding:8px 12px;text-align:left;">Ticker</th>
        <th style="padding:8px 12px;text-align:right;">DCF Fair Value</th>
        <th style="padding:8px 12px;text-align:right;">Current Price</th>
        <th style="padding:8px 12px;text-align:center;">Premium / Discount</th>
        <th style="padding:8px 12px;text-align:right;">WACC</th>
        <th style="padding:8px 12px;text-align:right;">Beta</th>
        <th style="padding:8px 12px;text-align:right;">Quality</th>
      </tr>
    </thead>
    <tbody>
{rows_html}
    </tbody>
  </table>

  <p style="color:#95a5a6;font-size:12px;margin-top:24px;">
    Generated by SEC Filing Parser &nbsp;|&nbsp;
    Data: SEC EDGAR XBRL + Alpaca Markets &nbsp;|&nbsp;
    DCF methodology: Unlevered FCFF (OCF method preferred)
  </p>
</body>
</html>
"""

    def _collect_attachments(self, tickers: List[str],
                             output_base_dir: Path) -> List[Path]:
        """Collect calculated_metrics.csv files for each ticker (≤1 MB each)."""
        attachments = []
        for ticker in tickers:
            path = output_base_dir / ticker.upper() / "parsed" / \
                   f"{ticker.upper()}_calculated_metrics.csv"
            if not path.exists():
                logger.debug(f"EmailReporter: attachment not found — {path}")
                continue
            size = path.stat().st_size
            if size > _MAX_ATTACHMENT_BYTES:
                logger.debug(f"EmailReporter: skipping {path.name} "
                             f"(size {size/1024:.0f} KB > 1 MB limit)")
                continue
            attachments.append(path)
        return attachments

    def _send(self, subject: str, body_html: str,
              attachments: Optional[List[Path]] = None) -> bool:
        """
        Send an HTML email via Gmail SMTP (STARTTLS on port 587).

        Args:
            subject:     Email subject line.
            body_html:   HTML body string.
            attachments: Optional list of file paths to attach.

        Returns:
            True on success, False on failure.
        """
        if attachments is None:
            attachments = []

        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"] = config.EMAIL_ADDRESS
        msg["To"] = config.EMAIL_ADDRESS  # report delivered to same address

        msg.attach(MIMEText(body_html, "html"))

        for path in attachments:
            try:
                with open(path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f'attachment; filename="{path.name}"',
                )
                msg.attach(part)
            except Exception as e:
                logger.warning(f"EmailReporter: could not attach {path.name} — {e}")

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(config.EMAIL_SMTP_HOST,
                              config.EMAIL_SMTP_PORT) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(config.EMAIL_ADDRESS, config.EMAIL_APP_PASSWORD)
                server.send_message(msg)

            logger.info(f"EmailReporter: sent '{subject}' to {config.EMAIL_ADDRESS}")
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error("EmailReporter: SMTP authentication failed — "
                         "check EMAIL_APP_PASSWORD in .env")
            return False
        except Exception as e:
            logger.error(f"EmailReporter: SMTP send failed — {e}", exc_info=True)
            return False
