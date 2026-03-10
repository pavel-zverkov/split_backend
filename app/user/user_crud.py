from datetime import date
import secrets
import string

from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from .user_model import User
from .user_follow_model import UserFollow
from .user_schema import UserUpdate, GhostUserCreate
from ..enums.account_type import AccountType
from ..enums.follow_status import FollowStatus


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


# Alias for backwards compatibility
get_user = get_user_by_id


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def get_user_by_name(
    db: Session,
    first_name: str,
    last_name: str | None,
    birthday: date | None
) -> User | None:
    return db.query(User).filter(
        User.first_name == first_name,
        User.last_name == last_name,
        User.birthday == birthday
    ).first()


def search_users(
    db: Session,
    query: str | None = None,
    account_type: AccountType | None = None,
    limit: int = 20,
    offset: int = 0
) -> tuple[list[User], int]:
    q = db.query(User).filter(User.is_active == True)

    if account_type:
        q = q.filter(User.account_type == account_type)

    if query:
        # Combine exact substring match (ILIKE) with fuzzy trigram search
        # word_similarity matches against words within compound strings like 'pavel_zverkov'
        search_pattern = f'%{query}%'
        similarity_threshold = 0.2
        q = q.filter(
            or_(
                # Exact substring matches
                User.username.ilike(search_pattern),
                User.username_display.ilike(search_pattern),
                User.first_name.ilike(search_pattern),
                User.last_name.ilike(search_pattern),
                # Fuzzy matches (handles typos like 'pvael' -> 'pavel')
                func.word_similarity(query, User.username) >= similarity_threshold,
                func.word_similarity(query, User.username_display) >= similarity_threshold,
                func.word_similarity(query, User.first_name) >= similarity_threshold,
                func.word_similarity(query, User.last_name) >= similarity_threshold,
            )
        ).order_by(
            # Order by best match first
            func.greatest(
                func.word_similarity(query, User.username),
                func.word_similarity(query, User.username_display),
                func.word_similarity(query, User.first_name),
                func.coalesce(func.word_similarity(query, User.last_name), 0),
            ).desc()
        )

    total = q.count()
    users = q.offset(offset).limit(limit).all()

    return users, total


def update_user(db: Session, user: User, data: UserUpdate) -> User:
    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


def generate_unique_username(db: Session, first_name: str, last_name: str | None) -> tuple[str, str]:
    base_username = first_name.lower()
    if last_name:
        base_username = f"{first_name.lower()}_{last_name.lower()}"

    # Clean username
    base_username = ''.join(c if c.isalnum() or c == '_' else '' for c in base_username)

    # Check if base username exists
    existing = get_user_by_username(db, base_username)
    if not existing:
        return base_username, base_username

    # Generate unique suffix
    suffix = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(4))
    unique_username = f"{base_username}_{suffix}"

    return unique_username, base_username


def create_ghost_user(
    db: Session,
    data: GhostUserCreate,
    created_by_id: int
) -> User:
    username, username_display = generate_unique_username(db, data.first_name, data.last_name)

    user = User(
        username=username,
        username_display=username_display,
        first_name=data.first_name,
        last_name=data.last_name,
        birthday=data.birthday,
        gender=data.gender,
        account_type=AccountType.GHOST,
        created_by=created_by_id,
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def find_matching_ghosts(
    db: Session,
    first_name: str,
    last_name: str | None,
    birthday: date | None
) -> list[User]:
    q = db.query(User).filter(
        User.account_type == AccountType.GHOST,
        User.is_active == True,
        User.first_name.ilike(first_name),
    )

    if last_name:
        q = q.filter(User.last_name.ilike(last_name))

    # If birthday provided, match it OR allow null birthday ghosts
    if birthday:
        q = q.filter(or_(User.birthday == birthday, User.birthday.is_(None)))

    return q.all()


def get_follow_status(db: Session, follower_id: int, following_id: int) -> FollowStatus | None:
    follow = db.query(UserFollow).filter(
        UserFollow.follower_id == follower_id,
        UserFollow.following_id == following_id
    ).first()

    if not follow:
        return None

    # Mask rejected as pending for privacy
    if follow.status == FollowStatus.REJECTED:
        return FollowStatus.PENDING

    return follow.status


def get_followers_count(db: Session, user_id: int) -> int:
    return db.query(UserFollow).filter(
        UserFollow.following_id == user_id,
        UserFollow.status == FollowStatus.ACCEPTED
    ).count()


def get_following_count(db: Session, user_id: int) -> int:
    return db.query(UserFollow).filter(
        UserFollow.follower_id == user_id,
        UserFollow.status == FollowStatus.ACCEPTED
    ).count()


def get_workouts_count(db: Session, user_id: int) -> int:
    from ..workout.workout_model import Workout
    return db.query(Workout).filter(Workout.user_id == user_id).count()


def soft_delete_user(db: Session, user: User) -> None:
    user.is_active = False
    user.password_hash = None
    db.commit()


def hard_delete_user(db: Session, user: User) -> None:
    user.is_active = False
    user.password_hash = None
    user.email = None
    user.logo = None
    db.commit()


def delete_user_follows(db: Session, user_id: int) -> None:
    db.query(UserFollow).filter(
        or_(
            UserFollow.follower_id == user_id,
            UserFollow.following_id == user_id
        )
    ).delete()
    db.commit()


def delete_user_club_memberships(db: Session, user_id: int) -> None:
    from ..club.club_membership_model import ClubMembership
    db.query(ClubMembership).filter(ClubMembership.user_id == user_id).delete()
    db.commit()


def delete_pending_claim_requests(db: Session, user_id: int) -> None:
    from .claim_request_model import ClaimRequest
    from ..enums.claim_status import ClaimStatus
    db.query(ClaimRequest).filter(
        ClaimRequest.claimer_id == user_id,
        ClaimRequest.status == ClaimStatus.PENDING
    ).delete()
    db.commit()


def user_owns_clubs(db: Session, user_id: int) -> bool:
    from ..club.club_model import Club
    return db.query(Club).filter(Club.owner_id == user_id).count() > 0


def user_organizes_active_events(db: Session, user_id: int) -> bool:
    from ..event.event_model import Event
    from ..enums.event_status import EventStatus
    active_statuses = [EventStatus.DRAFT, EventStatus.PLANNED, EventStatus.IN_PROGRESS]
    return db.query(Event).filter(
        Event.organizer_id == user_id,
        Event.status.in_(active_statuses)
    ).count() > 0


def can_create_ghost_users(db: Session, user_id: int) -> bool:
    from ..club.club_model import Club
    from ..club.club_membership_model import ClubMembership
    from ..event.event_participation_model import EventParticipation
    from ..enums.club_role import ClubRole
    from ..enums.event_role import EventRole

    # Check if user owns a club
    owns_club = db.query(Club).filter(Club.owner_id == user_id).count() > 0
    if owns_club:
        return True

    # Check if user is admin or coach in a club
    is_club_staff = db.query(ClubMembership).filter(
        ClubMembership.user_id == user_id,
        ClubMembership.role.in_([ClubRole.COACH])
    ).count() > 0
    if is_club_staff:
        return True

    # Check if user is organizer of any event
    is_organizer = db.query(EventParticipation).filter(
        EventParticipation.user_id == user_id,
        EventParticipation.role == EventRole.ORGANIZER
    ).count() > 0

    return is_organizer


def get_user_competitions_count(db: Session, user_id: int) -> int:
    """Count competitions user has registered for."""
    from ..competition.competition_registration_model import CompetitionRegistration
    return db.query(CompetitionRegistration).filter(
        CompetitionRegistration.user_id == user_id
    ).count()


def get_user_results_summary(db: Session, user_id: int) -> str | None:
    """Get a brief summary of user's best results."""
    from ..result.result_model import Result
    from ..enums.result_status import ResultStatus

    results = db.query(Result).filter(
        Result.user_id == user_id,
        Result.status == ResultStatus.OK,
        Result.position.isnot(None)
    ).order_by(Result.position.asc()).limit(3).all()

    if not results:
        return None

    best = results[0]
    if best.position == 1:
        return f"Best: 1st place ({len(results)} results)"
    elif best.position == 2:
        return f"Best: 2nd place ({len(results)} results)"
    elif best.position == 3:
        return f"Best: 3rd place ({len(results)} results)"
    else:
        return f"Best: {best.position}th place ({len(results)} results)"


def get_ghost_events(db: Session, ghost_user_id: int) -> list[dict]:
    """Get events where the ghost user has competition registrations, grouped by event."""
    from ..competition.competition_registration_model import CompetitionRegistration
    from ..competition.competition_model import Competition
    from ..event.event_model import Event
    from ..result.result_model import Result

    registrations = db.query(CompetitionRegistration).filter(
        CompetitionRegistration.user_id == ghost_user_id
    ).all()

    events_map: dict[int, dict] = {}
    for reg in registrations:
        comp = db.query(Competition).filter(Competition.id == reg.competition_id).first()
        if not comp:
            continue
        event = db.query(Event).filter(Event.id == comp.event_id).first()
        if not event:
            continue

        has_result = db.query(Result).filter(
            Result.user_id == ghost_user_id,
            Result.competition_id == comp.id
        ).count() > 0

        if event.id not in events_map:
            events_map[event.id] = {
                'event_id': event.id,
                'event_name': event.name,
                'competitions': [],
            }

        events_map[event.id]['competitions'].append({
            'competition_id': comp.id,
            'competition_name': comp.name,
            'has_result': has_result,
        })

    return list(events_map.values())


def get_ghost_clubs(db: Session, ghost_user_id: int) -> list[dict]:
    """Get clubs where the ghost user is a member."""
    from ..club.club_membership_model import ClubMembership
    from ..club.club_model import Club

    memberships = db.query(ClubMembership).filter(
        ClubMembership.user_id == ghost_user_id
    ).all()

    clubs = []
    for m in memberships:
        club = db.query(Club).filter(Club.id == m.club_id).first()
        if club:
            clubs.append({
                'club_id': club.id,
                'club_name': club.name,
            })

    return clubs
