from datetime import datetime, timezone

from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from .club_model import Club
from .club_membership_model import ClubMembership
from .club_schema import ClubCreate, ClubUpdate
from ..enums.privacy import Privacy
from ..enums.club_role import ClubRole
from ..enums.membership_status import MembershipStatus


def get_club_by_id(db: Session, club_id: int) -> Club | None:
    return db.query(Club).filter(Club.id == club_id).first()


def get_club_by_name(db: Session, name: str) -> Club | None:
    return db.query(Club).filter(Club.name == name).first()


def create_club(db: Session, data: ClubCreate, owner_id: int) -> Club:
    club = Club(
        name=data.name,
        description=data.description,
        location=data.location,
        privacy=data.privacy,
        owner_id=owner_id,
    )
    db.add(club)
    db.flush()

    # Create owner membership
    membership = ClubMembership(
        user_id=owner_id,
        club_id=club.id,
        role=ClubRole.OWNER,
        status=MembershipStatus.ACTIVE,
        joined_at=datetime.now(timezone.utc),
    )
    db.add(membership)
    db.commit()
    db.refresh(club)
    return club


def update_club(db: Session, club: Club, data: ClubUpdate) -> Club:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(club, field, value)
    db.commit()
    db.refresh(club)
    return club


def delete_club(db: Session, club: Club) -> None:
    db.delete(club)
    db.commit()


def get_members_count(db: Session, club_id: int) -> int:
    return db.query(ClubMembership).filter(
        ClubMembership.club_id == club_id,
        ClubMembership.status == MembershipStatus.ACTIVE
    ).count()


def get_membership(db: Session, user_id: int, club_id: int) -> ClubMembership | None:
    return db.query(ClubMembership).filter(
        ClubMembership.user_id == user_id,
        ClubMembership.club_id == club_id
    ).first()


def get_membership_status(db: Session, user_id: int, club_id: int) -> MembershipStatus | None:
    membership = get_membership(db, user_id, club_id)
    if not membership:
        return None
    # Mask rejected as pending
    if membership.status == MembershipStatus.REJECTED:
        return MembershipStatus.PENDING
    return membership.status


def get_membership_role(db: Session, user_id: int, club_id: int) -> ClubRole | None:
    membership = get_membership(db, user_id, club_id)
    if not membership or membership.status != MembershipStatus.ACTIVE:
        return None
    return membership.role


def is_club_admin(db: Session, user_id: int, club_id: int) -> bool:
    """Check if user is owner or coach of the club."""
    membership = get_membership(db, user_id, club_id)
    if not membership or membership.status != MembershipStatus.ACTIVE:
        return False
    return membership.role in [ClubRole.OWNER, ClubRole.COACH]


def is_club_owner(db: Session, user_id: int, club_id: int) -> bool:
    """Check if user is owner of the club."""
    membership = get_membership(db, user_id, club_id)
    if not membership or membership.status != MembershipStatus.ACTIVE:
        return False
    return membership.role == ClubRole.OWNER


def search_clubs(
    db: Session,
    query: str | None = None,
    privacy: Privacy | None = None,
    current_user_id: int | None = None,
    limit: int = 20,
    offset: int = 0
) -> tuple[list[Club], int]:
    q = db.query(Club)

    # Filter by privacy - private clubs only visible to members
    if privacy:
        q = q.filter(Club.privacy == privacy)

    # If not authenticated or filtering for specific privacy, exclude private clubs
    # unless user is a member
    if current_user_id:
        # Show all clubs where user is member OR club is not private
        member_club_ids = db.query(ClubMembership.club_id).filter(
            ClubMembership.user_id == current_user_id,
            ClubMembership.status == MembershipStatus.ACTIVE
        ).subquery()
        q = q.filter(
            or_(
                Club.privacy != Privacy.PRIVATE,
                Club.id.in_(member_club_ids)
            )
        )
    else:
        # Unauthenticated users can't see private clubs
        q = q.filter(Club.privacy != Privacy.PRIVATE)

    if query:
        search_pattern = f'%{query}%'
        q = q.filter(
            or_(
                Club.name.ilike(search_pattern),
                Club.description.ilike(search_pattern),
                Club.location.ilike(search_pattern),
            )
        )

    total = q.count()
    clubs = q.order_by(Club.created_at.desc()).offset(offset).limit(limit).all()
    return clubs, total


def get_club_members(
    db: Session,
    club_id: int,
    role: ClubRole | None = None,
    status: MembershipStatus | None = None,
    can_see_pending: bool = False,
    limit: int = 20,
    offset: int = 0
) -> tuple[list[ClubMembership], int]:
    q = db.query(ClubMembership).filter(ClubMembership.club_id == club_id)

    if role:
        q = q.filter(ClubMembership.role == role)

    if status:
        q = q.filter(ClubMembership.status == status)
    elif can_see_pending:
        # Owner/coach can see active and pending
        q = q.filter(ClubMembership.status.in_([MembershipStatus.ACTIVE, MembershipStatus.PENDING]))
    else:
        # Regular users only see active members
        q = q.filter(ClubMembership.status == MembershipStatus.ACTIVE)

    total = q.count()
    members = q.offset(offset).limit(limit).all()
    return members, total


def update_club_logo(db: Session, club: Club, logo_url: str) -> Club:
    club.logo = logo_url
    db.commit()
    db.refresh(club)
    return club


def get_membership_by_id(db: Session, membership_id: int) -> ClubMembership | None:
    return db.query(ClubMembership).filter(ClubMembership.id == membership_id).first()


def get_initial_membership_status(club: Club) -> MembershipStatus:
    """Determine initial membership status based on club's privacy settings."""
    if club.privacy == Privacy.PUBLIC:
        return MembershipStatus.ACTIVE
    return MembershipStatus.PENDING


def create_membership(
    db: Session,
    user_id: int,
    club_id: int,
    status: MembershipStatus,
    role: ClubRole = ClubRole.MEMBER
) -> ClubMembership:
    membership = ClubMembership(
        user_id=user_id,
        club_id=club_id,
        role=role,
        status=status,
        joined_at=datetime.now(timezone.utc) if status == MembershipStatus.ACTIVE else None,
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


def update_membership_status(
    db: Session,
    membership: ClubMembership,
    status: MembershipStatus
) -> ClubMembership:
    membership.status = status
    if status == MembershipStatus.ACTIVE:
        membership.joined_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(membership)
    return membership


def update_membership_role(
    db: Session,
    membership: ClubMembership,
    role: ClubRole
) -> ClubMembership:
    membership.role = role
    db.commit()
    db.refresh(membership)
    return membership


def delete_membership(db: Session, membership: ClubMembership) -> None:
    db.delete(membership)
    db.commit()


def transfer_ownership(
    db: Session,
    club: Club,
    old_owner_membership: ClubMembership,
    new_owner_membership: ClubMembership
) -> Club:
    # Update old owner to coach
    old_owner_membership.role = ClubRole.COACH
    # Update new owner to owner
    new_owner_membership.role = ClubRole.OWNER
    # Update club owner_id
    club.owner_id = new_owner_membership.user_id
    db.commit()
    db.refresh(club)
    return club


def can_remove_member(actor_role: ClubRole, target_role: ClubRole) -> bool:
    """Check if actor can remove target based on roles."""
    if actor_role == ClubRole.OWNER:
        # Owner can remove coach or member
        return target_role in [ClubRole.COACH, ClubRole.MEMBER]
    if actor_role == ClubRole.COACH:
        # Coach can only remove member
        return target_role == ClubRole.MEMBER
    return False
