from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.httpResponseMethod import HttpResponseMethod
from crud.judge import CRUDJudge
from crud.meeting import CRUDMeeting
from crud.nominate import CRUDNominate
from crud.vote import CRUDVote
from model.meeting import Meeting
from model.nominate import Nominate
from model.prize import Prize
from model.vote import Vote
from schema.nominate import NominateResponse
from schema.vote import (
    BallotRequest, BallotResponse, BatchBallotRequest, BatchBallotResponse, BatchBallotResult, VoteResponse,
)

from util.datetimeConverter import datetimeConverter
from util.votingPeriod import voting_ended, voting_started


def vote_to_dict(vote: Vote) -> dict:
    """輸出時使用別名，讓 JSON 欄位名稱為 pass 而不是 pass_"""
    return VoteResponse(**vote.dict()).model_dump(by_alias=True)


class VoteService:

    def __init__(self):
        self.crud_vote = CRUDVote()
        self.crud_judge = CRUDJudge()
        self.crud_meeting = CRUDMeeting()
        self.crud_nominate = CRUDNominate()

    async def submit_ballot(self, session: AsyncSession, data: BallotRequest):
        try:
            # 步驟 1、VR1：評審必須存在
            judge = await self.crud_judge.get(session, id=data.judge_id)
            if judge is None:
                return await HttpResponseMethod.not_found(
                    message=f"Judge {data.judge_id} not found"
                )

            # 步驟 2、VR2、VR14：鎖定獎項資料列，同一獎項的選票依序處理
            result = await session.execute(
                select(Prize).where(Prize.id == data.prize_id).with_for_update()
            )
            prize = result.scalars().first()
            if prize is None:
                return await HttpResponseMethod.not_found(
                    message=f"Prize {data.prize_id} not found"
                )

            # 步驟 3、VR3：評審與獎項必須屬於同一個會議
            if judge.meeting_id != prize.meeting_id:
                return await HttpResponseMethod.bad_request(
                    data={"judge_meeting_id": judge.meeting_id, "prize_meeting_id": prize.meeting_id},
                    message="Judge and prize belong to different meetings",
                )

            # 步驟 4、VR4：開始時間 <= 目前時間 < 截止時間
            meeting = await self.crud_meeting.get(session, id=prize.meeting_id)
            if not voting_started(meeting):
                return await HttpResponseMethod.bad_request(
                    message="Voting has not started yet",
                )
            if voting_ended(meeting):
                return await HttpResponseMethod.bad_request(
                    message="Voting has ended",
                )

            # 步驟 5、VR12：獎項必須有提名，N 為提名總數
            nominations = await self.crud_nominate.get_multi(session, prize_id=prize.id)
            n = len(nominations)
            if n == 0:
                return await HttpResponseMethod.bad_request(
                    message=f"Prize {prize.id} has no nominations",
                )
            nomination_ids = {nomination.id for nomination in nominations}

            # 步驟 6、VR5：同一位評審對同一獎項只能送出一次選票
            existing = await self.crud_vote.get_multi(
                session, Vote.nominate_id.in_(nomination_ids), judge_id=judge.id
            )
            if existing:
                return await HttpResponseMethod.bad_request(
                    message=f"Judge {judge.id} has already submitted a ballot for prize {prize.id}",
                )

            # 步驟 7、8：選票內容檢查（與批次送出共用）
            error = await self._check_entries(nomination_ids, data.entries)
            if error is not None:
                return error

            # 步驟 9、VR11：依公式產生排序值與分數，忽略客戶端送出的分數
            cur = datetimeConverter.get_current_timestamp()
            votes = self._build_votes(judge.id, n, data.entries, cur)

            # 步驟 10 到 12、VR13：寫入選票、重新計算提名，最後一次 commit
            session.add_all(votes)
            await session.flush()
            await self._recalculate(session, meeting, nominations, cur)
            await session.commit()

            response_data = BallotResponse(
                votes=[VoteResponse(**vote.dict()) for vote in sorted(votes, key=lambda v: v.id)],
                nominations=[
                    NominateResponse(**nomination.dict())
                    for nomination in sorted(nominations, key=lambda x: x.id)
                ],
            )
            return await HttpResponseMethod.ok(
                data=response_data.model_dump(by_alias=True),
                message=f"Ballot of judge {judge.id} for prize {prize.id} submitted successfully",
            )
        except Exception as e:
            await session.rollback()
            return await HttpResponseMethod.server_error(e)

    # ---- 選票內容檢查與建立，單一獎項與批次送出共用 ----

    @staticmethod
    async def _check_entries(nomination_ids, entries, prize_id=None):
        """
        VR6 到 VR10：選票必須剛好涵蓋全部提名；通過者排序為 1 到 P 連續，未通過者不可帶排序。
        通過時回傳 None，否則回傳 400。批次送出時在 data 中加入 prize_id，讓前端標示對應的獎項。
        """
        extra_data = {} if prize_id is None else {"prize_id": prize_id}

        entry_ids = [entry.nominate_id for entry in entries]
        duplicated = sorted({i for i in entry_ids if entry_ids.count(i) > 1})
        missing = sorted(nomination_ids - set(entry_ids))
        extra = sorted(set(entry_ids) - nomination_ids)
        if duplicated or missing or extra:
            return await HttpResponseMethod.bad_request(
                data={**extra_data, "missing": missing, "extra": extra, "duplicated": duplicated},
                message="The ballot must include every nomination of the prize exactly once",
            )

        passed = [entry for entry in entries if entry.pass_ == 1]
        failed = [entry for entry in entries if entry.pass_ == 0]
        if any(entry.sort is not None for entry in failed):
            return await HttpResponseMethod.bad_request(
                data={**extra_data, "nominate_ids": [e.nominate_id for e in failed if e.sort is not None]},
                message="Nominations that did not pass must not have a sort value",
            )
        if any(entry.sort is None for entry in passed):
            return await HttpResponseMethod.bad_request(
                data={**extra_data, "nominate_ids": [e.nominate_id for e in passed if e.sort is None]},
                message="Nominations that passed must have a sort value",
            )
        sorts = sorted(entry.sort for entry in passed)
        if sorts != list(range(1, len(passed) + 1)):
            return await HttpResponseMethod.bad_request(
                data={**extra_data, "sorts": sorts, "expected": list(range(1, len(passed) + 1))},
                message="Sort values of passed nominations must be consecutive and start from 1",
            )
        return None

    @staticmethod
    def _build_votes(judge_id: int, n: int, entries, cur: int) -> List[Vote]:
        """VR11：依公式產生排序值與分數，忽略客戶端送出的分數"""
        return [
            Vote(
                judge_id=judge_id,
                nominate_id=entry.nominate_id,
                pass_=entry.pass_,
                sort=entry.sort if entry.pass_ == 1 else n,
                score=(n - entry.sort + 1) / n if entry.pass_ == 1 else 0.0,
                created_at=cur,
            )
            for entry in entries
        ]

    async def submit_batch(self, session: AsyncSession, data: BatchBallotRequest):
        """
        VPB：一位評審一次送出多個獎項的選票，全部成功或全部失敗。
        必須包含該會議中此評審尚未送出的所有可投票獎項（底下有提名的獎項），不可包含已送出的獎項。
        """
        try:
            judge = await self.crud_judge.get(session, id=data.judge_id)
            if judge is None:
                return await HttpResponseMethod.not_found(
                    message=f"Judge {data.judge_id} not found"
                )
            # rollback 會讓已載入的物件失效，之後只使用這兩個值，不再讀取 judge 的屬性
            judge_id, judge_meeting_id = judge.id, judge.meeting_id

            prize_ids = [ballot.prize_id for ballot in data.ballots]
            duplicated = sorted({i for i in prize_ids if prize_ids.count(i) > 1})
            if duplicated:
                return await HttpResponseMethod.bad_request(
                    data={"prize_ids": duplicated},
                    message="Duplicate prize_id in ballots",
                )

            # VR14：依 id 順序鎖定所有獎項，與單一獎項送出互斥，順序固定避免死結
            rows = (await session.execute(
                select(Prize).where(Prize.id.in_(prize_ids)).order_by(Prize.id).with_for_update()
            )).scalars().all()
            prizes = {prize.id: prize for prize in rows}
            not_found = [i for i in prize_ids if i not in prizes]
            if not_found:
                await session.rollback()
                return await HttpResponseMethod.not_found(
                    data={"prize_ids": not_found},
                    message=f"Prize {not_found[0]} not found",
                )

            # VR3：所有獎項都必須與評審屬於同一個會議
            foreign = [i for i in prize_ids if prizes[i].meeting_id != judge_meeting_id]
            if foreign:
                await session.rollback()
                return await HttpResponseMethod.bad_request(
                    data={"prize_ids": foreign, "judge_meeting_id": judge_meeting_id},
                    message="Judge and prize belong to different meetings",
                )

            # VR4：開始時間 <= 目前時間 < 截止時間
            meeting = await self.crud_meeting.get(session, id=judge_meeting_id)
            if not voting_started(meeting):
                await session.rollback()
                return await HttpResponseMethod.bad_request(message="Voting has not started yet")
            if voting_ended(meeting):
                await session.rollback()
                return await HttpResponseMethod.bad_request(message="Voting has ended")

            # 會議所有獎項的提名，用來判斷可投票獎項
            meeting_prize_ids = (await session.execute(
                select(Prize.id).where(Prize.meeting_id == meeting.id)
            )).scalars().all()
            all_nominations = await self.crud_nominate.get_multi(
                session, Nominate.prize_id.in_(meeting_prize_ids)
            ) if meeting_prize_ids else []
            nominations_of = {}
            for nomination in all_nominations:
                nominations_of.setdefault(nomination.prize_id, []).append(nomination)

            # VR12：送出的獎項必須有提名
            empty = [i for i in prize_ids if not nominations_of.get(i)]
            if empty:
                await session.rollback()
                return await HttpResponseMethod.bad_request(
                    data={"prize_ids": empty},
                    message=f"Prize {empty[0]} has no nominations",
                )

            # VR5：已送出的獎項不可再送出
            voted_nominate_ids = set((await session.execute(
                select(Vote.nominate_id).where(Vote.judge_id == judge_id)
            )).scalars().all())
            voted_prizes = {n.prize_id for n in all_nominations if n.id in voted_nominate_ids}
            already = [i for i in prize_ids if i in voted_prizes]
            if already:
                await session.rollback()
                return await HttpResponseMethod.bad_request(
                    data={"prize_ids": already},
                    message=f"Judge {judge_id} has already submitted a ballot for prize {already[0]}",
                )

            # 必須包含所有尚未送出的可投票獎項
            required = sorted(pid for pid in nominations_of if pid not in voted_prizes)
            missing = [pid for pid in required if pid not in prizes]
            if missing:
                await session.rollback()
                return await HttpResponseMethod.bad_request(
                    data={"missing_prize_ids": missing},
                    message="The batch must include every votable prize not yet submitted",
                )

            # 每張選票的內容檢查
            for ballot in data.ballots:
                ids = {n.id for n in nominations_of[ballot.prize_id]}
                error = await self._check_entries(ids, ballot.entries, prize_id=ballot.prize_id)
                if error is not None:
                    await session.rollback()
                    return error

            # 寫入所有選票，重新計算各獎項的提名，最後一次 commit
            cur = datetimeConverter.get_current_timestamp()
            created = {}
            for ballot in data.ballots:
                nominations = nominations_of[ballot.prize_id]
                votes = self._build_votes(judge_id, len(nominations), ballot.entries, cur)
                session.add_all(votes)
                created[ballot.prize_id] = votes
            await session.flush()
            for ballot in data.ballots:
                await self._recalculate(session, meeting, nominations_of[ballot.prize_id], cur)
            await session.commit()

            # 回應只含選票，不含提名的計分結果，避免評審在投票頁看到計分
            response_data = BatchBallotResponse(ballots=[
                BatchBallotResult(
                    prize_id=pid,
                    votes=[VoteResponse(**vote.dict()) for vote in sorted(created[pid], key=lambda v: v.id)],
                )
                for pid in sorted(created)
            ])
            return await HttpResponseMethod.ok(
                data=response_data.model_dump(by_alias=True),
                message=f"Ballots of judge {judge_id} for {len(created)} prizes submitted successfully",
            )
        except Exception as e:
            await session.rollback()
            return await HttpResponseMethod.server_error(e)

    async def _recalculate(
        self,
        session: AsyncSession,
        meeting: Meeting,
        nominations: List[Nominate],
        cur: int,
    ) -> None:
        """重新計算獎項中每個提名的總得分、平均序位與門檻結果"""
        nomination_ids = [nomination.id for nomination in nominations]
        votes = await self.crud_vote.get_multi(session, Vote.nominate_id.in_(nomination_ids))
        judges = await self.crud_judge.get_multi(session, meeting_id=meeting.id)

        # 用 Decimal 計算門檻，避免 0.7 × 10 = 7.000000000000001 之類的浮點誤差
        required = Decimal(str(meeting.proportion)) * len(judges)

        for nomination in nominations:
            nomination_votes = [vote for vote in votes if vote.nominate_id == nomination.id]
            if not nomination_votes:
                continue
            pass_count = sum(vote.pass_ for vote in nomination_votes)
            nomination.total_score = sum(vote.score for vote in nomination_votes)
            nomination.sort_average = sum(vote.sort for vote in nomination_votes) / len(nomination_votes)
            nomination.threshold = 1 if Decimal(pass_count) >= required else 0
            nomination.updated_at = cur

    async def get_all(
        self,
        session: AsyncSession,
        judge_id: Optional[int] = None,
        nominate_id: Optional[int] = None,
    ):
        try:
            filters = {}
            if judge_id is not None:
                filters["judge_id"] = judge_id
            if nominate_id is not None:
                filters["nominate_id"] = nominate_id

            results = await self.crud_vote.get_multi(session, **filters)
            response_data = [vote_to_dict(result) for result in sorted(results, key=lambda v: v.id)]
            return await HttpResponseMethod.ok(
                data=response_data,
                message=f"{len(response_data)} votes retrieved successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)

    async def get_by_id(self, session: AsyncSession, vote_id: int):
        try:
            result = await self.crud_vote.get(session, id=vote_id)
            if result is None:
                return await HttpResponseMethod.not_found(
                    message=f"Vote {vote_id} not found"
                )
            return await HttpResponseMethod.ok(
                data=vote_to_dict(result),
                message=f"Vote {vote_id} retrieved successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)
