from sqlalchemy import Column, ForeignKey, Integer, String

from model.base import Base


class Prize(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    meeting_id = Column(
        Integer,
        ForeignKey("meeting.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(Integer, nullable=False)
