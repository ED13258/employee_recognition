from crud.base import CRUDBase
from model.manager import Manager
from schema.manager import ManagerCreate, ManagerUpdate


class CRUDManager(CRUDBase[Manager, ManagerCreate, ManagerUpdate]):
    def __init__(self):
        super().__init__(Manager)
