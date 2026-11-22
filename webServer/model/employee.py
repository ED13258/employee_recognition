from sqlalchemy import Column, ForeignKey, Integer, String

from model.base import Base


class Employee(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    # 不設定 ondelete：上司還有下屬時，資料庫會拒絕刪除上司（MR5）
    manager_id = Column(
        Integer,
        ForeignKey("manager.id"),
        nullable=False,
        index=True,
    )
    name = Column(String, nullable=False)
    created_at = Column(Integer, nullable=False)
