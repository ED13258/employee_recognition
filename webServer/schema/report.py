from typing import List, Optional

from pydantic import BaseModel


# ---- D2 獎項排名

class RankingItem(BaseModel):
    rank: Optional[int]          # 尚未有選票時為空值
    nominate_id: int
    manager_name: str            # 上司名稱
    employee_name: str           # 下屬名稱
    name: str
    threshold: Optional[int]
    sort_average: Optional[float]
    total_score: Optional[float]
    pass_count: int              # 投通過的評審數
    # VDQ1：計票結果頁的獎金計算表與排名一起顯示，空值代表尚未填寫
    issue_bonus: Optional[int]           # 核定獎金
    deduct_instant_bonus: Optional[int]  # 扣除即時獎勵
    comment: Optional[str]               # 備註


class RankingResponse(BaseModel):
    prize_id: int
    is_final: bool               # 會議已截止時為 true
    judge_count: int
    voted_judge_count: int
    items: List[RankingItem]


# ---- D3 投票進度

class ProgressJudge(BaseModel):
    judge_id: int
    name: str
    voted: bool
    voted_at: Optional[int]


class ProgressResponse(BaseModel):
    prize_id: int
    judge_count: int
    voted_judge_count: int
    judges: List[ProgressJudge]


# ---- D4 獎金彙總

class PrizeBonus(BaseModel):
    prize_id: int
    name: str
    issue_bonus: int
    deduct_instant_bonus: int
    net_bonus: int


class BonusSummaryResponse(BaseModel):
    meeting_id: int
    total_budget: int
    total_issue_bonus: int
    total_deduct_instant_bonus: int
    total_net_bonus: int
    remaining_budget: int        # DQ5：暫時以核定獎金計算
    over_budget: bool
    prizes: List[PrizeBonus]
