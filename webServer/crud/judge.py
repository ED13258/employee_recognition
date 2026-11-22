from crud.base import CRUDBase
from model.judge import Judge
from schema.judge import JudgeCreate, JudgeUpdate


class CRUDJudge(CRUDBase[Judge, JudgeCreate, JudgeUpdate]):
    def __init__(self):
        super().__init__(Judge)
