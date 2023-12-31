
from sqlalchemy import (Column,
                        Enum,
                        Integer)

from ..database import Base
from ..enums.enum_user_competition_role import UserCompetitionRole as Role


class UserCompetitionRole(Base):
    __tablename__ = 'user_competition_roles'

    id = Column(Integer, primary_key=True)
    role = Column(Enum(Role))
