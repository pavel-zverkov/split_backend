from sqlalchemy import (Column,
                        ForeignKey,
                        Integer,
                        String,
                        UniqueConstraint)
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

from ..database import Base


class WorkoutSplit(Base):
    __tablename__ = 'workout_splits'

    id = Column(Integer, primary_key=True, index=True)
    workout_id = Column(Integer, ForeignKey('workouts.id'), nullable=False)
    sequence = Column(Integer, nullable=False)
    control_point = Column(String, nullable=True)
    distance_meters = Column(Integer, nullable=True)
    cumulative_time = Column(Integer, nullable=False)
    split_time = Column(Integer, nullable=False)
    position = Column(Geometry('POINT'), nullable=True)

    __table_args__ = (
        UniqueConstraint('workout_id', 'sequence', name='workout_split_unique'),
    )

    # Relationships
    workout = relationship('Workout', back_populates='splits')
