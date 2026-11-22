from sqlalchemy.ext.asyncio import AsyncSession

from core.httpResponseMethod import HttpResponseMethod
from crud.employee import CRUDEmployee
from crud.manager import CRUDManager
from schema.manager import CreateRequest, UpdateRequest, ManagerResponse, ManagerCreate, ManagerUpdate

from util.datetimeConverter import datetimeConverter


class ManagerService:

    def __init__(self):
        self.crud_manager = CRUDManager()
        self.crud_employee = CRUDEmployee()

    async def create(self, session: AsyncSession, data: CreateRequest):
        try:
            # MR2：created_at 由伺服器產生
            create_data = ManagerCreate(
                **data.model_dump(),
                created_at=datetimeConverter.get_current_timestamp(),
            )

            result = await self.crud_manager.create(session, obj_in=create_data)
            response_data = ManagerResponse(**result.dict())

            return await HttpResponseMethod.ok(
                data=response_data.model_dump(),
                message=f"Manager {result.id} created successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)

    async def get_all(self, session: AsyncSession):
        try:
            results = await self.crud_manager.get_multi(session)
            response_data = [
                ManagerResponse(**result.dict()).model_dump()
                for result in sorted(results, key=lambda m: m.id)
            ]
            return await HttpResponseMethod.ok(
                data=response_data,
                message=f"{len(response_data)} managers retrieved successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)

    async def get_by_id(self, session: AsyncSession, manager_id: int):
        try:
            result = await self.crud_manager.get(session, id=manager_id)
            if result is None:
                return await HttpResponseMethod.not_found(
                    message=f"Manager {manager_id} not found"
                )
            response_data = ManagerResponse(**result.dict())
            return await HttpResponseMethod.ok(
                data=response_data.model_dump(),
                message=f"Manager {manager_id} retrieved successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)

    async def update(self, session: AsyncSession, data: UpdateRequest):
        try:
            manager_id = data.id

            db_obj = await self.crud_manager.get(session, id=manager_id)
            if db_obj is None:
                return await HttpResponseMethod.not_found(
                    message=f"Manager {manager_id} not found"
                )

            # MR3：名稱隨時可以修改；MR2：created_at 不在可修改範圍內
            update_data = ManagerUpdate(
                **data.model_dump(exclude={"id"}, exclude_none=True)
            ).model_dump(exclude_none=True)

            result = await self.crud_manager.update(session, obj_in=update_data, db_obj=db_obj)
            response_data = ManagerResponse(**result.dict())
            return await HttpResponseMethod.ok(
                data=response_data.model_dump(),
                message=f"Manager {manager_id} updated successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)

    async def delete(self, session: AsyncSession, manager_id: int):
        try:
            db_obj = await self.crud_manager.get(session, id=manager_id)
            if db_obj is None:
                return await HttpResponseMethod.not_found(
                    message=f"Manager {manager_id} not found"
                )

            # MR5：上司底下還有下屬時不得刪除
            employees = await self.crud_employee.get_multi(session, manager_id=manager_id)
            if employees:
                return await HttpResponseMethod.bad_request(
                    data={"employee_count": len(employees)},
                    message=f"Manager {manager_id} still has employees; transfer or delete them first",
                )

            await self.crud_manager.delete(session, db_obj=db_obj)
            return await HttpResponseMethod.ok(
                message=f"Manager {manager_id} deleted successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)
