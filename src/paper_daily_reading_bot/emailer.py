from __future__ import annotations

from email.message import EmailMessage
from typing import Iterable
import re
import smtplib

from paper_daily_reading_bot.config import EmailConfig


class EmailError(RuntimeError):
    """Raised when a report email cannot be sent."""


def send_html_email(config: EmailConfig, subject: str, html: str) -> None:
    recipients = config.resolved_recipients()
    sender = config.resolved_sender()
    smtp_host = config.resolved_smtp_host()
    if not smtp_host:
        raise EmailError("email.smtp_host is required")
    if not sender:
        raise EmailError("email sender is required; set email.sender or SMTP_SENDER")
    if not recipients:
        raise EmailError("email recipients are required; set email.recipients or SMTP_RECIPIENTS")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.set_content(_html_to_text(html))
    msg.add_alternative(html, subtype="html")

    username = config.resolved_username()
    password = config.resolved_password()
    with smtplib.SMTP(smtp_host, config.smtp_port, timeout=30) as smtp:
        smtp.ehlo()
        if config.use_tls:
            smtp.starttls()
            smtp.ehlo()
        if username or password:
            if not (username and password):
                raise EmailError("both SMTP username and password must be configured")
            smtp.login(username, password)
        smtp.send_message(msg)


def _html_to_text(html: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</(p|div|h[1-6]|li|tr)>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())
