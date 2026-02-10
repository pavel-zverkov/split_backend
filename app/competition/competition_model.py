from sqlalchemy import (ARRAY,
                        Column,
                        Date,
                        DateTime,
                        Enum,
                        ForeignKey,
                        Integer,
                        String,
                        Text,
                        func)
from sqlalchemy.orm import relationship

from ..database import Base
from ..enums.sport_kind import SportKind
from ..enums.start_format import StartFormat
from ..enums.competition_status import CompetitionStatus


class Competition(Base):
    __tablename__ = 'competitions'

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(
        Integer,
        ForeignKey('events.id', ondelete='CASCADE', onupdate='CASCADE'),
        nullable=False
    )
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    date = Column(Date, nullable=False)
    sport_kind = Column(Enum(SportKind), nullable=True)
    start_format = Column(Enum(StartFormat), nullable=False, default=StartFormat.SEPARATED_START)
    class_list = Column(ARRAY(String), nullable=True)
    control_points_list = Column(ARRAY(String), nullable=True)
    distance_meters = Column(Integer, nullable=True)
    location = Column(String, nullable=True)
    status = Column(Enum(CompetitionStatus), nullable=False, default=CompetitionStatus.PLANNED)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    parent_event = relationship('Event', back_populates='competitions')
    results = relationship('Result', back_populates='competition', cascade='all, delete-orphan')
