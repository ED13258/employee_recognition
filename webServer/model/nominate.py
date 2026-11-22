from sqlalchemy import Column, Float, ForeignKey, Integer, String

from model.base import Base


class Nominate(Base):
    # 為了快速開發，提名暫時不參照 manager、employee 表，直接記錄上司與下屬名稱。
    # 依 NCQ1 決議不檢查重複提名，所以沒有唯一限制。

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 連鎖刪除：刪除會議時，獎項與提名一起刪除。透過 API 刪除獎項時由 R6 擋下
    prize_id = Column(
        Integer,
        ForeignKey("prize.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    manager_name = Column(String, nullable=False)    # 上司名稱
    employee_name = Column(String, nullable=False)   # 下屬名稱
    name = Column(String, nullable=False)            # 提名名稱
    # 計分結果由 vote 層計算，客戶端不可寫入（NR6）
    total_score = Column(Float, nullable=True)
    sort_average = Column(Float, nullable=True)
    threshold = Column(Integer, nullable=True)
    issue_bonus = Column(Integer, nullable=True)
    deduct_instant_bonus = Column(Integer, nullable=True)
    comment = Column(String, nullable=True)
    created_at = Column(Integer, nullable=False)
    updated_at = Column(Integer, nullable=False)
