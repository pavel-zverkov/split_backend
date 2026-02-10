from sqlalchemy.orm import Session
from sqlalchemy import or_

from .artifact_model import Artifact
from ..enums.artifact_kind import ArtifactKind
from ..enums.event_role import EventRole
from ..enums.participation_status import ParticipationStatus
from ..enums.privacy import Privacy


def get_artifact(db: Session, artifact_id: int) -> Artifact | None:
    return db.query(Artifact).filter(Artifact.id == artifact_id).first()


def get_artifact_by_name(
    db: Session,
    file_name: str,
    competition_id: int | None = None,
    workout_id: int | None = None
) -> Artifact | None:
    q = db.query(Artifact).filter(Artifact.file_name == file_name)
    if competition_id:
        q = q.filter(Artifact.competition_id == competition_id)
    if workout_id:
        q = q.filter(Artifact.workout_id == workout_id)
    return q.first()


def create_artifact(
    db: Session,
    user_id: int,
    kind: ArtifactKind,
    file_path: str,
    file_name: str,
    file_size: int,
    mime_type: str,
    competition_id: int | None = None,
    workout_id: int | None = None,
    tags: list[str] | None = None
) -> Artifact:
    artifact = Artifact(
        user_id=user_id,
        kind=kind,
        file_path=file_path,
        file_name=file_name,
        file_size=file_size,
        mime_type=mime_type,
        competition_id=competition_id,
        workout_id=workout_id,
        tags=tags,
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


def update_artifact(
    db: Session,
    artifact: Artifact,
    tags: list[str] | None = None,
    kind: ArtifactKind | None = None
) -> Artifact:
    if tags is not None:
        artifact.tags = tags
    if kind is not None:
        artifact.kind = kind
    db.commit()
    db.refresh(artifact)
    return artifact


def delete_artifact(db: Session, artifact: Artifact) -> None:
    db.delete(artifact)
    db.commit()


def get_competition_artifacts(
    db: Session,
    competition_id: int,
    kind: ArtifactKind | None = None,
    tags: list[str] | None = None,
    limit: int = 20,
    offset: int = 0
) -> tuple[list[Artifact], int]:
    q = db.query(Artifact).filter(Artifact.competition_id == competition_id)

    if kind:
        q = q.filter(Artifact.kind == kind)
    if tags:
        # Filter by any of the provided tags (PostgreSQL ARRAY overlap)
        q = q.filter(Artifact.tags.overlap(tags))

    total = q.count()
    artifacts = q.order_by(Artifact.created_at.desc()).offset(offset).limit(limit).all()
    return artifacts, total


def get_workout_artifacts(
    db: Session,
    workout_id: int,
    kind: ArtifactKind | None = None,
    limit: int = 20,
    offset: int = 0
) -> tuple[list[Artifact], int]:
    q = db.query(Artifact).filter(Artifact.workout_id == workout_id)

    if kind:
        q = q.filter(Artifact.kind == kind)

    total = q.count()
    artifacts = q.order_by(Artifact.created_at.desc()).offset(offset).limit(limit).all()
    return artifacts, total


def can_manage_competition_artifact(db: Session, user_id: int, event_id: int, artifact_user_id: int) -> bool:
    """Check if user can manage competition artifact (organizer, secretary, or uploader)."""
    from ..event.event_crud import get_participation

    # Uploader can always manage
    if user_id == artifact_user_id:
        return True

    # Check event role
    participation = get_participation(db, user_id, event_id)
    if not participation or participation.status != ParticipationStatus.APPROVED:
        return False

    return participation.role in [EventRole.ORGANIZER, EventRole.SECRETARY]


def can_upload_competition_artifact(db: Session, user_id: int, event_id: int) -> bool:
    """Check if user can upload competition artifact (organizer or secretary)."""
    from ..event.event_crud import get_participation

    participation = get_participation(db, user_id, event_id)
    if not participation or participation.status != ParticipationStatus.APPROVED:
        return False

    return participation.role in [EventRole.ORGANIZER, EventRole.SECRETARY]


def can_view_workout_artifact(db: Session, viewer_id: int | None, workout_user_id: int, privacy: Privacy) -> bool:
    """Check if viewer can see workout artifact based on privacy settings."""
    # Public artifacts are visible to everyone
    if privacy == Privacy.PUBLIC:
        return True

    # Private and other modes require authentication
    if viewer_id is None:
        return False

    # Owner can always see
    if viewer_id == workout_user_id:
        return True

    # For FOLLOWERS privacy, check if viewer follows the workout owner
    if privacy == Privacy.FOLLOWERS:
        from ..user.user_follow_model import UserFollow
        from ..enums.follow_status import FollowStatus

        follow = db.query(UserFollow).filter(
            UserFollow.follower_id == viewer_id,
            UserFollow.following_id == workout_user_id,
            UserFollow.status == FollowStatus.ACCEPTED
        ).first()
        return follow is not None

    # Private and BY_REQUEST only visible to owner
    return False
