from sqlalchemy import (Column, Date,
                        Enum, ForeignKey,
                        Integer,
                        String, ARRAY)

from ..database import Base
from ..enums.enum_sport_kind import SportKind


class Competition(Base):
    __tablename__ = 'competitions'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    date = Column(Date)
    class_list = Column(ARRAY(String))
    control_point_list = Column(ARRAY(String))
    kind = Column(Enum(SportKind), nullable=True)
    format = Column(String, nullable=True)
    event = Column(Integer, ForeignKey('events.id'), nullable=True)
