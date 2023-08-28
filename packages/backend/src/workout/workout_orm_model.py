
from sqlalchemy import (JSON,
                        Column,
                        Date,
                        ForeignKey,
                        Integer,
                        String)
from sqlalchemy.orm import relationship

from ..database import Base


class Workout(Base):
    __tablename__ = 'workouts'

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date)
    user = Column(Integer, ForeignKey('users.id'))
    event = Column(Integer, ForeignKey('events.id'), nullable=True)
    fit_file = Column(String, nullable=True)
    gpx_file = Column(String, nullable=True)
    tcx_file = Column(String, nullable=True)
    splits = Column(JSON, nullable=True)

    owner = relationship('User')
