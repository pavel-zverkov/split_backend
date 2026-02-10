from sqlalchemy import (Column,
                        DateTime,
                        Enum,
                        ForeignKey,
                        Integer,
                        String,
                        Text,
                        func)
from sqlalchemy.orm import relationship

from ..database import Base
from ..enums.privacy import Privacy


class Club(Base):
    __tablename__ = 'clubs'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    logo = Column(String, nullable=True)
    location = Column(String, nullable=True)
    privacy = Column(Enum(Privacy), nullable=False, default=Privacy.PUBLIC)
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    owner = relationship('User', foreign_keys=[owner_id])
    memberships = relationship('ClubMembership', back_populates='club', cascade='all, delete-orphan')
