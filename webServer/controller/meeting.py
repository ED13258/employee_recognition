from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from schema.meeting import CreateRequest, UpdateRequest
from service.meeting import MeetingService

router = APIRouter(prefix="/meetings", tags=["meetings"])

_service = MeetingService()


@router.post("")
async def create_meeting(
    data: CreateRequest,
    session: AsyncSession = Depends(get_session),
):
    return await _service.create(session, data)


@router.get("")
async def get_meetings(
    session: AsyncSession = Depends(get_session),
):
    return await _service.get_all(session)


@router.get("/{meeting_id}")
async def get_meeting(
    meeting_id: int,
    session: AsyncSession = Depends(get_session),
):
    return await _service.get_by_id(session, meeting_id)


@router.put("")
async def update_meeting(
    data: UpdateRequest,
    session: AsyncSession = Depends(get_session),
):
    return await _service.update(session, data)


@router.delete("/{meeting_id}")
async def delete_meeting(
    meeting_id: int,
    session: AsyncSession = Depends(get_session),
):
    return await _service.delete(session, meeting_id)

