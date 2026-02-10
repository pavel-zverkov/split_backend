from sqlalchemy import (Boolean,
                        Column,
                        Date,
                        DateTime,
                        Enum,
                        ForeignKey,
                        Integer,
                        String,
                        func)
from sqlalchemy.orm import relationship

from ..database import Base
from ..enums.qualification_type import QualificationType
from ..enums.sport_kind import SportKind


class UserQualification(Base):
    __tablename__ = 'user_qualifications'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    type = Column(Enum(QualificationType), nullable=False)
    sport_kind = Column(Enum(SportKind), nullable=False)
    rank = Column(String, nullable=False)
    issued_date = Column(Date, nullable=True)
    valid_until = Column(Date, nullable=True)
    document_number = Column(String, nullable=True)
    confirmed = Column(Boolean, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    user = relationship('User')
