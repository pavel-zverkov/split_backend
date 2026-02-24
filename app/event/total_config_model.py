from sqlalchemy import (Boolean,
                        Column,
                        DateTime,
                        ForeignKey,
                        Integer,
                        String,
                        func)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from ..database import Base


class EventTotalConfig(Base):
    __tablename__ = 'event_total_configs'

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(
        Integer,
        ForeignKey('events.id', ondelete='CASCADE'),
        nullable=False
    )
    name = Column(String, nullable=False)
    rules = Column(JSONB, nullable=False)
    auto_calculate = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    event = relationship('Event')
    results = relationship('EventTotalResult', back_populates='config', cascade='all, delete-orphan')
