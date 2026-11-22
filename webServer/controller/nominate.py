from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from schema.nominate import CreateRequest, UpdateRequest
from service.nominate import NominateService

router = APIRouter(prefix="/nominations", tags=["nominations"])

_service = NominateService()


@router.post("")
async def create_nomination(
    data: CreateRequest,
    session: AsyncSession = Depends(get_session),
):
    return await _service.create(session, data)


@router.get("")
async def get_nominations(
    prize_id: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
):
    return await _service.get_all(session, prize_id)


@router.get("/{nominate_id}")
async def get_nomination(
    nominate_id: int,
    session: AsyncSession = Depends(get_session),
):
    return await _service.get_by_id(session, nominate_id)


@router.put("")
async def update_nomination(
    data: UpdateRequest,
    session: AsyncSession = Depends(get_session),
):
    return await _service.update(session, data)


@router.delete("/{nominate_id}")
async def delete_nomination(
    nominate_id: int,
    session: AsyncSession = Depends(get_session),
):
    return await _service.delete(session, nominate_id)
