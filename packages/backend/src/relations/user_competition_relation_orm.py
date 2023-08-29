from sqlalchemy import (Column,
                        ForeignKey,
                        Integer)

from ..database import Base


class UserCompetitionRelation(Base):
    __tablename__ = 'users_competitions'

    id = Column(Integer, primary_key=True, index=True)
    user = Column(Integer, ForeignKey('users.id'))
    competition = Column(Integer, ForeignKey('competitions.id'))
    role = Column(Integer, ForeignKey(
        'user_competition_roles.id'), nullable=True)
