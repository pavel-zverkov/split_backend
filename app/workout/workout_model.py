from sqlalchemy import (Column,
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
from ..enums.workout_status import WorkoutStatus
from ..enums.privacy import Privacy


class Workout(Base):
    __tablename__ = 'workouts'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    sport_kind = Column(Enum(SportKind), nullable=False)
    start_datetime = Column(DateTime, nullable=False)
    finish_datetime = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    distance_meters = Column(Integer, nullable=True)
    elevation_gain = Column(Integer, nullable=True)
    status = Column(Enum(WorkoutStatus), nullable=False, default=WorkoutStatus.DRAFT)
    privacy = Column(Enum(Privacy), nullable=False, default=Privacy.PRIVATE)
    fit_file = Column(String, nullable=True)
    gpx_file = Column(String, nullable=True)
    tcx_file = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    owner = relationship('User', back_populates='workouts', foreign_keys=[user_id])
    splits = relationship('WorkoutSplit', back_populates='workout', cascade='all, delete-orphan')
