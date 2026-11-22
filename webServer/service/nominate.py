from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.httpResponseMethod import HttpResponseMethod
from crud.meeting import CRUDMeeting
from crud.nominate import CRUDNominate
from crud.prize import CRUDPrize
from schema.nominate import CreateRequest, UpdateRequest, NominateResponse, NominateCreate, NominateUpdate

from util.datetimeConverter import datetimeConverter
from util.votingPeriod import voting_started

BONUS_FIELDS = ("issue_bonus", "deduct_instant_bonus")
PERSON_FIELDS = ("manager_name", "employee_name")   # 上司與下屬名稱，只能在投票開始前修改（NCR4）


class NominateService:

    def __init__(self):
        self.crud_nominate = CRUDNominate()
        self.crud_prize = CRUDPrize()
        self.crud_meeting = CRUDMeeting()

    async def _voting_started_for_prize(self, session: AsyncSession, prize_id: int) -> bool:
        prize = await self.crud_prize.get(session, id=prize_id)
        meeting = await self.crud_meeting.get(session, id=prize.meeting_id)
        return meeting is not None and voting_started(meeting)

    async def create(self, session: AsyncSession, data: CreateRequest):
        try:
            # NR1：所屬獎項必須存在
            prize = await self.crud_prize.get(session, id=data.prize_id)
            if prize is None:
                return await HttpResponseMethod.not_found(
                    message=f"Prize {data.prize_id} not found"
                )

            # NCR1、NCR2：上司與下屬名稱由 schema 檢查必填，不再檢查 manager、employee 表

            # NR3：投票開始後不得新增提名
            if await self._voting_started_for_prize(session, data.prize_id):
                return await HttpResponseMethod.bad_request(
                    message="Voting has started; nominations can no longer be added",
                )

            # NCR3：不檢查重複提名

            # NR6、NR12：計分結果與獎金為空值，created_at 與 updated_at 由伺服器產生
            cur = datetimeConverter.get_current_timestamp()
            create_data = NominateCreate(
                **data.model_dump(),
                created_at=cur,
                updated_at=cur,
            )

            result = await self.crud_nominate.create(session, obj_in=create_data)
            response_data = NominateResponse(**result.dict())

            return await HttpResponseMethod.ok(
                data=response_data.model_dump(),
                message=f"Nomination {result.id} created successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)

    async def get_all(self, session: AsyncSession, prize_id: Optional[int] = None):
        try:
            # NCQ3：只保留依獎項篩選
            filters = {} if prize_id is None else {"prize_id": prize_id}

            results = await self.crud_nominate.get_multi(session, **filters)
            response_data = [
                NominateResponse(**result.dict()).model_dump()
                for result in sorted(results, key=lambda n: n.id)
            ]
            return await HttpResponseMethod.ok(
                data=response_data,
                message=f"{len(response_data)} nominations retrieved successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)

    async def get_by_id(self, session: AsyncSession, nominate_id: int):
        try:
            result = await self.crud_nominate.get(session, id=nominate_id)
            if result is None:
                return await HttpResponseMethod.not_found(
                    message=f"Nomination {nominate_id} not found"
                )
            response_data = NominateResponse(**result.dict())
            return await HttpResponseMethod.ok(
                data=response_data.model_dump(),
                message=f"Nomination {nominate_id} retrieved successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)

    async def update(self, session: AsyncSession, data: UpdateRequest):
        try:
            nominate_id = data.id

            db_obj = await self.crud_nominate.get(session, id=nominate_id)
            if db_obj is None:
                return await HttpResponseMethod.not_found(
                    message=f"Nomination {nominate_id} not found"
                )

            # 使用 exclude_unset：帶入 null 代表清空，沒帶代表維持原值
            update_data = data.model_dump(exclude={"id"}, exclude_unset=True)

            # NR7、NCR1：提名名稱、上司與下屬名稱不可為空
            for field in ("name",) + PERSON_FIELDS:
                if field in update_data and update_data[field] is None:
                    return await HttpResponseMethod.bad_request(
                        message=f"{field} cannot be null",
                    )

            # NCR4：上司與下屬名稱只能在投票開始前修改
            changed_people = [f for f in PERSON_FIELDS if f in update_data and update_data[f] != getattr(db_obj, f)]
            if changed_people and await self._voting_started_for_prize(session, db_obj.prize_id):
                return await HttpResponseMethod.bad_request(
                    data={"locked_fields": changed_people},
                    message="Voting has started; manager_name and employee_name can no longer be modified",
                )

            # NR10：扣除即時獎金不得大於核定獎金，與現有值合併後比較，空值視為 0
            # NR8、NR9：不檢查投票時間、門檻結果與總預算
            if any(field in update_data for field in BONUS_FIELDS):
                issue_bonus = update_data["issue_bonus"] if "issue_bonus" in update_data else db_obj.issue_bonus
                deduct = (
                    update_data["deduct_instant_bonus"]
                    if "deduct_instant_bonus" in update_data
                    else db_obj.deduct_instant_bonus
                )
                if (deduct or 0) > (issue_bonus or 0):
                    return await HttpResponseMethod.bad_request(
                        data={"issue_bonus": issue_bonus, "deduct_instant_bonus": deduct},
                        message="deduct_instant_bonus cannot be greater than issue_bonus",
                    )

            # NR12：每次修改都更新 updated_at
            update_data["updated_at"] = datetimeConverter.get_current_timestamp()
            update_data = NominateUpdate(**update_data).model_dump(exclude_unset=True)

            result = await self.crud_nominate.update(session, obj_in=update_data, db_obj=db_obj)
            response_data = NominateResponse(**result.dict())
            return await HttpResponseMethod.ok(
                data=response_data.model_dump(),
                message=f"Nomination {nominate_id} updated successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)

    async def delete(self, session: AsyncSession, nominate_id: int):
        try:
            db_obj = await self.crud_nominate.get(session, id=nominate_id)
            if db_obj is None:
                return await HttpResponseMethod.not_found(
                    message=f"Nomination {nominate_id} not found"
                )

            # NR3：投票開始後不得刪除提名
            if await self._voting_started_for_prize(session, db_obj.prize_id):
                return await HttpResponseMethod.bad_request(
                    message="Voting has started; nominations can no longer be deleted",
                )

            await self.crud_nominate.delete(session, db_obj=db_obj)
            return await HttpResponseMethod.ok(
                message=f"Nomination {nominate_id} deleted successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)
