from sqlalchemy import (Column,
                        DateTime,
                        Enum,
                        ForeignKey,
                        Integer,
                        String,
                        UniqueConstraint,
                        func)
from sqlalchemy.orm import relationship

from ..database import Base
from ..enums.registration_status import RegistrationStatus


class CompetitionRegistration(Base):
    """
    Represents an athlete's registration for a specific competition.

    Athletes register for competitions within an event. Status inherits from
    EventParticipation at creation time (pending -> pending, approved -> registered).

    Attributes:
        user_id: The athlete.
        competition_id: The competition.
        class_: Competition class (age/gender group, e.g., 'M21', 'W35').
        bib_number: Start number assigned by organizer.
        start_time: Individual start time (for separated_start format).
        status: pending | registered | confirmed | rejected.
    """
    __tablename__ = 'competition_registrations'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    competition_id = Column(Integer, ForeignKey('competitions.id'), nullable=False)
    class_ = Column('class', String, nullable=True)
    bib_number = Column(String, nullable=True)
    start_time = Column(DateTime, nullable=True)
    status = Column(Enum(RegistrationStatus), nullable=False, default=RegistrationStatus.PENDING)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('user_id', 'competition_id', name='competition_registration_unique'),
    )

    # Relationships
    user = relationship('User')
    competition = relationship('Competition')
