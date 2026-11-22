from typing import Annotated, Optional

from pydantic import BaseModel, Field, StringConstraints

# 上司、下屬名稱：去除前後空白後至少 1 個字元（NCR1）
PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class CreateRequest(BaseModel):
    """計分結果、獎金、created_at 與 updated_at 都不允許由客戶端在新增時寫入"""
    prize_id: int = Field(description="所屬獎項")
    manager_name: PersonName = Field(description="上司名稱")
    employee_name: PersonName = Field(description="下屬名稱")
    name: str = Field(min_length=1, description="提名名稱")
    comment: Optional[str] = Field(default=None, description="備註")


class UpdateRequest(BaseModel):
    """
    部分更新：可修改提名名稱、上司與下屬名稱、獎金與備註。
    使用 exclude_unset 判斷有帶入的欄位，所以帶入 null 可以清空獎金與備註。
    上司與下屬名稱只能在投票開始前修改（NCR4）。
    prize_id 與計分結果不在可修改範圍內（NR4、NR6）。
    """
    id: int
    name: Optional[str] = Field(default=None, min_length=1)
    manager_name: Optional[PersonName] = Field(default=None, description="上司名稱")
    employee_name: Optional[PersonName] = Field(default=None, description="下屬名稱")
    issue_bonus: Optional[int] = Field(default=None, ge=0, description="核定獎金")
    deduct_instant_bonus: Optional[int] = Field(default=None, ge=0, description="扣除即時獎金")
    comment: Optional[str] = None


class NominateResponse(BaseModel):
    id: int
    prize_id: int
    manager_name: str
    employee_name: str
    name: str
    total_score: Optional[float]
    sort_average: Optional[float]
    threshold: Optional[int]
    issue_bonus: Optional[int]
    deduct_instant_bonus: Optional[int]
    comment: Optional[str]
    created_at: int
    updated_at: int


class NominateCreate(BaseModel):
    prize_id: int
    manager_name: str
    employee_name: str
    name: str
    comment: Optional[str] = None
    created_at: int
    updated_at: int


class NominateUpdate(BaseModel):
    name: Optional[str] = None
    manager_name: Optional[str] = None
    employee_name: Optional[str] = None
    issue_bonus: Optional[int] = None
    deduct_instant_bonus: Optional[int] = None
    comment: Optional[str] = None
    updated_at: int
