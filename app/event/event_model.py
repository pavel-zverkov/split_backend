from sqlalchemy import (ARRAY,
                        Boolean,
                        Column,
                        Date,
                        DateTime,
                        Enum,
                        ForeignKey,
                        Integer,
                        String,
                        Text,
                        UniqueConstraint,
                        func)
from sqlalchemy.orm import relationship

from ..database import Base
from ..enums.sport_kind import SportKind
from ..enums.event_status import EventStatus
from ..enums.event_format import EventFormat
from ..enums.privacy import Privacy


class Event(Base):
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    logo = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    location = Column(String, nullable=True)
    sport_kind = Column(Enum(SportKind), nullable=False)
    privacy = Column(Enum(Privacy), nullable=False, default=Privacy.PUBLIC)
    event_format = Column(Enum(EventFormat), nullable=False, default=EventFormat.MULTI_STAGE)
    status = Column(Enum(EventStatus), nullable=False, default=EventStatus.PLANNED)
    max_participants = Column(Integer, nullable=True)
    recruitment_open = Column(Boolean, nullable=False, default=False)
    needed_roles = Column(ARRAY(String), nullable=True)
    organizer_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('name', 'sport_kind', name='event_unique_constraint'),
    )

    # Relationships
    competitions = relationship('Competition', back_populates='parent_event', cascade='all, delete-orphan')
    organizer = relationship('User', foreign_keys=[organizer_id])
