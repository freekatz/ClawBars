from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session
from app.middleware.auth import require_agent
from app.models.agent import Agent
from app.models.coin import CoinAccount, CoinTransaction
from app.schemas.coin import BalanceResponse, TransactionItem
from app.schemas.common import ApiResponse
from app.services.coin import CoinService

router = APIRouter(prefix="/coins", tags=["coins"])


def _account_to_response(account: CoinAccount) -> BalanceResponse:
    return BalanceResponse(
        agent_id=account.agent_id,
        balance=account.balance,
        total_earned=account.total_earned,
        total_spent=account.total_spent,
    )


def _tx_to_item(tx: CoinTransaction) -> TransactionItem:
    return TransactionItem(
        id=tx.id,
        agent_id=tx.agent_id,
        type=tx.type,
        amount=tx.amount,
        balance_after=tx.balance_after,
        ref_type=tx.ref_type,
        ref_id=tx.ref_id,
        note=tx.note,
        created_at=tx.created_at,
    )


@router.get("/balance", response_model=ApiResponse[BalanceResponse])
async def balance(
    current: Agent = Depends(require_agent),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[BalanceResponse]:
    svc = CoinService(session)
    account = await svc.get_balance(current.id)
    return ApiResponse(data=_account_to_response(account))


@router.get("/transactions", response_model=ApiResponse[list[TransactionItem]])
async def transactions(
    limit: int = Query(default=20, ge=1, le=100),
    tx_type: str | None = Query(default=None),
    current: Agent = Depends(require_agent),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[list[TransactionItem]]:
    svc = CoinService(session)
    txs = await svc.list_transactions(current.id, limit=limit, tx_type=tx_type)
    return ApiResponse(data=[_tx_to_item(t) for t in txs])
