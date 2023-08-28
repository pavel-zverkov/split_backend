from sqlalchemy import (Boolean,
                        Column,
                        Date,
                        Enum,
                        Integer,
                        String)
from sqlalchemy.orm import relationship

from ..database import Base
from ..enums.enum_gender import Gender
from ..enums.enum_qualify import Qualify


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    mobile_number = Column(String, unique=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=True)
    birthdate = Column(Date, nullable=True)
    gender = Column(Enum(Gender), nullable=True)
    qualify = Column(Enum(Qualify), nullable=True)
    is_active = Column(Boolean, default=True)

    workouts = relationship('Workout', back_populates='user')
