from typing import Optional

from pydantic import BaseModel, Field


class CreateRequest(BaseModel):
    name: str = Field(min_length=1, description="下屬名稱")
    manager_id: int = Field(description="所屬上司")


class UpdateRequest(BaseModel):
    """部分更新：可修改名稱與所屬上司，created_at 不允許由客戶端修改"""
    id: int
    name: Optional[str] = Field(default=None, min_length=1)
    manager_id: Optional[int] = None


class EmployeeResponse(BaseModel):
    id: int
    manager_id: int
    name: str
    created_at: int


class EmployeeCreate(BaseModel):
    manager_id: int
    name: str
    created_at: int


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    manager_id: Optional[int] = None
