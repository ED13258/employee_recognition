from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from schema.judge import CreateRequest, UpdateRequest
from service.judge import JudgeService

router = APIRouter(prefix="/judges", tags=["judges"])

_service = JudgeService()


@router.post("")
async def create_judge(
    data: CreateRequest,
    session: AsyncSession = Depends(get_session),
):
    return await _service.create(session, data)


@router.get("")
async def get_judges(
    meeting_id: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
):
    return await _service.get_all(session, meeting_id)


@router.get("/{judge_id}")
async def get_judge(
    judge_id: int,
    session: AsyncSession = Depends(get_session),
):
    return await _service.get_by_id(session, judge_id)


@router.put("")
async def update_judge(
    data: UpdateRequest,
    session: AsyncSession = Depends(get_session),
):
    return await _service.update(session, data)


@router.delete("/{judge_id}")
async def delete_judge(
    judge_id: int,
    session: AsyncSession = Depends(get_session),
):
    return await _service.delete(session, judge_id)
