from datetime import datetime

from sqlalchemy.orm import Session

from ..enums.enum_sport_kind import SportKind
from .user_competition_relation_orm import UserCompetitionRelation


def get_user_competition_relation(db: Session, uc_r_id: int) -> None:
    return db.query(UserCompetitionRelation)\
             .filter(UserCompetitionRelation.id == uc_r_id)\
             .first()


def create_user_competition_relation(
    db: Session,
    user_id: int,
    competition_id: int,
    role_id: int
) -> None:

    db_user_competition_relation = UserCompetitionRelation(
        user=user_id,
        competition=competition_id,
        role=role_id,
    )
    db.add(db_user_competition_relation)
    db.commit()
    db.refresh(db_user_competition_relation)
    return db_user_competition_relation

# TODO: update_user_competition_relation, delete
