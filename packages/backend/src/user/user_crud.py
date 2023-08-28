from datetime import datetime
from ..enums.enum_gender import Gender
from ..enums.enum_qualify import Qualify

from sqlalchemy.orm import Session

from .user_orm_model import User


def get_user(db: Session, user_id: int) -> None:
    return db.query(User).filter(User.id == user_id).first()


def create_user(
    db: Session,
    mobile_number: str,
    first_name: str,
    last_name: str | None = None,
    birthdate: datetime | None = None,
    gender: Gender | None = None,
    qualify: Qualify | None = None,
    is_active: bool = True
) -> None:

    db_user = User(
        mobile_number=mobile_number,
        first_name=first_name,
        last_name=last_name,
        birthdate=birthdate,
        gender=gender,
        qualify=qualify,
        is_active=is_active,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# TODO: update_user, delete_user
