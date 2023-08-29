from sqlalchemy.orm import Session

from .user_orm_model import User as ORMUser
from .user_pydantic_model import UserCreate


def get_user(db: Session, mobile_number: str) -> None:
    return db.query(ORMUser).filter(ORMUser.mobile_number == mobile_number).first()


def create_user(
    db: Session,
    user: UserCreate
) -> None:

    db_user = ORMUser(**user.model_dump())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# TODO: update_user, delete_user
