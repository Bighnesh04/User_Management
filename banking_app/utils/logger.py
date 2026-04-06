from __future__ import annotations

import logging
from typing import Optional

from starlette.concurrency import run_in_threadpool

from utils.mailer import send_email

from sqlalchemy.ext.asyncio import AsyncSession

from models.transaction import AuditLog

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
app_logger = logging.getLogger("banking_app")


async def log_activity(db: AsyncSession, user_id: Optional[int], action: str, details: Optional[str] = None) -> None:
    db.add(AuditLog(user_id=user_id, action=action, details=details))


async def send_notification(channel: str, recipient: str, message: str) -> None:
    if channel.lower() == "email":
        try:
            await run_in_threadpool(
                send_email,
                recipient,
                "Banking App Notification",
                message,
            )
            app_logger.info("Email sent | recipient=%s message=%s", recipient, message)
        except Exception as exc:
            app_logger.exception("Email notification failed for %s", recipient)
            app_logger.error("SMTP error: %s", exc)
        return

    app_logger.info("Notification | channel=%s recipient=%s message=%s", channel, recipient, message)
