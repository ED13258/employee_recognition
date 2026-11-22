from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.httpResponseMethod import HttpResponseMethod
from crud.employee import CRUDEmployee
from crud.manager import CRUDManager
from schema.employee import CreateRequest, UpdateRequest, EmployeeResponse, EmployeeCreate, EmployeeUpdate

from util.datetimeConverter import datetimeConverter


class EmployeeService:

    def __init__(self):
        self.crud_employee = CRUDEmployee()
        self.crud_manager = CRUDManager()

    async def create(self, session: AsyncSession, data: CreateRequest):
        try:
            # ER3：所屬上司必須存在
            manager = await self.crud_manager.get(session, id=data.manager_id)
            if manager is None:
                return await HttpResponseMethod.not_found(
                    message=f"Manager {data.manager_id} not found"
                )

            # ER2：created_at 由伺服器產生
            create_data = EmployeeCreate(
                **data.model_dump(),
                created_at=datetimeConverter.get_current_timestamp(),
            )

            result = await self.crud_employee.create(session, obj_in=create_data)
            response_data = EmployeeResponse(**result.dict())

            return await HttpResponseMethod.ok(
                data=response_data.model_dump(),
                message=f"Employee {result.id} created successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)

    async def get_all(self, session: AsyncSession, manager_id: Optional[int] = None):
        try:
            filters = {} if manager_id is None else {"manager_id": manager_id}
            results = await self.crud_employee.get_multi(session, **filters)
            response_data = [
                EmployeeResponse(**result.dict()).model_dump()
                for result in sorted(results, key=lambda e: e.id)
            ]
            return await HttpResponseMethod.ok(
                data=response_data,
                message=f"{len(response_data)} employees retrieved successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)

    async def get_by_id(self, session: AsyncSession, employee_id: int):
        try:
            result = await self.crud_employee.get(session, id=employee_id)
            if result is None:
                return await HttpResponseMethod.not_found(
                    message=f"Employee {employee_id} not found"
                )
            response_data = EmployeeResponse(**result.dict())
            return await HttpResponseMethod.ok(
                data=response_data.model_dump(),
                message=f"Employee {employee_id} retrieved successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)

    async def update(self, session: AsyncSession, data: UpdateRequest):
        try:
            employee_id = data.id

            db_obj = await self.crud_employee.get(session, id=employee_id)
            if db_obj is None:
                return await HttpResponseMethod.not_found(
                    message=f"Employee {employee_id} not found"
                )

            # ER4、ER6：可修改名稱與所屬上司；ER2：created_at 不在可修改範圍內
            update_data = EmployeeUpdate(
                **data.model_dump(exclude={"id"}, exclude_none=True)
            ).model_dump(exclude_none=True)

            # ER6：更換上司時，新上司必須存在
            if "manager_id" in update_data:
                manager = await self.crud_manager.get(session, id=update_data["manager_id"])
                if manager is None:
                    return await HttpResponseMethod.not_found(
                        message=f"Manager {update_data['manager_id']} not found"
                    )

            result = await self.crud_employee.update(session, obj_in=update_data, db_obj=db_obj)
            response_data = EmployeeResponse(**result.dict())
            return await HttpResponseMethod.ok(
                data=response_data.model_dump(),
                message=f"Employee {employee_id} updated successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)

    async def delete(self, session: AsyncSession, employee_id: int):
        try:
            db_obj = await self.crud_employee.get(session, id=employee_id)
            if db_obj is None:
                return await HttpResponseMethod.not_found(
                    message=f"Employee {employee_id} not found"
                )

            # NCR5：提名改為記錄名稱，不再參照下屬，所以移除 ER7 的提名檢查

            await self.crud_employee.delete(session, db_obj=db_obj)
            return await HttpResponseMethod.ok(
                message=f"Employee {employee_id} deleted successfully",
            )
        except Exception as e:
            return await HttpResponseMethod.server_error(e)
