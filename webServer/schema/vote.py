from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from schema.nominate import NominateResponse


class BallotEntry(BaseModel):
    """選票中的一個項目。score 不在欄位中，客戶端送出也會被忽略（VR11）"""
    model_config = ConfigDict(populate_by_name=True)

    nominate_id: int
    pass_: Literal[0, 1] = Field(alias="pass", description="1 為通過，0 為未通過")
    sort: Optional[int] = Field(default=None, description="通過者的排序，從 1 開始；未通過者不可帶入")


class BallotRequest(BaseModel):
    """一整張選票：同一位評審對同一個獎項所有提名的投票"""
    judge_id: int
    prize_id: int
    entries: List[BallotEntry] = Field(min_length=1)


class BatchBallot(BaseModel):
    """批次送出中的一張選票"""
    prize_id: int
    entries: List[BallotEntry] = Field(min_length=1)


class BatchBallotRequest(BaseModel):
    """POST /votes/batch：一位評審一次送出多個獎項的選票，全部成功或全部失敗"""
    judge_id: int
    ballots: List[BatchBallot] = Field(min_length=1)


class VoteResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    judge_id: int
    nominate_id: int
    pass_: int = Field(alias="pass")
    sort: int
    score: float
    created_at: int


class BallotResponse(BaseModel):
    votes: List[VoteResponse]
    nominations: List[NominateResponse]


class BatchBallotResult(BaseModel):
    prize_id: int
    votes: List[VoteResponse]


class BatchBallotResponse(BaseModel):
    ballots: List[BatchBallotResult]


class VoteCreate(BaseModel):
    judge_id: int
    nominate_id: int
    pass_: int
    sort: int
    score: float
    created_at: int
