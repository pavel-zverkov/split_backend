from datetime import date

from sqlalchemy.orm import Session

from ..enums.competition_status import CompetitionStatus
from ..enums.event_role import EventRole
from .competition_model import Competition
from .competition_team_model import CompetitionTeam
from .competition_schema import CompetitionCreate, CompetitionUpdate


def get_competition(db: Session, competition_id: int) -> Competition | None:
    return db.query(Competition).filter(Competition.id == competition_id).first()


def get_competition_by_name(
    db: Session,
    name: str,
    date: date,
    sport_kind: str
) -> Competition | None:
    return db.query(Competition).filter(
        Competition.name == name,
        Competition.sport_kind == sport_kind,
        Competition.date == date
    ).first()


def create_competition(
    db: Session,
    event_id: int,
    data: CompetitionCreate,
    sport_kind=None
) -> Competition:
    competition = Competition(
        event_id=event_id,
        name=data.name,
        description=data.description,
        date=data.date,
        sport_kind=data.sport_kind or sport_kind,
        start_format=data.start_format,
        location=data.location,
        status=CompetitionStatus.PLANNED,
    )
    db.add(competition)
    db.commit()
    db.refresh(competition)
    return competition


def update_competition(db: Session, competition: Competition, data: CompetitionUpdate) -> Competition:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(competition, field, value)
    db.commit()
    db.refresh(competition)
    return competition


def delete_competition(db: Session, competition: Competition) -> None:
    db.delete(competition)
    db.commit()


def get_competitions_by_event(
    db: Session,
    event_id: int,
    status: CompetitionStatus | None = None,
    competition_date: date | None = None,
    limit: int = 20,
    offset: int = 0
) -> tuple[list[Competition], int]:
    q = db.query(Competition).filter(Competition.event_id == event_id)

    if status:
        q = q.filter(Competition.status == status)
    if competition_date:
        q = q.filter(Competition.date == competition_date)

    total = q.count()
    competitions = q.order_by(Competition.date.asc()).offset(offset).limit(limit).all()
    return competitions, total


def get_registrations_count(db: Session, competition_id: int) -> int:
    from .competition_registration_model import CompetitionRegistration
    return db.query(CompetitionRegistration).filter(
        CompetitionRegistration.competition_id == competition_id
    ).count()


def get_results_count(db: Session, competition_id: int) -> int:
    from ..result.result_model import Result
    return db.query(Result).filter(Result.competition_id == competition_id).count()


# Status transition rules
VALID_STATUS_TRANSITIONS = {
    CompetitionStatus.PLANNED: [CompetitionStatus.REGISTRATION_OPEN, CompetitionStatus.CANCELLED],
    CompetitionStatus.REGISTRATION_OPEN: [CompetitionStatus.REGISTRATION_CLOSED, CompetitionStatus.IN_PROGRESS, CompetitionStatus.CANCELLED],
    CompetitionStatus.REGISTRATION_CLOSED: [CompetitionStatus.REGISTRATION_OPEN, CompetitionStatus.IN_PROGRESS, CompetitionStatus.CANCELLED],
    CompetitionStatus.IN_PROGRESS: [CompetitionStatus.FINISHED, CompetitionStatus.CANCELLED],
    CompetitionStatus.FINISHED: [],
    CompetitionStatus.CANCELLED: [],
}


def is_valid_status_transition(current: CompetitionStatus, new: CompetitionStatus) -> bool:
    if current == new:
        return True
    return new in VALID_STATUS_TRANSITIONS.get(current, [])


def validate_competition_for_in_progress(db: Session, competition: Competition) -> str | None:
    """Validate competition can transition to IN_PROGRESS. Returns error message or None."""
    from datetime import date as date_type
    from ..enums.start_format import StartFormat
    from .competition_registration_model import CompetitionRegistration
    from ..enums.registration_status import RegistrationStatus

    today = date_type.today()
    if today < competition.date:
        return f'Cannot start competition before its date ({competition.date})'

    # For separated_start: check that all registered athletes have bib_number and start_time
    if competition.start_format == StartFormat.SEPARATED_START:
        not_ready = db.query(CompetitionRegistration).filter(
            CompetitionRegistration.competition_id == competition.id,
            CompetitionRegistration.status.in_([
                RegistrationStatus.REGISTERED,
                RegistrationStatus.CONFIRMED,
            ]),
            (CompetitionRegistration.bib_number.is_(None)) | (CompetitionRegistration.start_time.is_(None))
        ).count()

        if not_ready > 0:
            return f'Start list is not ready: {not_ready} registration(s) missing bib number or start time'

    # For mass_start: check that all registered athletes have bib_number
    elif competition.start_format == StartFormat.MASS_START:
        not_ready = db.query(CompetitionRegistration).filter(
            CompetitionRegistration.competition_id == competition.id,
            CompetitionRegistration.status.in_([
                RegistrationStatus.REGISTERED,
                RegistrationStatus.CONFIRMED,
            ]),
            CompetitionRegistration.bib_number.is_(None)
        ).count()

        if not_ready > 0:
            return f'Start list is not ready: {not_ready} registration(s) missing bib number'

    return None


def validate_competition_for_finished(db: Session, competition: Competition) -> str | None:
    """Validate competition can transition to FINISHED. Returns error message or None."""
    from datetime import date as date_type
    from .competition_registration_model import CompetitionRegistration
    from ..result.result_model import Result
    from ..enums.registration_status import RegistrationStatus

    today = date_type.today()
    if today <= competition.date:
        return f'Cannot finish competition on or before its date ({competition.date})'

    # Check that all registered athletes have results
    registered_count = db.query(CompetitionRegistration).filter(
        CompetitionRegistration.competition_id == competition.id,
        CompetitionRegistration.status.in_([
            RegistrationStatus.REGISTERED,
            RegistrationStatus.CONFIRMED,
        ]),
    ).count()

    results_count = db.query(Result).filter(
        Result.competition_id == competition.id,
    ).count()

    if results_count < registered_count:
        missing = registered_count - results_count
        return f'Cannot finish competition: {missing} registered athlete(s) have no results'

    return None


# Team functions
def get_competition_team(
    db: Session,
    competition_id: int,
    role: EventRole | None = None,
    limit: int = 20,
    offset: int = 0
) -> tuple[list, int]:
    """Get competition team members (inherited + assigned)."""
    from ..event.event_crud import get_team_members, TEAM_ROLES
    from ..event.event_participation_model import EventParticipation

    competition = get_competition(db, competition_id)
    if not competition:
        return [], 0

    # Get event team members
    event_members, _ = get_team_members(db, competition.event_id, role=role, limit=1000, offset=0)

    # Get competition-specific assignments
    comp_assignments = db.query(CompetitionTeam).filter(
        CompetitionTeam.competition_id == competition_id
    ).all()

    assignment_map = {a.user_id: a for a in comp_assignments}

    team = []
    for member in event_members:
        user_id = member.user_id

        # Check if excluded
        if user_id in assignment_map and assignment_map[user_id].excluded:
            continue

        # Check if has specific assignment
        if user_id in assignment_map:
            assignment = assignment_map[user_id]
            team.append({
                'user': member.user,
                'role': assignment.role,
                'position': member.position,
                'inherited': False,
            })
        else:
            # Inherited from event
            team.append({
                'user': member.user,
                'role': member.role,
                'position': member.position,
                'inherited': True,
            })

    total = len(team)
    return team[offset:offset + limit], total


def assign_team_member(
    db: Session,
    competition_id: int,
    user_id: int,
    role: EventRole
) -> CompetitionTeam:
    """Assign a team member to a competition."""
    # Check if already assigned
    existing = db.query(CompetitionTeam).filter(
        CompetitionTeam.competition_id == competition_id,
        CompetitionTeam.user_id == user_id
    ).first()

    if existing:
        existing.role = role
        existing.excluded = False
        db.commit()
        db.refresh(existing)
        return existing

    assignment = CompetitionTeam(
        competition_id=competition_id,
        user_id=user_id,
        role=role,
        excluded=False,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def remove_from_competition_team(db: Session, competition_id: int, user_id: int) -> bool:
    """Remove or exclude a team member from competition."""
    assignment = db.query(CompetitionTeam).filter(
        CompetitionTeam.competition_id == competition_id,
        CompetitionTeam.user_id == user_id
    ).first()

    if assignment:
        # Specific assignment - delete it
        db.delete(assignment)
        db.commit()
        return True

    # No specific assignment - create exclusion
    exclusion = CompetitionTeam(
        competition_id=competition_id,
        user_id=user_id,
        role=EventRole.VOLUNTEER,  # Placeholder, doesn't matter when excluded
        excluded=True,
    )
    db.add(exclusion)
    db.commit()
    return True


def is_event_team_member(db: Session, user_id: int, event_id: int) -> bool:
    """Check if user is an event team member."""
    from ..event.event_crud import is_team_member
    return is_team_member(db, user_id, event_id)


def can_manage_competition(db: Session, user_id: int, event_id: int) -> bool:
    """Check if user can create/update/delete competitions (chief of organizer, secretary, or judge)."""
    from ..event.event_crud import get_participation
    from ..enums.event_position import EventPosition

    participation = get_participation(db, user_id, event_id)
    if not participation:
        return False

    # Must be chief of organizer, secretary, or judge
    if participation.position != EventPosition.CHIEF:
        return False

    return participation.role in [EventRole.ORGANIZER, EventRole.SECRETARY, EventRole.JUDGE]


def can_delete_competition(db: Session, user_id: int, event_id: int) -> bool:
    """Check if user can delete competitions (chief of organizer or secretary only)."""
    from ..event.event_crud import get_participation
    from ..enums.event_position import EventPosition

    participation = get_participation(db, user_id, event_id)
    if not participation:
        return False

    if participation.position != EventPosition.CHIEF:
        return False

    return participation.role in [EventRole.ORGANIZER, EventRole.SECRETARY]
