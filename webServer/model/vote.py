from sqlalchemy import Column, Float, ForeignKey, Integer, UniqueConstraint

from model.base import Base


class Vote(Base):
    # VR5：同一位評審對同一個提名只能有一筆選票
    __table_args__ = (
        UniqueConstraint("judge_id", "nominate_id", name="uq_vote_judge_nominate"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 兩個外鍵都連鎖刪除：只有在投票開始前刪除會議時才會發生，而那時不會有選票
    judge_id = Column(
        Integer,
        ForeignKey("judge.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nominate_id = Column(
        Integer,
        ForeignKey("nominate.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # pass 是 Python 保留字：屬性命名為 pass_，資料庫欄位名稱仍為 pass
    pass_ = Column("pass", Integer, nullable=False)
    sort = Column(Integer, nullable=False)
    score = Column(Float, nullable=False)
    created_at = Column(Integer, nullable=False)
