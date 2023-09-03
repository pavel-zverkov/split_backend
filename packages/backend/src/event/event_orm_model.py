from sqlalchemy import (Column,
                        Date,
                        Enum,
                        Integer,
                        String,
                        UniqueConstraint)
from sqlalchemy.orm import relationship

from ..database import Base
from ..enums.enum_sport_kind import SportKind
from ..enums.enum_status import Status


class Event(Base):
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    start_date = Column(Date)
    end_date = Column(Date)
    sport_kind = Column(Enum(SportKind))
    status = Column(Enum(Status))
    __table_args__ = (
        UniqueConstraint('name', 'sport_kind', name='event_unique_constraint'),
    )

    competitions = relationship('Competition', back_populates='parent_event')
