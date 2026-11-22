from typing import Optional

from pydantic import BaseModel, Field


class CreateRequest(BaseModel):
    name: str = Field(min_length=1, description="評審名稱")
    meeting_id: int = Field(description="所屬會議")


class UpdateRequest(BaseModel):
    """部分更新：只能修改名稱，meeting_id 與 created_at 不允許由客戶端修改"""
    id: int
    name: Optional[str] = Field(default=None, min_length=1)


class JudgeResponse(BaseModel):
    id: int
    name: str
    meeting_id: int
    created_at: int


class JudgeCreate(BaseModel):
    name: str
    meeting_id: int
    created_at: int


class JudgeUpdate(BaseModel):
    name: Optional[str] = None
