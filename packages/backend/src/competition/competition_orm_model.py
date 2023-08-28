from sqlalchemy import (Column,
                        Enum,
                        Integer,
                        String)

from ..database import Base
from ..enums.enum_sport_kind import SportKind
from ..enums.enum_status import Status


class Competition(Base):
    __tablename__ = 'competitions'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    kind = Column(Enum(SportKind))
    status = Column(Enum(Status), default=Status.PLANNED)
