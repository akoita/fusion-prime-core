"""
Email notification channel using SendGrid.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from app.models.notification import MarginAlert, NotificationStatus

logger = logging.getLogger(__name__)


class EmailChannel:
    """
    Email notification delivery via SendGrid.

    Sends margin alerts and other notifications via email.
    """

    def __init__(self, sendgrid_api_key: Optional[str] = None, from_email: Optional[str] = None):
        """
        Initialize email channel.

        Args:
            sendgrid_api_key: SendGrid API key (or from SENDGRID_API_KEY env var)
            from_email: From email address (or from FROM_EMAIL env var)
        """
        self.api_key = sendgrid_api_key or os.getenv("SENDGRID_API_KEY")
        self.from_email = from_email or os.getenv("FROM_EMAIL", "alerts@fusionprime.io")
        self.enabled = bool(self.api_key)

        if not self.enabled:
            logger.warning("SendGrid API key not configured, email notifications disabled")
        else:
            logger.info(f"Email channel initialized (from: {self.from_email})")

    async def send_margin_alert(self, alert: MarginAlert, to_email: str) -> Dict[str, Any]:
        """
        Send margin alert via email.

        Args:
            alert: Margin alert to send
            to_email: Recipient email address

        Returns:
            Delivery result with status and metadata
        """
        if not self.enabled:
            logger.warning("Email channel not enabled, skipping send")
            return {"status": NotificationStatus.FAILED, "error": "Email channel not configured"}

        try:
            # Build email content
            subject = self._build_subject(alert)
            html_content = self._build_html_content(alert)
            text_content = self._build_text_content(alert)

            # Send via SendGrid
            # NOTE: Actual SendGrid integration would go here
            # For now, just log
            logger.info(
                f"Sending margin alert email to {to_email}: "
                f"{alert.event_type} (severity: {alert.severity})"
            )

            # Simulated send
            # In production:
            # from sendgrid import SendGridAPIClient
            # from sendgrid.helpers.mail import Mail
            # message = Mail(
            #     from_email=self.from_email,
            #     to_emails=to_email,
            #     subject=subject,
            #     html_content=html_content,
            #     plain_text_content=text_content
            # )
            # sg = SendGridAPIClient(self.api_key)
            # response = sg.send(message)

            return {
                "status": NotificationStatus.SENT,
                "channel": "email",
                "to": to_email,
                "subject": subject,
                "sent_at": datetime.utcnow().isoformat() + "Z",
                "simulated": True,  # Remove in production
            }

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return {
                "status": NotificationStatus.FAILED,
                "channel": "email",
                "error": str(e),
                "to": to_email,
            }

    def _build_subject(self, alert: MarginAlert) -> str:
        """Build email subject line."""
        severity_emoji = {"low": "ℹ️", "medium": "⚠️", "high": "🚨", "critical": "🔴"}

        emoji = severity_emoji.get(alert.severity.lower(), "📢")

        subject_map = {
            "margin_warning": f"{emoji} Margin Warning - Health at {alert.health_score:.1f}%",
            "margin_call": f"{emoji} MARGIN CALL - Urgent Action Required",
            "liquidation_imminent": f"{emoji} LIQUIDATION IMMINENT - Immediate Action Required",
        }

        return subject_map.get(alert.event_type, f"{emoji} Margin Alert - {alert.event_type}")

    def _build_html_content(self, alert: MarginAlert) -> str:
        """Build HTML email content."""
        # Color coding by severity
        color_map = {
            "low": "#3b82f6",  # blue
            "medium": "#f59e0b",  # amber
            "high": "#ef4444",  # red
            "critical": "#dc2626",  # dark red
        }

        color = color_map.get(alert.severity.lower(), "#6b7280")

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: {color}; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9fafb; padding: 20px; border-radius: 0 0 8px 8px; }}
        .metric {{ background: white; padding: 15px; margin: 10px 0; border-radius: 4px; border-left: 4px solid {color}; }}
        .metric-label {{ font-size: 12px; color: #6b7280; text-transform: uppercase; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: {color}; }}
        .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #e5e7eb; font-size: 12px; color: #6b7280; }}
        .action-button {{ display: inline-block; background: {color}; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; margin-top: 15px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2 style="margin: 0;">{alert.message}</h2>
            <p style="margin: 5px 0 0 0;">User: {alert.user_id}</p>
        </div>

        <div class="content">
            <div class="metric">
                <div class="metric-label">Health Score</div>
                <div class="metric-value">{alert.health_score:.2f}%</div>
                <div style="font-size: 14px; color: #6b7280; margin-top: 5px;">
                    Status: {alert.status}
                </div>
            </div>

            <div class="metric">
                <div class="metric-label">Collateral Value (USD)</div>
                <div class="metric-value">${alert.total_collateral_usd:,.2f}</div>
            </div>

            <div class="metric">
                <div class="metric-label">Borrow Value (USD)</div>
                <div class="metric-value">${alert.total_borrow_usd:,.2f}</div>
            </div>

            <div class="metric">
                <div class="metric-label">Liquidation Price Drop</div>
                <div class="metric-value">{alert.liquidation_price_drop_percent:.2f}%</div>
                <div style="font-size: 14px; color: #6b7280; margin-top: 5px;">
                    Collateral can drop this much before liquidation
                </div>
            </div>

            <h3>Recommended Actions:</h3>
            <ul>
                <li>Add more collateral to your account</li>
                <li>Reduce your borrow positions</li>
                <li>Monitor your position closely</li>
            </ul>

            <a href="#" class="action-button">View Dashboard</a>
        </div>

        <div class="footer">
            <p>This is an automated alert from Fusion Prime Risk Engine.</p>
            <p>Alert triggered at: {alert.timestamp}</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    def _build_text_content(self, alert: MarginAlert) -> str:
        """Build plain text email content."""
        text = f"""
MARGIN ALERT: {alert.message}

User: {alert.user_id}
Event Type: {alert.event_type}
Severity: {alert.severity.upper()}

=== Position Details ===
Health Score: {alert.health_score:.2f}%
Status: {alert.status}

Collateral Value: ${alert.total_collateral_usd:,.2f}
Borrow Value: ${alert.total_borrow_usd:,.2f}

Liquidation Price Drop: {alert.liquidation_price_drop_percent:.2f}%
(Your collateral can drop this much before liquidation)

=== Recommended Actions ===
- Add more collateral to your account
- Reduce your borrow positions
- Monitor your position closely

---
This is an automated alert from Fusion Prime Risk Engine.
Alert triggered at: {alert.timestamp}

To manage your positions, visit the Fusion Prime dashboard.
"""
        return text
