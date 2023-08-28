
from sqlalchemy import (Column,
                        Enum,
                        Integer,
                        String)

from ..database import Base
from ..enums.enum_status import Status


class Event(Base):
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    status = Column(Enum(Status), default=Status.PLANNED)
