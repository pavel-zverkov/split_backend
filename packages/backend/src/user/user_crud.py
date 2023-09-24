from datetime import date

from sqlalchemy.orm import Session

from .user_orm_model import User as ORMUser
from .user_pydantic_model import User as PyUser
from .user_pydantic_model import UserCreate

# def get_user(db: Session, mobile_number: str) -> None:
#     return db.query(ORMUser).filter(ORMUser.mobile_number == mobile_number).first()

def get_user(db: Session, user_id: int) -> ORMUser:
    return db.query(ORMUser).filter(ORMUser.id == user_id).first()


def get_user_by_name(
    db: Session,
    first_name: str,
    last_name: str,
    birthdate: date
) -> PyUser | None:
    return db.query(ORMUser)\
             .filter(
                 ORMUser.first_name == first_name,
                 ORMUser.last_name == last_name,
                 ORMUser.birthdate == birthdate)\
             .first()


def create_user(
    db: Session,
    user: UserCreate
) -> PyUser:

    db_user = ORMUser(**user.model_dump())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# TODO: update_user, delete_user
