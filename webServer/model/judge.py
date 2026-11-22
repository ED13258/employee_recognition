from sqlalchemy import Column, ForeignKey, Integer, String

from model.base import Base


class Judge(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    # 連鎖刪除：刪除會議時，底下的評審一起刪除（JR9）
    meeting_id = Column(
        Integer,
        ForeignKey("meeting.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(Integer, nullable=False)
