from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class BalanceResponse(BaseModel):
    agent_id: str
    balance: int
    total_earned: int = 0
    total_spent: int = 0


class TransactionItem(BaseModel):
    id: str
    agent_id: str
    type: str
    amount: int
    balance_after: int
    ref_type: str | None = None
    ref_id: str | None = None
    note: str | None = None
    created_at: datetime | None = None


class TransactionList(BaseModel):
    items: list[TransactionItem]
