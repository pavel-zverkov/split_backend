from sqlalchemy import (Boolean,
                        Column,
                        DateTime,
                        Enum,
                        ForeignKey,
                        Integer,
                        UniqueConstraint,
                        func)
from sqlalchemy.orm import relationship

from ..database import Base
from ..enums.event_role import EventRole


class CompetitionTeam(Base):
    """
    Represents a team member's assignment to a specific competition.

    By default, event team members work on all competitions. This table allows
    overriding that behavior - either assigning specific roles per competition
    or excluding a member from a particular competition.

    If no record exists, the user inherits their role from EventParticipation.

    Attributes:
        competition_id: The competition.
        user_id: The team member.
        role: organizer | secretary | judge | volunteer.
        excluded: If true, user doesn't work on this competition.
    """
    __tablename__ = 'competition_teams'

    id = Column(Integer, primary_key=True, index=True)
    competition_id = Column(Integer, ForeignKey('competitions.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    role = Column(Enum(EventRole), nullable=False)
    excluded = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('competition_id', 'user_id', name='competition_team_unique'),
    )

    # Relationships
    competition = relationship('Competition')
    user = relationship('User')
