from typing import List, Optional

from pydantic import BaseModel, Field

from schema.judge import JudgeResponse


class CreateRequest(BaseModel):
    name: str = Field(min_length=1)
    total_judges: int = Field(ge=1, description="總評審人數上限")
    total_budget: int = Field(ge=0, description="總預算")
    proportion: float = Field(default=0.75, gt=0, le=1, description="通過門檻比例 (0<x<=1)")
    voting_kickoff: int = Field(ge=0, description="投票開始時間 (timestamp)")
    voting_deadline: int = Field(ge=0, description="投票截止時間 (timestamp)")


class UpdateRequest(BaseModel):
    """
    部分更新：只會修改有帶入的欄位，created_at 不允許由客戶端修改。
    total_judges（評委人數）建立後不可修改（MDR12），不在此請求中，帶入時忽略。
    """
    id: int
    name: Optional[str] = Field(default=None, min_length=1)
    total_budget: Optional[int] = Field(default=None, ge=0)
    proportion: Optional[float] = Field(default=None, gt=0, le=1)
    voting_kickoff: Optional[int] = Field(default=None, ge=0)
    voting_deadline: Optional[int] = Field(default=None, ge=0)


class MeetingResponse(BaseModel):
    id: int
    name: str
    total_judges: int
    total_budget: int
    proportion: float
    voting_kickoff: int
    voting_deadline: int
    created_at: int


class MeetingWithJudgesResponse(MeetingResponse):
    """POST /meetings 的回應：會議與一併建立的評委（VP6.1）"""
    judges: List[JudgeResponse]


class MeetingWithProgressResponse(MeetingResponse):
    """GET /meetings 與 GET /meetings/{meeting_id} 的回應，加上選票進度（MP2）"""
    voted_judge_count: int       # 已投完所有可投票獎項的評審人數
    vote_progress: float         # 選票進度：voted_judge_count / total_judges，0 到 1，只到小數點第二位（無條件捨去）


class MeetingCreate(BaseModel):
    name: str
    total_judges: int
    total_budget: int
    proportion: float
    voting_kickoff: int
    voting_deadline: int
    created_at: int


class MeetingUpdate(BaseModel):
    name: Optional[str] = None
    total_budget: Optional[int] = None
    proportion: Optional[float] = None
    voting_kickoff: Optional[int] = None
    voting_deadline: Optional[int] = None
