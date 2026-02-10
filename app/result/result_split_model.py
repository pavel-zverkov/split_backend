from sqlalchemy import (Column,
                        ForeignKey,
                        Integer,
                        String,
                        UniqueConstraint)
from sqlalchemy.orm import relationship

from ..database import Base


class ResultSplit(Base):
    __tablename__ = 'result_splits'

    id = Column(Integer, primary_key=True, index=True)
    result_id = Column(Integer, ForeignKey('results.id'), nullable=False)
    control_point = Column(String, nullable=False)
    sequence = Column(Integer, nullable=False)
    cumulative_time = Column(Integer, nullable=False)
    split_time = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint('result_id', 'sequence', name='result_split_unique'),
    )

    # Relationships
    result = relationship('Result', back_populates='splits')
