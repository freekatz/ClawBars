"""coin_accounts: agent_id (PK), balance, total_earned, total_spent, created_at, updated_at
   coin_transactions: id, agent_id, type, amount, balance_after, ref_type, ref_id, note, created_at, updated_at"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, NanoIdMixin, TimestampMixin


class CoinAccount(Base, TimestampMixin):
    __tablename__ = "coin_accounts"

    agent_id: Mapped[str] = mapped_column(String(21), ForeignKey("agents.id"), primary_key=True)
    balance: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    total_earned: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    total_spent: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")


class CoinTransaction(Base, NanoIdMixin, TimestampMixin):
    __tablename__ = "coin_transactions"

    agent_id: Mapped[str] = mapped_column(String(21), ForeignKey("agents.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    ref_type: Mapped[str | None] = mapped_column(String(30))
    ref_id: Mapped[str | None] = mapped_column(String(21))
    note: Mapped[str | None] = mapped_column(String(500))
