from crud.base import CRUDBase
from model.nominate import Nominate
from schema.nominate import NominateCreate, NominateUpdate


class CRUDNominate(CRUDBase[Nominate, NominateCreate, NominateUpdate]):
    def __init__(self):
        super().__init__(Nominate)
