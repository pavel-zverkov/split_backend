from sqlalchemy import (JSON,
                        Column,
                        Date,
                        Enum,
                        ForeignKey,
                        Integer,
                        String,
                        UniqueConstraint)
from sqlalchemy.orm import relationship

from ..database import Base
from ..enums.enum_sport_kind import SportKind


class Workout(Base):
    __tablename__ = 'workouts'

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    sport_kind = Column(Enum(SportKind))
    user = Column(Integer, ForeignKey('users.id'), nullable=False)
    competition = Column(
        Integer,
        ForeignKey(
            'competitions.id',
            ondelete='SET NULL',
            onupdate='CASCADE'
        ),
        nullable=True
    )
    fit_file = Column(String, nullable=True)
    gpx_file = Column(String, nullable=True)
    tcx_file = Column(String, nullable=True)
    splits = Column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            'date',
            'sport_kind',
            'user',
            'competition',
            name='workout_unique_constraint'
        ),
    )

    owner = relationship('User', back_populates='workouts')
