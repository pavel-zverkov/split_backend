from sqlalchemy import (ARRAY,
                        Column,
                        DateTime,
                        Enum,
                        ForeignKey,
                        Integer,
                        String,
                        func)
from sqlalchemy.orm import relationship

from ..database import Base
from ..enums.event_role import EventRole
from ..enums.event_position import EventPosition


class EventInvite(Base):
    """
    Represents an invite link for joining an event.

    Organizers can generate invite tokens that allow users to join events
    with pre-assigned roles and positions. Invites can expire or have usage limits.

    Attributes:
        event_id: The event this invite is for.
        token: Unique invite token.
        role: Role assigned to users who use this invite.
        position: Optional position (chief/deputy) for team roles.
        competition_ids: Pre-selected competitions for the invited user.
        expires_at: When the invite expires (null = never).
        max_uses: Maximum uses (null = unlimited).
        uses_count: Current usage count.
    """
    __tablename__ = 'event_invites'

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=False)
    token = Column(String, unique=True, nullable=False)
    role = Column(Enum(EventRole), nullable=False)
    position = Column(Enum(EventPosition), nullable=True)
    competition_ids = Column(ARRAY(Integer), nullable=True)
    expires_at = Column(DateTime, nullable=True)
    max_uses = Column(Integer, nullable=True)
    uses_count = Column(Integer, nullable=False, default=0)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    event = relationship('Event')
    creator = relationship('User', foreign_keys=[created_by])
