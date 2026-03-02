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
from ..enums.result_status import ResultStatus


class Result(Base):
    __tablename__ = 'results'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    competition_id = Column(Integer, ForeignKey('competitions.id'), nullable=False)
    distance_id = Column(Integer, ForeignKey('distances.id'), nullable=True)
    workout_id = Column(Integer, ForeignKey('workouts.id'), nullable=True)
    class_ = Column('class', String, nullable=True)
    position = Column(Integer, nullable=True)         # rank within class
    position_in_distance = Column(Integer, nullable=True)  # rank within distance
    position_overall = Column(Integer, nullable=True)  # rank across all classes
    time_total = Column(Integer, nullable=True)
    time_behind_leader = Column(Integer, nullable=True)          # vs class leader
    time_behind_distance_leader = Column(Integer, nullable=True) # vs distance leader
    status = Column(Enum(ResultStatus), nullable=False, default=ResultStatus.OK)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('user_id', 'competition_id', name='result_unique'),
    )

    # Relationships
    user = relationship('User')
    competition = relationship('Competition', back_populates='results')
    distance = relationship('Distance', back_populates='results')
    workout = relationship('Workout')
    splits = relationship('ResultSplit', back_populates='result', cascade='all, delete-orphan')
