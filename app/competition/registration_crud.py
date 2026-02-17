from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..enums.registration_status import RegistrationStatus
from ..enums.competition_status import CompetitionStatus
from ..enums.start_format import StartFormat
from ..enums.event_role import EventRole
from ..enums.participation_status import ParticipationStatus
from .competition_model import Competition
from .competition_registration_model import CompetitionRegistration


def get_registration(db: Session, registration_id: int) -> CompetitionRegistration | None:
    return db.query(CompetitionRegistration).filter(
        CompetitionRegistration.id == registration_id
    ).first()


def get_registration_by_user(
    db: Session,
    user_id: int,
    competition_id: int
) -> CompetitionRegistration | None:
    return db.query(CompetitionRegistration).filter(
        CompetitionRegistration.user_id == user_id,
        CompetitionRegistration.competition_id == competition_id
    ).first()


def create_registration(
    db: Session,
    user_id: int,
    competition_id: int,
    competition_class: str | None = None,
    bib_number: str | None = None,
    start_time: datetime | None = None,
    status: RegistrationStatus = RegistrationStatus.REGISTERED
) -> CompetitionRegistration:
    registration = CompetitionRegistration(
        user_id=user_id,
        competition_id=competition_id,
        class_=competition_class,
        bib_number=bib_number,
        start_time=start_time,
        status=status,
    )
    db.add(registration)
    db.commit()
    db.refresh(registration)
    return registration


def update_registration(
    db: Session,
    registration: CompetitionRegistration,
    bib_number: str | None = None,
    start_time: datetime | None = None,
    status: RegistrationStatus | None = None,
    competition_class: str | None = None
) -> CompetitionRegistration:
    if bib_number is not None:
        registration.bib_number = bib_number
    if start_time is not None:
        registration.start_time = start_time
    if status is not None:
        registration.status = status
    if competition_class is not None:
        registration.class_ = competition_class
    db.commit()
    db.refresh(registration)
    return registration


def delete_registration(db: Session, registration: CompetitionRegistration) -> None:
    db.delete(registration)
    db.commit()


def get_registrations(
    db: Session,
    competition_id: int,
    competition_class: str | None = None,
    status: RegistrationStatus | None = None,
    limit: int = 20,
    offset: int = 0
) -> tuple[list[CompetitionRegistration], int]:
    q = db.query(CompetitionRegistration).filter(
        CompetitionRegistration.competition_id == competition_id
    )

    if competition_class:
        q = q.filter(CompetitionRegistration.class_ == competition_class)
    if status:
        q = q.filter(CompetitionRegistration.status == status)

    total = q.count()
    registrations = q.order_by(CompetitionRegistration.created_at.desc()).offset(offset).limit(limit).all()
    return registrations, total


def get_start_list(
    db: Session,
    competition_id: int,
    competition_class: str | None = None
) -> list[CompetitionRegistration]:
    """Get confirmed registrations for start list."""
    q = db.query(CompetitionRegistration).filter(
        CompetitionRegistration.competition_id == competition_id,
        CompetitionRegistration.status == RegistrationStatus.CONFIRMED
    )

    if competition_class:
        q = q.filter(CompetitionRegistration.class_ == competition_class)

    return q.order_by(CompetitionRegistration.start_time.asc()).all()


def is_bib_number_unique(
    db: Session,
    competition_id: int,
    bib_number: str,
    exclude_registration_id: int | None = None
) -> bool:
    """Check if bib number is unique within competition."""
    q = db.query(CompetitionRegistration).filter(
        CompetitionRegistration.competition_id == competition_id,
        CompetitionRegistration.bib_number == bib_number
    )
    if exclude_registration_id:
        q = q.filter(CompetitionRegistration.id != exclude_registration_id)
    return q.first() is None


def has_result(db: Session, registration_id: int) -> bool:
    """Check if registration has a result."""
    from ..result.result_model import Result
    registration = get_registration(db, registration_id)
    if not registration:
        return False
    return db.query(Result).filter(
        Result.competition_id == registration.competition_id,
        Result.user_id == registration.user_id
    ).first() is not None


def can_register(db: Session, competition: Competition, is_team_member: bool = False) -> bool:
    """Check if registration is allowed for competition.
    When registration is closed, only team members can register athletes.
    """
    if competition.status == CompetitionStatus.REGISTRATION_OPEN:
        return True
    if competition.status == CompetitionStatus.REGISTRATION_CLOSED:
        return is_team_member
    if competition.status == CompetitionStatus.IN_PROGRESS:
        return competition.start_format == StartFormat.FREE
    return False


def can_cancel_registration(db: Session, competition: Competition, is_team_member: bool = False) -> bool:
    """Check if user can cancel their own registration.
    When registration is closed, only team members can cancel.
    """
    if competition.status == CompetitionStatus.REGISTRATION_OPEN:
        return True
    if competition.status == CompetitionStatus.REGISTRATION_CLOSED:
        return is_team_member
    if competition.status == CompetitionStatus.IN_PROGRESS:
        return competition.start_format == StartFormat.FREE
    return False


def has_approved_event_participation(db: Session, user_id: int, event_id: int) -> bool:
    """Check if user has approved participation as participant in the event."""
    from ..event.event_participation_model import EventParticipation

    participation = db.query(EventParticipation).filter(
        EventParticipation.user_id == user_id,
        EventParticipation.event_id == event_id,
        EventParticipation.role == EventRole.PARTICIPANT,
        EventParticipation.status == ParticipationStatus.APPROVED
    ).first()

    return participation is not None


def can_manage_registrations(db: Session, user_id: int, event_id: int) -> bool:
    """Check if user can manage registrations (organizer or secretary)."""
    from ..event.event_crud import get_participation

    participation = get_participation(db, user_id, event_id)
    if not participation or participation.status != ParticipationStatus.APPROVED:
        return False

    return participation.role in [EventRole.ORGANIZER, EventRole.SECRETARY]


def get_class_summaries(db: Session, competition_id: int) -> list[dict]:
    """Get class summaries for start list."""
    from sqlalchemy import func

    registrations = db.query(
        CompetitionRegistration.class_,
        func.count(CompetitionRegistration.id).label('count'),
        func.min(CompetitionRegistration.start_time).label('first_start')
    ).filter(
        CompetitionRegistration.competition_id == competition_id,
        CompetitionRegistration.status == RegistrationStatus.CONFIRMED
    ).group_by(
        CompetitionRegistration.class_
    ).all()

    return [
        {
            'class': r[0],
            'count': r[1],
            'first_start': r[2]
        }
        for r in registrations
    ]
