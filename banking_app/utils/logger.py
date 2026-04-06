from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.transaction import AuditLog

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
app_logger = logging.getLogger("banking_app")


async def log_activity(db: AsyncSession, user_id: Optional[int], action: str, details: Optional[str] = None) -> None:
    db.add(AuditLog(user_id=user_id, action=action, details=details))


def send_notification(channel: str, recipient: str, message: str) -> None:
    app_logger.info("Notification | channel=%s recipient=%s message=%s", channel, recipient, message)
