from datetime import date

from sqlalchemy.orm import Session

from .user_orm_model import User
from .user_pydantic_model import UserCreate

# def get_user(db: Session, mobile_number: str) -> None:
#     return db.query(User).filter(User.mobile_number == mobile_number).first()


def get_user(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_name(
    db: Session,
    first_name: str,
    last_name: str | None,
    birthdate: date | None
) -> User | None:
    return db.query(User)\
             .filter(
                 User.first_name == first_name,
                 User.last_name == last_name,
                 User.birthdate == birthdate)\
             .first()


def create_user(
    db: Session,
    user: UserCreate
) -> User:

    db_user = User(**user.model_dump())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# TODO: update_user, delete_user
