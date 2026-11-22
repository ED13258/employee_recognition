from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from service.report import ReportService

# 跨表的唯讀彙總查詢。不設定 prefix，路徑分別掛在 /prizes 與 /meetings 底下
router = APIRouter(tags=["reports"])

_service = ReportService()


@router.get("/prizes/{prize_id}/ranking")
async def get_prize_ranking(
    prize_id: int,
    session: AsyncSession = Depends(get_session),
):
    return await _service.get_ranking(session, prize_id)


@router.get("/prizes/{prize_id}/progress")
async def get_prize_progress(
    prize_id: int,
    session: AsyncSession = Depends(get_session),
):
    return await _service.get_progress(session, prize_id)


@router.get("/meetings/{meeting_id}/bonus-summary")
async def get_meeting_bonus_summary(
    meeting_id: int,
    session: AsyncSession = Depends(get_session),
):
    return await _service.get_bonus_summary(session, meeting_id)
