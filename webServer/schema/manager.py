from typing import Optional

from pydantic import BaseModel, Field


class CreateRequest(BaseModel):
    name: str = Field(min_length=1, description="上司名稱")


class UpdateRequest(BaseModel):
    """部分更新：只能修改名稱，created_at 不允許由客戶端修改"""
    id: int
    name: Optional[str] = Field(default=None, min_length=1)


class ManagerResponse(BaseModel):
    id: int
    name: str
    created_at: int


class ManagerCreate(BaseModel):
    name: str
    created_at: int


class ManagerUpdate(BaseModel):
    name: Optional[str] = None
