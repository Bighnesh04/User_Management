from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "pradhansaibighnesh@gmail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", SMTP_USERNAME)
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes", "on"}


def send_email(recipient: str, subject: str, body: str) -> None:
    if not SMTP_PASSWORD:
        raise RuntimeError("SMTP_PASSWORD is not configured")

    message = EmailMessage()
    message["From"] = SMTP_FROM_EMAIL
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    if SMTP_USE_TLS:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as client:
            client.ehlo()
            client.starttls()
            client.ehlo()
            client.login(SMTP_USERNAME, SMTP_PASSWORD)
            client.send_message(message)
    else:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=20) as client:
            client.login(SMTP_USERNAME, SMTP_PASSWORD)
            client.send_message(message)
