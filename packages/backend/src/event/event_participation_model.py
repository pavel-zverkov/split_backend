from sqlalchemy import (Column,
                        DateTime,
                        Enum,
                        ForeignKey,
                        Integer,
                        UniqueConstraint,
                        func)
from sqlalchemy.orm import relationship

from ..database import Base
from ..enums.event_role import EventRole
from ..enums.event_position import EventPosition
from ..enums.participation_status import ParticipationStatus


class EventParticipation(Base):
    """
    Represents a user's participation in an event.

    Users can participate in events with various roles:
    - Team roles: organizer, secretary, judge, volunteer (may have position: chief/deputy)
    - Athlete roles: participant, spectator

    For 'by_request' events, participation requires approval.

    Attributes:
        user_id: The participant.
        event_id: The event.
        role: organizer | secretary | judge | volunteer | participant | spectator.
        position: chief | deputy | null (only for team roles).
        status: pending | approved | rejected.
        joined_at: When participation was approved.
    """
    __tablename__ = 'event_participations'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=False)
    role = Column(Enum(EventRole), nullable=False)
    position = Column(Enum(EventPosition), nullable=True)
    status = Column(Enum(ParticipationStatus), nullable=False, default=ParticipationStatus.PENDING)
    joined_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('user_id', 'event_id', name='event_participation_unique'),
    )

    # Relationships
    user = relationship('User')
    event = relationship('Event')
