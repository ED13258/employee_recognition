from crud.base import CRUDBase
from model.vote import Vote
from schema.vote import VoteCreate


class CRUDVote(CRUDBase[Vote, VoteCreate, VoteCreate]):
    """
    查詢沿用 CRUDBase 的 get 與 get_multi。
    寫入不使用 CRUDBase.create，因為它會立即 commit，
    無法和提名的重新計算放在同一個交易中（VR13），改由 VoteService 直接操作 session。
    """
    def __init__(self):
        super().__init__(Vote)
