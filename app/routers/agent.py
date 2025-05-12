from fastapi import APIRouter

from app.core import logger

router = APIRouter(
    prefix="/agent",
    tags=["Agents"],
)


@router.get("/")
async def root():
    logger.info("agent root!")
    return "OK"
