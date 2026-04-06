from __future__ import annotations

import os
from decimal import Decimal
from typing import Optional

from redis import asyncio as redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class BalanceCache:
    def __init__(self) -> None:
        self._client = redis.from_url(REDIS_URL, decode_responses=True)
        self._fallback: dict[int, str] = {}

    async def get_balance(self, account_id: int) -> Optional[Decimal]:
        key = f"balance:{account_id}"
        try:
            value = await self._client.get(key)
            if value is None:
                return None
            return Decimal(value)
        except Exception:
            value = self._fallback.get(account_id)
            return Decimal(value) if value is not None else None

    async def set_balance(self, account_id: int, balance: Decimal) -> None:
        key = f"balance:{account_id}"
        try:
            await self._client.set(key, str(balance), ex=60)
        except Exception:
            self._fallback[account_id] = str(balance)


balance_cache = BalanceCache()
