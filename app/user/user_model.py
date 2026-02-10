from sqlalchemy import (Boolean,
                        Column,
                        Date,
                        DateTime,
                        Enum,
                        ForeignKey,
                        Integer,
                        String,
                        Text,
                        UniqueConstraint,
                        func)
from sqlalchemy.orm import relationship

from ..database import Base
from ..enums.gender import Gender
from ..enums.account_type import AccountType
from ..enums.privacy import Privacy


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    username_display = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=True)
    password_hash = Column(String, nullable=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=True)
    birthday = Column(Date, nullable=True)
    gender = Column(Enum(Gender), nullable=True)
    logo = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    privacy_default = Column(Enum(Privacy), default=Privacy.PRIVATE)
    account_type = Column(Enum(AccountType), nullable=False, default=AccountType.REGISTERED)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('first_name', 'last_name', 'birthday',
                         name='user_unique_constraint'),
    )

    # Relationships
    workouts = relationship('Workout', back_populates='owner', foreign_keys='Workout.user_id')
    creator = relationship('User', remote_side=[id], foreign_keys=[created_by])
