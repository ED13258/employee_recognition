from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from schema.prize import BonusBatchRequest, CreateRequest, UpdateRequest
from service.prize import PrizeService

router = APIRouter(prefix="/prizes", tags=["prizes"])

_service = PrizeService()


@router.post("")
async def create_prize(
    data: CreateRequest,
    session: AsyncSession = Depends(get_session),
):
    return await _service.create(session, data)


@router.get("")
async def get_prizes(
    meeting_id: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
):
    return await _service.get_all(session, meeting_id)


@router.get("/{prize_id}")
async def get_prize(
    prize_id: int,
    session: AsyncSession = Depends(get_session),
):
    return await _service.get_by_id(session, prize_id)


@router.put("")
async def update_prize(
    data: UpdateRequest,
    session: AsyncSession = Depends(get_session),
):
    return await _service.update(session, data)


@router.put("/{prize_id}/bonuses")
async def update_prize_bonuses(
    prize_id: int,
    data: BonusBatchRequest,
    session: AsyncSession = Depends(get_session),
):
    return await _service.update_bonuses(session, prize_id, data)


@router.delete("/{prize_id}")
async def delete_prize(
    prize_id: int,
    session: AsyncSession = Depends(get_session),
):
    return await _service.delete(session, prize_id)
