from pydantic import BaseModel

from ..enums.enum_user_competition_role import UserCompetitionRole as Role


class UserEventRole(BaseModel):

    id: int
    role: Role
