from sqlalchemy import (Column,
                        ForeignKey,
                        Integer)

from ..database import Base


class CompetitionEventRelation(Base):
    __tablename__ = 'competitions_events'

    id = Column(Integer, primary_key=True)
    competition = Column(Integer, ForeignKey('competitions.id'))
    event = Column(Integer, ForeignKey('events.id'))
