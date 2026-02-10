from sqlalchemy.orm import Session

from .user_qualification_model import UserQualification
from .qualification_schema import QualificationCreate, QualificationUpdate
from ..enums.qualification_type import QualificationType
from ..enums.sport_kind import SportKind


def get_qualification_by_id(db: Session, qualification_id: int) -> UserQualification | None:
    return db.query(UserQualification).filter(
        UserQualification.id == qualification_id
    ).first()


def get_user_qualifications(db: Session, user_id: int) -> list[UserQualification]:
    return db.query(UserQualification).filter(
        UserQualification.user_id == user_id
    ).order_by(UserQualification.created_at.desc()).all()


def get_duplicate_qualification(
    db: Session,
    user_id: int,
    type: QualificationType,
    sport_kind: SportKind,
    rank: str,
    exclude_id: int | None = None
) -> UserQualification | None:
    """Check if user already has a qualification with same type, sport_kind, and rank."""
    q = db.query(UserQualification).filter(
        UserQualification.user_id == user_id,
        UserQualification.type == type,
        UserQualification.sport_kind == sport_kind,
        UserQualification.rank == rank
    )
    if exclude_id:
        q = q.filter(UserQualification.id != exclude_id)
    return q.first()


def create_qualification(
    db: Session,
    user_id: int,
    data: QualificationCreate
) -> UserQualification:
    qualification = UserQualification(
        user_id=user_id,
        type=data.type,
        sport_kind=data.sport_kind,
        rank=data.rank,
        issued_date=data.issued_date,
        valid_until=data.valid_until,
        document_number=data.document_number,
        confirmed=None,
    )
    db.add(qualification)
    db.commit()
    db.refresh(qualification)
    return qualification


def update_qualification(
    db: Session,
    qualification: UserQualification,
    data: QualificationUpdate
) -> UserQualification:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(qualification, field, value)
    db.commit()
    db.refresh(qualification)
    return qualification


def delete_qualification(db: Session, qualification: UserQualification) -> None:
    db.delete(qualification)
    db.commit()
