from sqlalchemy.orm import Session

from ..user.user_model import User
from ..event.event_model import Event
from ..club.club_model import Club
from ..competition.competition_model import Competition
from ..enums.account_type import AccountType
from ..enums.privacy import Privacy


def search_users(db: Session, q: str, limit: int) -> list[User]:
    pattern = f'%{q}%'
    return db.query(User).filter(
        User.is_active == True,
        User.account_type == AccountType.REGISTERED,
        (
            User.username_display.ilike(pattern) |
            User.first_name.ilike(pattern) |
            User.last_name.ilike(pattern)
        )
    ).limit(limit).all()


def search_events(db: Session, q: str, limit: int) -> list[Event]:
    pattern = f'%{q}%'
    return db.query(Event).filter(
        Event.privacy == Privacy.PUBLIC,
        (
            Event.name.ilike(pattern) |
            Event.location.ilike(pattern)
        )
    ).limit(limit).all()


def search_clubs(db: Session, q: str, limit: int) -> list[Club]:
    pattern = f'%{q}%'
    return db.query(Club).filter(
        Club.privacy == Privacy.PUBLIC,
        (
            Club.name.ilike(pattern) |
            Club.location.ilike(pattern)
        )
    ).limit(limit).all()


def search_competitions(db: Session, q: str, limit: int) -> list[Competition]:
    pattern = f'%{q}%'
    return db.query(Competition).join(Event, Competition.event_id == Event.id).filter(
        Event.privacy == Privacy.PUBLIC,
        (
            Competition.name.ilike(pattern) |
            Competition.location.ilike(pattern)
        )
    ).limit(limit).all()
