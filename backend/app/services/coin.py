from __future__ import annotations

from nanoid import generate
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.coin import CoinAccount, CoinTransaction


class CoinService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_account(self, agent_id: str) -> CoinAccount:
        result = await self.session.execute(
            select(CoinAccount).where(CoinAccount.agent_id == agent_id)
        )
        account = result.scalar_one_or_none()
        if not account:
            raise AppError(code=40401, message="Coin account not found", http_status=404)
        return account

    async def ensure_account(self, agent_id: str, initial_balance: int = 0) -> CoinAccount:
        result = await self.session.execute(
            select(CoinAccount).where(CoinAccount.agent_id == agent_id)
        )
        account = result.scalar_one_or_none()
        if not account:
            account = CoinAccount(
                agent_id=agent_id,
                balance=initial_balance,
                total_earned=initial_balance,
                total_spent=0,
            )
            self.session.add(account)
            await self.session.flush()
        return account

    async def get_balance(self, agent_id: str) -> CoinAccount:
        return await self._get_account(agent_id)

    async def credit(
        self,
        agent_id: str,
        amount: int,
        tx_type: str,
        ref_type: str | None = None,
        ref_id: str | None = None,
        note: str | None = None,
    ) -> CoinTransaction:
        # Atomic SQL update to prevent race conditions
        stmt = (
            update(CoinAccount)
            .where(CoinAccount.agent_id == agent_id)
            .values(
                balance=CoinAccount.balance + amount,
                total_earned=CoinAccount.total_earned + amount,
            )
            .returning(CoinAccount.balance)
        )
        result = await self.session.execute(stmt)
        row = result.one_or_none()
        if row is None:
            raise AppError(code=40401, message="Coin account not found", http_status=404)
        new_balance = row[0]
        tx = CoinTransaction(
            id=generate(size=21),
            agent_id=agent_id,
            type=tx_type,
            amount=amount,
            balance_after=new_balance,
            ref_type=ref_type,
            ref_id=ref_id,
            note=note,
        )
        self.session.add(tx)
        await self.session.flush()
        return tx

    async def debit(
        self,
        agent_id: str,
        amount: int,
        tx_type: str,
        ref_type: str | None = None,
        ref_id: str | None = None,
        note: str | None = None,
    ) -> CoinTransaction:
        # Atomic SQL update with balance check to prevent race conditions and overdraft
        stmt = (
            update(CoinAccount)
            .where(CoinAccount.agent_id == agent_id, CoinAccount.balance >= amount)
            .values(
                balance=CoinAccount.balance - amount,
                total_spent=CoinAccount.total_spent + amount,
            )
            .returning(CoinAccount.balance)
        )
        result = await self.session.execute(stmt)
        row = result.one_or_none()
        if row is None:
            # Check if account exists to give appropriate error
            account = await self.session.execute(
                select(CoinAccount).where(CoinAccount.agent_id == agent_id)
            )
            if account.scalar_one_or_none() is None:
                raise AppError(code=40401, message="Coin account not found", http_status=404)
            raise AppError(
                code=40201,
                message="Insufficient balance",
                detail={"required": amount},
                http_status=402,
            )
        new_balance = row[0]
        tx = CoinTransaction(
            id=generate(size=21),
            agent_id=agent_id,
            type=tx_type,
            amount=-amount,
            balance_after=new_balance,
            ref_type=ref_type,
            ref_id=ref_id,
            note=note,
        )
        self.session.add(tx)
        await self.session.flush()
        return tx

    async def grant(self, agent_id: str, amount: int, note: str | None = None) -> CoinTransaction:
        return await self.credit(agent_id=agent_id, amount=amount, tx_type="system_grant", note=note)

    async def list_transactions(
        self,
        agent_id: str,
        limit: int = 20,
        tx_type: str | None = None,
    ) -> list[CoinTransaction]:
        stmt = (
            select(CoinTransaction)
            .where(CoinTransaction.agent_id == agent_id)
            .order_by(CoinTransaction.created_at.desc())
            .limit(limit)
        )
        if tx_type:
            stmt = stmt.where(CoinTransaction.type == tx_type)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
