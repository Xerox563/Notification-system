from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_queue, get_session
from app.core.queue import RedisQueue
from app.schemas.notification import BulkCreate, BulkOut
from app.services import bulk_service

router = APIRouter(tags=["bulk"])


@router.post("/notifications/bulk", response_model=BulkOut, status_code=202)
async def create_bulk(
    data: BulkCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    queue: RedisQueue = Depends(get_queue),
):
    return await bulk_service.start_bulk(session, queue, data, request.app.state.settings)


@router.get("/bulk/{bulk_id}", response_model=BulkOut)
async def get_bulk(bulk_id: str, session: AsyncSession = Depends(get_session)):
    return await bulk_service.get_bulk(session, bulk_id)
