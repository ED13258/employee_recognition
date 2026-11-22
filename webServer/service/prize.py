from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.httpResponseMethod import HttpResponseMethod
from crud.meeting import CRUDMeeting
from crud.nominate import CRUDNominate
from crud.prize import CRUDPrize
from model.nominate import Nominate
from model.prize import Prize
from schema.nominate import NominateResponse
from schema.prize import (
    BonusBatchRequest, CreateRequest, UpdateRequest, PrizeResponse, PrizeWithNominationsResponse, PrizeUpdate,
)

from util.datetimeConverter import datetimeConverter
from util.votingPeriod import voting_started


class PrizeService:

    def __init__(self):
        self.crud_prize = CRUDPrize()
        self.crud_meeting = CRUDMeeting()
        self.crud_nominate = CRUDNominate()

    async def create(self, session: AsyncSession, data: CreateRequest):
        try:
            # R1：所屬會議必須存在
            meeting = await self.crud_meeting.get(session, id=data.meeting_id)
            if meeting is None:
                return await HttpResponseMethod.not_found(
                    message=f"Meeting {data.meeting_id} not found"
                )

            # R2：投票開始後不得新增獎項
            if voting_started(meeting):
                return await HttpResponseMethod.bad_request(
                    message="Voting has started; prizes can no longer be added",
                )

            # MD6.2：獎項與提名在同一個交易中建立，最後一次 commit；任何失敗都 rollback，不會留下部分資料。
            # 不使用 CRUDBase.create，因為它每次都會立即 commit。
            cur = datetimeConverter.get_current_timestamp()
            prize = Prize(name=data.name, meeting_id=data.meeting_id, created_at=cur)
            session.add(prize)
            await session.flush()            # 取得獎項 id

            # 提名的計分欄位與獎金為空值，created_at 與 updated_at 由伺服器產生（與 nominate 層一致）
            nominations = [
                Nominate(
                    prize_id=prize.id,
                    manager_name=n.manager_name,
                    employee_name=n.employee_name,
                    name=n.name,
                    created_at=cur,
                    updated_at=cur,
                )
                for n in data.nominations
            ]
            session.add_all(nominations)
            await session.flush()
            await session.commit()

            response_data = PrizeWithNominationsResponse(
                **prize.dict(),
                nominations=[NominateResponse(**n.dict()) for n in nominations],
            )
            return await HttpResponseMethod.ok(
                data=response_data.model_dump(),
                message=f"Prize {prize.id} created successfully with {len(nominations)} nominations",
            )
        except Exception as e:
            await session.rollback()
            return await HttpResponseMethod.server_error(e)

    async def get_all(self, session: AsyncSession, meeting_id: Optional[int] = None):
        try:
            filters = {} if meeting_id is None else {"meeting_id": meeting_id}
            results = await self.crud_prize.get_multi(session, **filters)
            response_data = [
                PrizeResponse(**result.dict()).model_dump()
                for result in sorted(results, key=lambda p: p.id)
            ]
            return await HttpResponseMethod.ok(
                data=response_data,
                message=f"{len(response_data)} prizes retrieved successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)

    async def get_by_id(self, session: AsyncSession, prize_id: int):
        try:
            result = await self.crud_prize.get(session, id=prize_id)
            if result is None:
                return await HttpResponseMethod.not_found(
                    message=f"Prize {prize_id} not found"
                )
            response_data = PrizeResponse(**result.dict())
            return await HttpResponseMethod.ok(
                data=response_data.model_dump(),
                message=f"Prize {prize_id} retrieved successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)

    async def update(self, session: AsyncSession, data: UpdateRequest):
        try:
            prize_id = data.id

            db_obj = await self.crud_prize.get(session, id=prize_id)
            if db_obj is None:
                return await HttpResponseMethod.not_found(
                    message=f"Prize {prize_id} not found"
                )

            # R4：名稱隨時可以修改；R3、R5：meeting_id 與 created_at 不在可修改範圍內
            update_data = PrizeUpdate(
                **data.model_dump(exclude={"id"}, exclude_none=True)
            ).model_dump(exclude_none=True)

            result = await self.crud_prize.update(session, obj_in=update_data, db_obj=db_obj)
            response_data = PrizeResponse(**result.dict())
            return await HttpResponseMethod.ok(
                data=response_data.model_dump(),
                message=f"Prize {prize_id} updated successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)

    async def update_bonuses(self, session: AsyncSession, prize_id: int, data: BonusBatchRequest):
        """
        VD6.2：一次儲存一個獎項多筆提名的核定獎金、扣除即時獎勵與備註。
        所有檢查通過後才寫入，最後一次 commit；任何失敗都不會修改資料。
        不檢查投票時間（VDQ5）與總預算（NR9）。
        """
        try:
            prize = await self.crud_prize.get(session, id=prize_id)
            if prize is None:
                return await HttpResponseMethod.not_found(
                    message=f"Prize {prize_id} not found"
                )

            ids = [item.nominate_id for item in data.items]
            duplicated = sorted({i for i in ids if ids.count(i) > 1})
            if duplicated:
                return await HttpResponseMethod.bad_request(
                    data={"nominate_ids": duplicated},
                    message="Duplicate nominate_id in items",
                )

            # 鎖定要修改的提名，避免與其他修改同時進行時，合併後的獎金檢查失準
            rows = (await session.execute(
                select(Nominate).where(Nominate.id.in_(ids)).with_for_update()
            )).scalars().all()
            nominations = {n.id: n for n in rows}

            # 提名必須存在且屬於此獎項
            foreign = [i for i in ids if i not in nominations or nominations[i].prize_id != prize_id]
            if foreign:
                await session.rollback()
                return await HttpResponseMethod.bad_request(
                    data={"nominate_ids": foreign},
                    message="Nomination does not belong to this prize",
                )

            # NR10：扣除即時獎勵不得大於核定獎金，與現有值合併後比較，空值視為 0
            changes, invalid = [], []
            for item in data.items:
                update_data = item.model_dump(exclude={"nominate_id"}, exclude_unset=True)
                nomination = nominations[item.nominate_id]
                issue = update_data.get("issue_bonus", nomination.issue_bonus)
                deduct = update_data.get("deduct_instant_bonus", nomination.deduct_instant_bonus)
                if (deduct or 0) > (issue or 0):
                    invalid.append(item.nominate_id)
                changes.append((nomination, update_data))
            if invalid:
                await session.rollback()
                return await HttpResponseMethod.bad_request(
                    data={"nominate_ids": invalid},
                    message="deduct_instant_bonus cannot be greater than issue_bonus",
                )

            cur = datetimeConverter.get_current_timestamp()
            for nomination, update_data in changes:
                for field, value in update_data.items():
                    setattr(nomination, field, value)
                nomination.updated_at = cur   # NR12
            await session.commit()

            response_data = [NominateResponse(**nominations[i].dict()).model_dump() for i in ids]
            return await HttpResponseMethod.ok(
                data=response_data,
                message=f"Bonuses of {len(ids)} nominations in prize {prize_id} updated successfully",
            )
        except Exception as e:
            await session.rollback()
            return await HttpResponseMethod.server_error(e)

    async def delete(self, session: AsyncSession, prize_id: int):
        try:
            db_obj = await self.crud_prize.get(session, id=prize_id)
            if db_obj is None:
                return await HttpResponseMethod.not_found(
                    message=f"Prize {prize_id} not found"
                )

            # R2：投票開始後不得刪除獎項
            meeting = await self.crud_meeting.get(session, id=db_obj.meeting_id)
            if meeting is not None and voting_started(meeting):
                return await HttpResponseMethod.bad_request(
                    message="Voting has started; prizes can no longer be deleted",
                )

            # R6：獎項底下已有提名時不得刪除
            nominations = await self.crud_nominate.get_multi(session, prize_id=prize_id)
            if nominations:
                return await HttpResponseMethod.bad_request(
                    data={"nomination_count": len(nominations)},
                    message=f"Prize {prize_id} still has nominations; delete them first",
                )

            await self.crud_prize.delete(session, db_obj=db_obj)
            return await HttpResponseMethod.ok(
                message=f"Prize {prize_id} deleted successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)
