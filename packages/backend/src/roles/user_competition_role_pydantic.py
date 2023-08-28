from pydantic import BaseModel

from ..enums.enum_user_competition_role import UserCompetitionRole as Role


class UserCompetitionRole(BaseModel):

    id: int
    role: Role
