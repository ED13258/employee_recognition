from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from schema.vote import BallotRequest, BatchBallotRequest
from service.vote import VoteService

# VR15：選票送出後不得修改，所以不提供 PUT 與 DELETE
router = APIRouter(prefix="/votes", tags=["votes"])

_service = VoteService()


@router.post("")
async def submit_ballot(
    data: BallotRequest,
    session: AsyncSession = Depends(get_session),
):
    return await _service.submit_ballot(session, data)


@router.post("/batch")
async def submit_batch(
    data: BatchBallotRequest,
    session: AsyncSession = Depends(get_session),
):
    return await _service.submit_batch(session, data)


@router.get("")
async def get_votes(
    judge_id: Optional[int] = None,
    nominate_id: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
):
    return await _service.get_all(session, judge_id, nominate_id)


@router.get("/{vote_id}")
async def get_vote(
    vote_id: int,
    session: AsyncSession = Depends(get_session),
):
    return await _service.get_by_id(session, vote_id)
