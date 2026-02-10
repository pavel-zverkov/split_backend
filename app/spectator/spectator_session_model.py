from sqlalchemy import (Column,
                        DateTime,
                        Enum,
                        ForeignKey,
                        Integer,
                        String,
                        func)
from sqlalchemy.orm import relationship

from ..database import Base
from ..enums.spectator_source import SpectatorSource


class SpectatorSession(Base):
    __tablename__ = 'spectator_sessions'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=False)
    competition_id = Column(Integer, ForeignKey('competitions.id'), nullable=True)
    session_start = Column(DateTime, server_default=func.now(), nullable=False)
    session_end = Column(DateTime, nullable=True)
    source = Column(Enum(SpectatorSource), nullable=False)
    ip_hash = Column(String, nullable=True)

    # Relationships
    user = relationship('User')
    event = relationship('Event')
    competition = relationship('Competition')
