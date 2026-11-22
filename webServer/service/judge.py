from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.httpResponseMethod import HttpResponseMethod
from crud.judge import CRUDJudge
from crud.meeting import CRUDMeeting
from model.meeting import Meeting
from schema.judge import CreateRequest, UpdateRequest, JudgeResponse, JudgeCreate, JudgeUpdate

from util.datetimeConverter import datetimeConverter
from util.votingPeriod import voting_started


class JudgeService:

    def __init__(self):
        self.crud_judge = CRUDJudge()
        self.crud_meeting = CRUDMeeting()

    async def create(self, session: AsyncSession, data: CreateRequest):
        try:
            # JR1：所屬會議必須存在
            # D5：鎖定會議資料列，同一會議的新增評審與調整人數上限依序處理，避免超過上限
            result = await session.execute(
                select(Meeting).where(Meeting.id == data.meeting_id).with_for_update()
            )
            meeting = result.scalars().first()
            if meeting is None:
                return await HttpResponseMethod.not_found(
                    message=f"Meeting {data.meeting_id} not found"
                )

            # JR3：投票開始後不得新增評審
            if voting_started(meeting):
                return await HttpResponseMethod.bad_request(
                    message="Voting has started; judges can no longer be added",
                )

            # JR2：評審數不得超過人數上限
            judges = await self.crud_judge.get_multi(session, meeting_id=data.meeting_id)
            if len(judges) >= meeting.total_judges:
                return await HttpResponseMethod.bad_request(
                    data={"judge_count": len(judges), "total_judges": meeting.total_judges},
                    message=f"Meeting {data.meeting_id} has reached its judge limit",
                )

            # JR7：created_at 由伺服器產生
            create_data = JudgeCreate(
                **data.model_dump(),
                created_at=datetimeConverter.get_current_timestamp(),
            )

            result = await self.crud_judge.create(session, obj_in=create_data)
            response_data = JudgeResponse(**result.dict())

            return await HttpResponseMethod.ok(
                data=response_data.model_dump(),
                message=f"Judge {result.id} created successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)

    async def get_all(self, session: AsyncSession, meeting_id: Optional[int] = None):
        try:
            filters = {} if meeting_id is None else {"meeting_id": meeting_id}
            results = await self.crud_judge.get_multi(session, **filters)
            response_data = [
                JudgeResponse(**result.dict()).model_dump()
                for result in sorted(results, key=lambda j: j.id)
            ]
            return await HttpResponseMethod.ok(
                data=response_data,
                message=f"{len(response_data)} judges retrieved successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)

    async def get_by_id(self, session: AsyncSession, judge_id: int):
        try:
            result = await self.crud_judge.get(session, id=judge_id)
            if result is None:
                return await HttpResponseMethod.not_found(
                    message=f"Judge {judge_id} not found"
                )
            response_data = JudgeResponse(**result.dict())
            return await HttpResponseMethod.ok(
                data=response_data.model_dump(),
                message=f"Judge {judge_id} retrieved successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)

    async def update(self, session: AsyncSession, data: UpdateRequest):
        try:
            judge_id = data.id

            db_obj = await self.crud_judge.get(session, id=judge_id)
            if db_obj is None:
                return await HttpResponseMethod.not_found(
                    message=f"Judge {judge_id} not found"
                )

            # JR5：名稱隨時可以修改；JR4、JR7：meeting_id 與 created_at 不在可修改範圍內
            update_data = JudgeUpdate(
                **data.model_dump(exclude={"id"}, exclude_none=True)
            ).model_dump(exclude_none=True)

            result = await self.crud_judge.update(session, obj_in=update_data, db_obj=db_obj)
            response_data = JudgeResponse(**result.dict())
            return await HttpResponseMethod.ok(
                data=response_data.model_dump(),
                message=f"Judge {judge_id} updated successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)

    async def delete(self, session: AsyncSession, judge_id: int):
        try:
            db_obj = await self.crud_judge.get(session, id=judge_id)
            if db_obj is None:
                return await HttpResponseMethod.not_found(
                    message=f"Judge {judge_id} not found"
                )

            # JR3：投票開始後不得刪除評審。選票只能在投票開始後送出，所以這裡不會有該評審的選票
            meeting = await self.crud_meeting.get(session, id=db_obj.meeting_id)
            if meeting is not None and voting_started(meeting):
                return await HttpResponseMethod.bad_request(
                    message="Voting has started; judges can no longer be deleted",
                )

            await self.crud_judge.delete(session, db_obj=db_obj)
            return await HttpResponseMethod.ok(
                message=f"Judge {judge_id} deleted successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)
