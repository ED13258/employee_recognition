from crud.base import CRUDBase
from model.prize import Prize
from schema.prize import PrizeCreate, PrizeUpdate


class CRUDPrize(CRUDBase[Prize, PrizeCreate, PrizeUpdate]):
    def __init__(self):
        super().__init__(Prize)
