from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session
from app.middleware.auth import require_user
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.user import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserProfile,
)
from app.services.user import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_to_profile(user: User) -> UserProfile:
    return UserProfile(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        status=user.status,
        avatar_url=user.avatar_url,
    )


@router.post("/register", response_model=ApiResponse[UserProfile], status_code=201)
async def register(
    payload: RegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[UserProfile]:
    svc = UserService(session)
    user = await svc.register(payload)
    await session.commit()
    return ApiResponse(data=_user_to_profile(user))


@router.post("/login", response_model=ApiResponse[TokenResponse])
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[TokenResponse]:
    svc = UserService(session)
    result = await svc.login(payload)
    return ApiResponse(data=TokenResponse(access_token=result.access_token, refresh_token=result.refresh_token))


@router.post("/refresh", response_model=ApiResponse[TokenResponse])
async def refresh(
    payload: RefreshRequest,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[TokenResponse]:
    svc = UserService(session)
    result = await svc.refresh(payload.refresh_token)
    return ApiResponse(data=TokenResponse(access_token=result.access_token, refresh_token=result.refresh_token))


@router.get("/me", response_model=ApiResponse[UserProfile])
async def me(
    current_user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[UserProfile]:
    svc = UserService(session)
    user = await svc.get_profile(current_user.id)
    return ApiResponse(data=_user_to_profile(user))


@router.put("/me", response_model=ApiResponse[UserProfile])
async def update_me(
    payload: UpdateProfileRequest,
    current_user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[UserProfile]:
    svc = UserService(session)
    user = await svc.update_profile(current_user.id, payload)
    await session.commit()
    return ApiResponse(data=_user_to_profile(user))


@router.get("/users/{user_id}", response_model=ApiResponse[dict])
async def get_user_public(
    user_id: str,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[dict]:
    """Get basic public profile of a user (name only)."""
    svc = UserService(session)
    user = await svc.get_profile(user_id)
    return ApiResponse(data={"id": user.id, "name": user.name, "role": user.role})


@router.get("/me/agents", response_model=ApiResponse[list[dict]])
async def my_agents(
    current_user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[list[dict]]:
    """List all agents owned by the current user."""
    from sqlalchemy import select
    from app.models.agent import Agent
    result = await session.execute(
        select(Agent).where(Agent.owner_id == current_user.id, Agent.deleted_at.is_(None))
        .order_by(Agent.created_at.desc())
    )
    agents = result.scalars().all()
    return ApiResponse(data=[
        {
            "id": a.id,
            "name": a.name,
            "agent_type": a.agent_type,
            "reputation": a.reputation,
            "status": a.status,
        }
        for a in agents
    ])
