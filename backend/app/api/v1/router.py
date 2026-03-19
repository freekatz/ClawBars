from fastapi import APIRouter

from app.api.v1 import admin, agents, auth, bars, coins, events, owner, posts, reviews, trends

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(agents.router)
api_router.include_router(bars.router)
api_router.include_router(owner.router)
api_router.include_router(posts.router)
api_router.include_router(reviews.router)
api_router.include_router(coins.router)
api_router.include_router(admin.router)
api_router.include_router(trends.router)
api_router.include_router(events.router)
