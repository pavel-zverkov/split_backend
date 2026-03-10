from sqlalchemy import (Column,
                        Enum,
                        ForeignKey,
                        Integer,
                        String,
                        UniqueConstraint)
from sqlalchemy.orm import relationship

from ..database import Base
from ..enums.control_point_type import ControlPointType


class ControlPoint(Base):
    __tablename__ = 'control_points'

    id = Column(Integer, primary_key=True, index=True)
    distance_id = Column(
        Integer,
        ForeignKey('distances.id', ondelete='CASCADE'),
        nullable=False
    )
    code = Column(String, nullable=False)
    sequence = Column(Integer, nullable=False)
    type = Column(Enum(ControlPointType), nullable=False, default=ControlPointType.CONTROL)

    __table_args__ = (
        UniqueConstraint('distance_id', 'sequence', name='cp_sequence_unique'),
        UniqueConstraint('distance_id', 'code', name='cp_code_unique'),
    )

    # Relationships
    distance = relationship('Distance', back_populates='control_points')
