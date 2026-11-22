from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from schema.manager import CreateRequest, UpdateRequest
from service.manager import ManagerService

router = APIRouter(prefix="/managers", tags=["managers"])

_service = ManagerService()


@router.post("")
async def create_manager(
    data: CreateRequest,
    session: AsyncSession = Depends(get_session),
):
    return await _service.create(session, data)


@router.get("")
async def get_managers(
    session: AsyncSession = Depends(get_session),
):
    return await _service.get_all(session)


@router.get("/{manager_id}")
async def get_manager(
    manager_id: int,
    session: AsyncSession = Depends(get_session),
):
    return await _service.get_by_id(session, manager_id)


@router.put("")
async def update_manager(
    data: UpdateRequest,
    session: AsyncSession = Depends(get_session),
):
    return await _service.update(session, data)


@router.delete("/{manager_id}")
async def delete_manager(
    manager_id: int,
    session: AsyncSession = Depends(get_session),
):
    return await _service.delete(session, manager_id)
