
from sqlalchemy import (Column,
                        Date,
                        Enum, ForeignKey,
                        Integer,
                        String)

from ..database import Base
from ..enums.enum_sport_kind import SportKind


class Event(Base):
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    date = Column(Date)
    sport_kind = Column(Enum(SportKind))
    competition = Column(Integer, ForeignKey('competitions.id'), nullable=True)
