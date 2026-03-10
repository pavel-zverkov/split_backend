from sqlalchemy import (Column,
                        DateTime,
                        Enum,
                        Float,
                        ForeignKey,
                        Integer,
                        String,
                        UniqueConstraint,
                        func)
from sqlalchemy.orm import relationship

from ..database import Base
from ..enums.total_result_status import TotalResultStatus


class EventTotalResult(Base):
    __tablename__ = 'event_total_results'

    id = Column(Integer, primary_key=True, index=True)
    config_id = Column(
        Integer,
        ForeignKey('event_total_configs.id', ondelete='CASCADE'),
        nullable=False
    )
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    class_ = Column('class', String, nullable=True)
    total_value = Column(Float, nullable=True)
    position = Column(Integer, nullable=True)
    position_overall = Column(Integer, nullable=True)
    stages_counted = Column(Integer, nullable=False, default=0)
    stages_total = Column(Integer, nullable=False, default=0)
    status = Column(Enum(TotalResultStatus), nullable=False, default=TotalResultStatus.OK)
    calculated_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('config_id', 'user_id', 'class', name='total_result_unique'),
    )

    # Relationships
    config = relationship('EventTotalConfig', back_populates='results')
    user = relationship('User')
