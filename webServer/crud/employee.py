from crud.base import CRUDBase
from model.employee import Employee
from schema.employee import EmployeeCreate, EmployeeUpdate


class CRUDEmployee(CRUDBase[Employee, EmployeeCreate, EmployeeUpdate]):
    def __init__(self):
        super().__init__(Employee)
