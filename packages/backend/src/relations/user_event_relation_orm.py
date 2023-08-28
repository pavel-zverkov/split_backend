from sqlalchemy import (Column,
                        ForeignKey,
                        Integer)

from ..database import Base


class UserEventRelation(Base):
    __tablename__ = 'users_events'

    id = Column(Integer, primary_key=True, index=True)
    user = Column(Integer, ForeignKey('users.id'))
    event = Column(Integer, ForeignKey('events.id'))
    role = Column(Integer, ForeignKey('user_event_roles.id'))
