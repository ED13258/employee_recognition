from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from schema.employee import CreateRequest, UpdateRequest
from service.employee import EmployeeService

router = APIRouter(prefix="/employees", tags=["employees"])

_service = EmployeeService()


@router.post("")
async def create_employee(
    data: CreateRequest,
    session: AsyncSession = Depends(get_session),
):
    return await _service.create(session, data)


@router.get("")
async def get_employees(
    manager_id: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
):
    return await _service.get_all(session, manager_id)


@router.get("/{employee_id}")
async def get_employee(
    employee_id: int,
    session: AsyncSession = Depends(get_session),
):
    return await _service.get_by_id(session, employee_id)


@router.put("")
async def update_employee(
    data: UpdateRequest,
    session: AsyncSession = Depends(get_session),
):
    return await _service.update(session, data)


@router.delete("/{employee_id}")
async def delete_employee(
    employee_id: int,
    session: AsyncSession = Depends(get_session),
):
    return await _service.delete(session, employee_id)
