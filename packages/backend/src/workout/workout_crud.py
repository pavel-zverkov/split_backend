from datetime import date

from sqlalchemy.orm import Session

from .workout_model import Workout
from .workout_schema import WorkoutCreate, WorkoutUpdate
from ..enums.workout_status import WorkoutStatus
from ..enums.privacy import Privacy


def get_workout(db: Session, workout_id: int) -> Workout | None:
    return db.query(Workout).filter(Workout.id == workout_id).first()


def get_workout_by_event(
    db: Session,
    user_id: int,
    event_id: int,
    competition_date: date
) -> Workout | None:
    """Legacy function for split comparer compatibility."""
    from ..competition.competition_model import Competition

    workout = db.query(Workout).outerjoin(Competition).filter(
        Workout.user_id == user_id,
        Competition.event_id == event_id,
        Competition.date == competition_date
    ).first()

    return workout


def create_workout(
    db: Session,
    user_id: int,
    data: WorkoutCreate
) -> Workout:
    workout = Workout(
        user_id=user_id,
        title=data.title,
        description=data.description,
        sport_kind=data.sport_kind,
        start_datetime=data.start_datetime,
        finish_datetime=data.finish_datetime,
        duration_seconds=data.duration_seconds,
        distance_meters=data.distance_meters,
        elevation_gain=data.elevation_gain,
        privacy=data.privacy,
        status=WorkoutStatus.DRAFT,
    )
    db.add(workout)
    db.commit()
    db.refresh(workout)
    return workout


def update_workout(
    db: Session,
    workout: Workout,
    data: WorkoutUpdate
) -> Workout:
    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if value is not None:
            setattr(workout, field, value)

    db.commit()
    db.refresh(workout)
    return workout


def delete_workout(db: Session, workout: Workout) -> None:
    db.delete(workout)
    db.commit()


def get_user_workouts(
    db: Session,
    user_id: int,
    sport_kind: str | None = None,
    status: WorkoutStatus | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 20,
    offset: int = 0
) -> tuple[list[Workout], int]:
    from ..enums.sport_kind import SportKind

    q = db.query(Workout).filter(Workout.user_id == user_id)

    if sport_kind:
        try:
            q = q.filter(Workout.sport_kind == SportKind(sport_kind))
        except ValueError:
            pass
    if status:
        q = q.filter(Workout.status == status)
    if date_from:
        q = q.filter(Workout.start_datetime >= date_from)
    if date_to:
        q = q.filter(Workout.start_datetime <= date_to)

    total = q.count()
    workouts = q.order_by(Workout.start_datetime.desc()).offset(offset).limit(limit).all()
    return workouts, total


def get_linked_result(db: Session, workout_id: int):
    """Get result linked to this workout."""
    from ..result.result_model import Result
    return db.query(Result).filter(Result.workout_id == workout_id).first()


def get_workout_artifacts(db: Session, workout_id: int):
    """Get artifacts for this workout."""
    from ..artifact.artifact_model import Artifact
    return db.query(Artifact).filter(Artifact.workout_id == workout_id).all()


def unlink_results_from_workout(db: Session, workout_id: int) -> None:
    """Set workout_id to null in all results referencing this workout."""
    from ..result.result_model import Result
    db.query(Result).filter(Result.workout_id == workout_id).update({"workout_id": None})
    db.commit()


def delete_workout_artifacts(db: Session, workout_id: int) -> list[str]:
    """Delete artifacts and return file paths for MinIO cleanup."""
    from ..artifact.artifact_model import Artifact
    artifacts = db.query(Artifact).filter(Artifact.workout_id == workout_id).all()
    file_paths = [a.file_path for a in artifacts]
    for artifact in artifacts:
        db.delete(artifact)
    db.commit()
    return file_paths


def get_visible_workouts(
    db: Session,
    owner_id: int,
    viewer_id: int | None,
    limit: int = 20,
    offset: int = 0
) -> tuple[list[Workout], int]:
    """Get workouts visible to viewer based on privacy settings."""
    q = db.query(Workout).filter(Workout.user_id == owner_id)

    # If viewer is owner, show all
    if viewer_id == owner_id:
        pass
    # If viewer is authenticated, check privacy
    elif viewer_id is not None:
        from ..user.user_follow_model import UserFollow
        from ..enums.follow_status import FollowStatus

        # Check if viewer follows owner
        follow = db.query(UserFollow).filter(
            UserFollow.follower_id == viewer_id,
            UserFollow.following_id == owner_id,
            UserFollow.status == FollowStatus.ACCEPTED
        ).first()

        if follow:
            # Follower can see public and followers-only
            q = q.filter(Workout.privacy.in_([Privacy.PUBLIC, Privacy.FOLLOWERS]))
        else:
            # Non-follower can only see public
            q = q.filter(Workout.privacy == Privacy.PUBLIC)
    else:
        # Anonymous can only see public
        q = q.filter(Workout.privacy == Privacy.PUBLIC)

    total = q.count()
    workouts = q.order_by(Workout.start_datetime.desc()).offset(offset).limit(limit).all()
    return workouts, total


def can_view_workout(db: Session, workout: Workout, viewer_id: int | None) -> bool:
    """Check if viewer can see the workout."""
    # Public is always visible
    if workout.privacy == Privacy.PUBLIC:
        return True

    # Private requires authentication
    if viewer_id is None:
        return False

    # Owner can always see
    if workout.user_id == viewer_id:
        return True

    # Followers privacy
    if workout.privacy == Privacy.FOLLOWERS:
        from ..user.user_follow_model import UserFollow
        from ..enums.follow_status import FollowStatus

        follow = db.query(UserFollow).filter(
            UserFollow.follower_id == viewer_id,
            UserFollow.following_id == workout.user_id,
            UserFollow.status == FollowStatus.ACCEPTED
        ).first()
        return follow is not None

    # Private and BY_REQUEST only visible to owner
    return False
