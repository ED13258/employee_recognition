from sqlalchemy import Column, Integer, String, Float

from model.base import Base


class Meeting(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    total_judges = Column(Integer, nullable=False)
    total_budget = Column(Integer, nullable=False)
    proportion = Column(Float, nullable=False)
    voting_kickoff = Column(Integer, nullable=False)
    voting_deadline = Column(Integer, nullable=False)
    created_at = Column(Integer, nullable=False)
