from typing import List, Optional

from pydantic import BaseModel, Field

from schema.nominate import NominateResponse, PersonName


class NominationInput(BaseModel):
    """新增獎項時一併建立的提名（MD6.1）"""
    manager_name: PersonName = Field(description="上司名稱")
    name: str = Field(min_length=1, description="提名名稱")
    employee_name: PersonName = Field(description="下屬名稱")


class CreateRequest(BaseModel):
    name: str = Field(min_length=1, description="獎項名稱")
    meeting_id: int = Field(description="所屬會議")
    # 選填：不帶時行為與擴充前相同。帶入時與獎項在同一個交易中建立，全部成功或全部失敗（MDQ1）
    nominations: List[NominationInput] = Field(default_factory=list, description="提名名單")


class UpdateRequest(BaseModel):
    """部分更新：只能修改名稱，meeting_id 與 created_at 不允許由客戶端修改"""
    id: int
    name: Optional[str] = Field(default=None, min_length=1)


class PrizeResponse(BaseModel):
    id: int
    name: str
    meeting_id: int
    created_at: int


class PrizeWithNominationsResponse(PrizeResponse):
    """POST /prizes 的回應：獎項與一併建立的提名"""
    nominations: List[NominateResponse]


class BonusItem(BaseModel):
    """
    批次儲存獎金的一筆提名（VD6.2）。
    使用 exclude_unset 判斷有帶入的欄位：帶入 null 代表清空，沒帶代表維持原值，與 PUT /nominations 相同。
    """
    nominate_id: int
    issue_bonus: Optional[int] = Field(default=None, ge=0, description="核定獎金")
    deduct_instant_bonus: Optional[int] = Field(default=None, ge=0, description="扣除即時獎勵")
    comment: Optional[str] = Field(default=None, description="備註")


class BonusBatchRequest(BaseModel):
    """PUT /prizes/{prize_id}/bonuses：同一獎項的多筆提名，全部成功或全部失敗（VDQ2）"""
    items: List[BonusItem] = Field(min_length=1)


class PrizeCreate(BaseModel):
    name: str
    meeting_id: int
    created_at: int


class PrizeUpdate(BaseModel):
    name: Optional[str] = None
