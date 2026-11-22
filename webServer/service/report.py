from fractions import Fraction

from sqlalchemy.ext.asyncio import AsyncSession

from core.httpResponseMethod import HttpResponseMethod
from crud.judge import CRUDJudge
from crud.meeting import CRUDMeeting
from crud.nominate import CRUDNominate
from crud.prize import CRUDPrize
from crud.vote import CRUDVote
from model.nominate import Nominate
from model.vote import Vote
from schema.report import (
    BonusSummaryResponse,
    PrizeBonus,
    ProgressJudge,
    ProgressResponse,
    RankingItem,
    RankingResponse,
)

from util.votingPeriod import voting_ended

# DR1：門檻分組的先後順序。通過在前，未通過在後，尚未有選票的放最後
GROUP_PASSED, GROUP_FAILED, GROUP_NO_VOTES = 0, 1, 2


class ReportService:
    """跨表的唯讀彙總查詢，不會修改任何資料"""

    def __init__(self):
        self.crud_meeting = CRUDMeeting()
        self.crud_prize = CRUDPrize()
        self.crud_nominate = CRUDNominate()
        self.crud_judge = CRUDJudge()
        self.crud_vote = CRUDVote()

    async def _prize_votes(self, session: AsyncSession, nominations):
        ids = [nomination.id for nomination in nominations]
        if not ids:
            return []
        return await self.crud_vote.get_multi(session, Vote.nominate_id.in_(ids))

    # ---- D2 獎項排名

    async def get_ranking(self, session: AsyncSession, prize_id: int):
        try:
            prize = await self.crud_prize.get(session, id=prize_id)
            if prize is None:
                return await HttpResponseMethod.not_found(
                    message=f"Prize {prize_id} not found"
                )

            meeting = await self.crud_meeting.get(session, id=prize.meeting_id)
            judges = await self.crud_judge.get_multi(session, meeting_id=meeting.id)
            nominations = await self.crud_nominate.get_multi(session, prize_id=prize_id)
            votes = await self._prize_votes(session, nominations)

            rows = []
            for nomination in nominations:
                nomination_votes = [vote for vote in votes if vote.nominate_id == nomination.id]
                if nomination_votes:
                    group = GROUP_PASSED if nomination.threshold == 1 else GROUP_FAILED
                    # 同分判斷不用浮點數：以排序值總和 / 選票數的精確分數比較平均序位
                    average = Fraction(sum(vote.sort for vote in nomination_votes), len(nomination_votes))
                else:
                    group, average = GROUP_NO_VOTES, None
                rows.append({
                    "nomination": nomination,
                    "group": group,
                    "average": average,
                    "pass_count": sum(vote.pass_ for vote in nomination_votes),
                })

            # DR1、DR2：先依門檻分組，組內依平均序位由小到大，最後以 id 讓順序固定
            rows.sort(key=lambda r: (r["group"], r["average"] if r["average"] is not None else 0, r["nomination"].id))

            # DR3、DR4：同分並列、下一名跳號、跨組連續編號；尚未有選票的沒有名次
            items = []
            previous_key, previous_rank = None, None
            for position, row in enumerate(rows, start=1):
                if row["group"] == GROUP_NO_VOTES:
                    rank = None
                else:
                    key = (row["group"], row["average"])
                    rank = previous_rank if key == previous_key else position
                    previous_key, previous_rank = key, rank
                nomination = row["nomination"]
                items.append(RankingItem(
                    rank=rank,
                    nominate_id=nomination.id,
                    manager_name=nomination.manager_name,
                    employee_name=nomination.employee_name,
                    name=nomination.name,
                    threshold=nomination.threshold,
                    sort_average=nomination.sort_average,
                    total_score=nomination.total_score,
                    pass_count=row["pass_count"],
                    issue_bonus=nomination.issue_bonus,
                    deduct_instant_bonus=nomination.deduct_instant_bonus,
                    comment=nomination.comment,
                ))

            response_data = RankingResponse(
                prize_id=prize_id,
                is_final=voting_ended(meeting),
                judge_count=len(judges),
                voted_judge_count=len({vote.judge_id for vote in votes}),
                items=items,
            )
            return await HttpResponseMethod.ok(
                data=response_data.model_dump(),
                message=f"Ranking of prize {prize_id} retrieved successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)

    # ---- D3 投票進度

    async def get_progress(self, session: AsyncSession, prize_id: int):
        try:
            prize = await self.crud_prize.get(session, id=prize_id)
            if prize is None:
                return await HttpResponseMethod.not_found(
                    message=f"Prize {prize_id} not found"
                )

            judges = await self.crud_judge.get_multi(session, meeting_id=prize.meeting_id)
            nominations = await self.crud_nominate.get_multi(session, prize_id=prize_id)
            votes = await self._prize_votes(session, nominations)

            # 評審只要有一筆選票屬於此獎項，就視為已投票
            voted_at = {}
            for vote in votes:
                voted_at[vote.judge_id] = min(vote.created_at, voted_at.get(vote.judge_id, vote.created_at))

            progress = [
                ProgressJudge(
                    judge_id=judge.id,
                    name=judge.name,
                    voted=judge.id in voted_at,
                    voted_at=voted_at.get(judge.id),
                )
                for judge in sorted(judges, key=lambda j: j.id)
            ]
            response_data = ProgressResponse(
                prize_id=prize_id,
                judge_count=len(judges),
                voted_judge_count=sum(1 for p in progress if p.voted),
                judges=progress,
            )
            return await HttpResponseMethod.ok(
                data=response_data.model_dump(),
                message=f"Voting progress of prize {prize_id} retrieved successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)

    # ---- D4 獎金彙總

    async def get_bonus_summary(self, session: AsyncSession, meeting_id: int):
        try:
            meeting = await self.crud_meeting.get(session, id=meeting_id)
            if meeting is None:
                return await HttpResponseMethod.not_found(
                    message=f"Meeting {meeting_id} not found"
                )

            prizes = await self.crud_prize.get_multi(session, meeting_id=meeting_id)
            prize_ids = [prize.id for prize in prizes]
            nominations = (
                await self.crud_nominate.get_multi(session, Nominate.prize_id.in_(prize_ids))
                if prize_ids else []
            )

            # 空值的獎金視為 0
            prize_bonuses = []
            for prize in sorted(prizes, key=lambda p: p.id):
                prize_nominations = [n for n in nominations if n.prize_id == prize.id]
                issue = sum(n.issue_bonus or 0 for n in prize_nominations)
                deduct = sum(n.deduct_instant_bonus or 0 for n in prize_nominations)
                prize_bonuses.append(PrizeBonus(
                    prize_id=prize.id,
                    name=prize.name,
                    issue_bonus=issue,
                    deduct_instant_bonus=deduct,
                    net_bonus=issue - deduct,
                ))

            total_issue = sum(p.issue_bonus for p in prize_bonuses)
            total_deduct = sum(p.deduct_instant_bonus for p in prize_bonuses)

            # DQ5：剩餘預算暫時以核定獎金計算。若改以實發金額計算，將 total_issue 換成 total_issue - total_deduct
            response_data = BonusSummaryResponse(
                meeting_id=meeting_id,
                total_budget=meeting.total_budget,
                total_issue_bonus=total_issue,
                total_deduct_instant_bonus=total_deduct,
                total_net_bonus=total_issue - total_deduct,
                remaining_budget=meeting.total_budget - total_issue,
                over_budget=total_issue > meeting.total_budget,
                prizes=prize_bonuses,
            )
            return await HttpResponseMethod.ok(
                data=response_data.model_dump(),
                message=f"Bonus summary of meeting {meeting_id} retrieved successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)
