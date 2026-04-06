from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional


class FraudDetector:
    def __init__(
        self,
        large_transfer_threshold: Decimal = Decimal("100000"),
        rapid_tx_limit: int = 5,
        rapid_window_seconds: int = 60,
        last_n_transactions: int = 20,
    ) -> None:
        self.large_transfer_threshold = large_transfer_threshold
        self.rapid_tx_limit = rapid_tx_limit
        self.rapid_window = timedelta(seconds=rapid_window_seconds)
        self.transactions_by_account = defaultdict(lambda: deque(maxlen=last_n_transactions))
        self.alerts: list[dict] = []

    def evaluate(self, account_id: int, amount: Decimal, location: Optional[str]) -> list[str]:
        now = datetime.utcnow()
        tx_window = self.transactions_by_account[account_id]
        tx_window.append({"time": now, "amount": amount, "location": location})

        reasons: list[str] = []

        if amount >= self.large_transfer_threshold:
            reasons.append("Large amount transfer detected")

        recent = [tx for tx in tx_window if now - tx["time"] <= self.rapid_window]
        if len(recent) >= self.rapid_tx_limit:
            reasons.append("Multiple rapid transactions detected")

        recent_locations = {tx["location"] for tx in recent if tx["location"]}
        if location and recent_locations and location not in recent_locations:
            reasons.append("Location mismatch detected")

        if reasons:
            self.alerts.append(
                {
                    "account_id": account_id,
                    "amount": str(amount),
                    "location": location,
                    "reasons": reasons,
                    "timestamp": now.isoformat(),
                }
            )

        return reasons

    def get_alerts(self) -> list[dict]:
        return self.alerts[-100:]


fraud_detector = FraudDetector()
