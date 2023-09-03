from sqlalchemy import (Boolean,
                        Column,
                        Date,
                        Enum,
                        Integer,
                        String, UniqueConstraint)
from sqlalchemy.orm import relationship

from ..database import Base
from ..enums.enum_gender import Gender
from ..enums.enum_qualify import Qualify


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    mobile_number = Column(String, unique=True, nullable=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=True)
    birthdate = Column(Date, nullable=True)
    gender = Column(Enum(Gender), nullable=True)
    qualify = Column(Enum(Qualify), nullable=True)
    is_active = Column(Boolean, default=True)
    __table_args__ = (
        UniqueConstraint('first_name', 'last_name', 'birthdate',
                         name='user_unique_constraint'),
    )

    workouts = relationship('Workout', back_populates='owner')
