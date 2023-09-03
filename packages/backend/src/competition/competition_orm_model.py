from sqlalchemy import (ARRAY,
                        Column,
                        Date,
                        Enum,
                        ForeignKey,
                        Integer,
                        String)
from sqlalchemy.orm import relationship

from ..database import Base
from ..enums.enum_sport_kind import SportKind


class Competition(Base):
    __tablename__ = 'competitions'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    date = Column(Date)
    class_list = Column(ARRAY(String))
    control_point_list = Column(ARRAY(String))
    sport_kind = Column(Enum(SportKind), nullable=True)
    format = Column(String, nullable=True)
    description = Column(String, nullable=True)
    location = Column(String, nullable=True)
    event = Column(
        Integer,
        ForeignKey(
            'events.id',
            ondelete='CASCADE',
            onupdate='CASCADE'
        ),
        nullable=True
    )

    parent_event = relationship('Event', back_populates='competitions')
