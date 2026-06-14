from fastapi import APIRouter

from .available_guilds import router as available_guilds_router
from .guild import router as guild_router

router = APIRouter()
router.include_router(guild_router)
router.include_router(available_guilds_router)
