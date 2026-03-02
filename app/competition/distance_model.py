from sqlalchemy import (ARRAY,
                        Column,
                        DateTime,
                        ForeignKey,
                        Integer,
                        String,
                        func)
from sqlalchemy.orm import relationship

from ..database import Base


class Distance(Base):
    __tablename__ = 'distances'

    id = Column(Integer, primary_key=True, index=True)
    competition_id = Column(
        Integer,
        ForeignKey('competitions.id', ondelete='CASCADE'),
        nullable=False
    )
    name = Column(String, nullable=False)
    distance_meters = Column(Integer, nullable=True)
    climb_meters = Column(Integer, nullable=True)
    control_time = Column(Integer, nullable=True)  # seconds
    classes = Column(ARRAY(String), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    competition = relationship('Competition', back_populates='distances')
    control_points = relationship(
        'ControlPoint',
        back_populates='distance',
        cascade='all, delete-orphan',
        order_by='ControlPoint.sequence'
    )
    results = relationship('Result', back_populates='distance')
