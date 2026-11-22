from typing import Dict, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.httpResponseMethod import HttpResponseMethod
from crud.meeting import CRUDMeeting
from model.judge import Judge
from model.meeting import Meeting
from schema.judge import JudgeResponse
from schema.meeting import (
    CreateRequest, UpdateRequest, MeetingResponse, MeetingWithJudgesResponse, MeetingWithProgressResponse,
    MeetingCreate, MeetingUpdate,
)

from util.datetimeConverter import datetimeConverter
from util.votingPeriod import voting_started

# 投票開始後不得修改的欄位。total_judges 建立後即不可修改（MDR12），不在 UpdateRequest 中，所以不需列入
LOCKED_AFTER_KICKOFF = ("proportion", "voting_kickoff", "voting_deadline")

# 每場會議中「投完所有可投票獎項」的評審人數（MP5）
# - 可投票獎項：底下至少有一筆提名的獎項
# - 選票以整張為單位送出，評審投過某獎項的任一提名，即代表投完該獎項
# {prize_filter}、{judge_filter} 在查詢單一會議時填入條件，查詢全部時為空字串
VOTED_JUDGE_SQL = """
WITH votable AS (
    SELECT p.meeting_id, COUNT(DISTINCT p.id) AS prize_count
    FROM prize p
    JOIN nominate n ON n.prize_id = p.id
    {prize_filter}
    GROUP BY p.meeting_id
),
judge_done AS (
    SELECT j.meeting_id, v.judge_id, COUNT(DISTINCT n.prize_id) AS voted_prizes
    FROM vote v
    JOIN judge j    ON j.id = v.judge_id
    JOIN nominate n ON n.id = v.nominate_id
    {judge_filter}
    GROUP BY j.meeting_id, v.judge_id
)
SELECT d.meeting_id, COUNT(*) AS voted_judge_count
FROM judge_done d
JOIN votable t ON t.meeting_id = d.meeting_id
WHERE d.voted_prizes >= t.prize_count
GROUP BY d.meeting_id
"""


def with_progress(meeting: Meeting, voted_judge_count: int) -> dict:
    """
    加上選票進度：已投票評審人數 / 會議設定的評審總人數。
    只到小數點第二位，第三位以後無條件捨去（MPR2），上限為 1（MPR3）。
    先以整數算出百分比再除以 100，避免浮點數誤差（例如 0.29 * 100 = 28.999…）。
    """
    if not meeting.total_judges:
        progress = 0.0
    else:
        progress = min(100, voted_judge_count * 100 // meeting.total_judges) / 100
    return MeetingWithProgressResponse(
        **meeting.dict(), voted_judge_count=voted_judge_count, vote_progress=progress,
    ).model_dump()


class MeetingService:

    def __init__(self):
        self.crud_meeting = CRUDMeeting()

    async def create(self, session: AsyncSession, data: CreateRequest):
        try:
            # 開始時間必須早於截止時間
            if data.voting_kickoff >= data.voting_deadline:
                return await HttpResponseMethod.bad_request(
                    message="voting_kickoff must be earlier than voting_deadline",
                )

            cur = datetimeConverter.get_current_timestamp()

            create_data = MeetingCreate(
                **data.model_dump(),
                created_at=cur,
            )

            # VP6.1：會議與「評委 1」到「評委 N」在同一個交易中建立，最後一次 commit；
            # 任何失敗都 rollback，不會留下沒有評委的會議。不使用 CRUDBase.create，因為它會立即 commit。
            meeting = Meeting(**create_data.model_dump())
            session.add(meeting)
            await session.flush()            # 取得會議 id

            judges = [
                Judge(name=f"評委 {i}", meeting_id=meeting.id, created_at=cur)
                for i in range(1, data.total_judges + 1)
            ]
            session.add_all(judges)
            await session.flush()
            await session.commit()

            response_data = MeetingWithJudgesResponse(
                **meeting.dict(),
                judges=[JudgeResponse(**judge.dict()) for judge in judges],
            )
            return await HttpResponseMethod.ok(
                data=response_data.model_dump(),
                message=f"Meeting {meeting.id} created successfully with {len(judges)} judges",
            )
        except Exception as e:
            await session.rollback()
            return await HttpResponseMethod.server_error(e)

    async def _voted_judge_counts(self, session: AsyncSession, meeting_id: Optional[int] = None) -> Dict[int, int]:
        """以一次查詢取得各會議已投票的評審人數；沒有出現在結果中的會議視為 0"""
        if meeting_id is None:
            sql = VOTED_JUDGE_SQL.format(prize_filter="", judge_filter="")
            params = {}
        else:
            sql = VOTED_JUDGE_SQL.format(prize_filter="WHERE p.meeting_id = :mid", judge_filter="WHERE j.meeting_id = :mid")
            params = {"mid": meeting_id}
        rows = (await session.execute(text(sql), params)).all()
        return {row.meeting_id: row.voted_judge_count for row in rows}

    async def get_all(self, session: AsyncSession):
        try:
            results = await self.crud_meeting.get_multi(session)
            voted = await self._voted_judge_counts(session)
            response_data = [
                with_progress(result, voted.get(result.id, 0))
                for result in sorted(results, key=lambda m: m.id)
            ]
            return await HttpResponseMethod.ok(
                data=response_data,
                message=f"{len(response_data)} meetings retrieved successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)

    async def get_by_id(self, session: AsyncSession, meeting_id: int):
        try:
            result = await self.crud_meeting.get(session, id=meeting_id)
            if result is None:
                return await HttpResponseMethod.not_found(
                    message=f"Meeting {meeting_id} not found"
                )
            voted = await self._voted_judge_counts(session, meeting_id)
            return await HttpResponseMethod.ok(
                data=with_progress(result, voted.get(meeting_id, 0)),
                message=f"Meeting {meeting_id} retrieved successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)

    async def update(self, session: AsyncSession, data: UpdateRequest):
        try:
            meeting_id = data.id

            # 人數上限不可修改（MDR12），所以不再需要 D5 的會議鎖定
            db_obj = await self.crud_meeting.get(session, id=meeting_id)
            if db_obj is None:
                return await HttpResponseMethod.not_found(
                    message=f"Meeting {meeting_id} not found"
                )

            update_data = MeetingUpdate(
                **data.model_dump(exclude={"id"}, exclude_none=True)
            ).model_dump(exclude_none=True)

            # 投票開始後，鎖定門檻比例、開始與截止時間
            cur = datetimeConverter.get_current_timestamp()
            if cur >= db_obj.voting_kickoff:
                changed = [
                    field for field in LOCKED_AFTER_KICKOFF
                    if field in update_data and update_data[field] != getattr(db_obj, field)
                ]
                if changed:
                    return await HttpResponseMethod.bad_request(
                        data={"locked_fields": changed},
                        message="Voting has started; these fields can no longer be modified",
                    )

            # 開始時間必須早於截止時間（與現有值合併後檢查）
            kickoff = update_data.get("voting_kickoff", db_obj.voting_kickoff)
            deadline = update_data.get("voting_deadline", db_obj.voting_deadline)
            if kickoff >= deadline:
                return await HttpResponseMethod.bad_request(
                    message="voting_kickoff must be earlier than voting_deadline",
                )

            result = await self.crud_meeting.update(session, obj_in=update_data, db_obj=db_obj)
            response_data = MeetingResponse(**result.dict())
            return await HttpResponseMethod.ok(
                data=response_data.model_dump(),
                message=f"Meeting {meeting_id} updated successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)

    async def delete(self, session: AsyncSession, meeting_id: int):
        try:
            db_obj = await self.crud_meeting.get(session, id=meeting_id)
            if db_obj is None:
                return await HttpResponseMethod.not_found(
                    message=f"Meeting {meeting_id} not found"
                )

            # VR17：投票開始後不得刪除會議，避免連鎖刪除選票與計分結果
            if voting_started(db_obj):
                return await HttpResponseMethod.bad_request(
                    message="Voting has started; the meeting can no longer be deleted",
                )

            await self.crud_meeting.delete(session, db_obj=db_obj)
            return await HttpResponseMethod.ok(
                message=f"Meeting {meeting_id} deleted successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)
