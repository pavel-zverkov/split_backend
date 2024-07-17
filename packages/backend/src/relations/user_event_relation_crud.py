from sqlalchemy.orm import Session

from .user_event_relation_orm import UserEventRelation


def get_user_event_relation(db: Session, ue_r_id: int) -> UserEventRelation | None:
    return db.query(UserEventRelation)\
             .filter(UserEventRelation.id == ue_r_id)\
             .first()


def create_user_event_relation(
    db: Session,
    user_id: int,
    event_id: int,
    role_id: int
) -> UserEventRelation:

    db_user_event_relation = UserEventRelation(
        user=user_id,
        event=event_id,
        role=role_id,
    )
    db.add(db_user_event_relation)
    db.commit()
    db.refresh(db_user_event_relation)
    return db_user_event_relation

# TODO: update_user_event_relation, delete
