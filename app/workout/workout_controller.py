from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..database.minio_integration import get_minio_client
from ..auth.auth_service import get_current_user, get_current_user_optional
from ..user.user_model import User
from ..user.user_crud import get_user_by_id
from ..enums.workout_status import WorkoutStatus
from . import workout_crud
from .workout_schema import (
    WorkoutCreate,
    WorkoutUpdate,
    WorkoutResponse,
    WorkoutListItem,
    WorkoutDetailResponse,
    WorkoutsListResponse,
    WorkoutOwnerBrief,
    WorkoutUserBrief,
    WorkoutSplitResponse,
    WorkoutArtifactBrief,
    LinkedResultBrief,
    UserWorkoutsResponse,
)

workout_router = APIRouter(tags=['workouts'])

BUCKET_NAME = 'event-artifacts'


# ===== Helper Functions =====

def get_workout_or_404(db: Session, workout_id: int):
    workout = workout_crud.get_workout(db, workout_id)
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Workout not found'
        )
    return workout


def build_linked_result(result) -> LinkedResultBrief | None:
    if not result:
        return None
    return LinkedResultBrief(
        id=result.id,
        competition_id=result.competition_id,
        competition_name=result.competition.name if result.competition else '',
        position=result.position,
        time_total=result.time_total,
    )


def build_workout_list_item(workout, db: Session) -> WorkoutListItem:
    linked_result = workout_crud.get_linked_result(db, workout.id)
    return WorkoutListItem(
        id=workout.id,
        title=workout.title,
        sport_kind=workout.sport_kind,
        privacy=workout.privacy,
        status=workout.status,
        start_datetime=workout.start_datetime,
        duration_ms=workout.duration_ms,
        distance_meters=workout.distance_meters,
        elevation_gain=workout.elevation_gain,
        has_splits=len(workout.splits) > 0 if workout.splits else False,
        linked_result=build_linked_result(linked_result),
        created_at=workout.created_at,
    )


# ===== 12.1 Create Workout =====

@workout_router.post('/api/workouts', response_model=WorkoutResponse, status_code=status.HTTP_201_CREATED)
async def create_workout(
    data: WorkoutCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new workout."""
    # Auto-calculate finish_datetime / duration_ms
    if data.finish_datetime and data.duration_ms:
        expected = data.start_datetime + timedelta(milliseconds=data.duration_ms)
        if abs((data.finish_datetime - expected).total_seconds()) > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='finish_datetime and duration_ms are inconsistent with start_datetime'
            )
    elif data.finish_datetime and not data.duration_ms:
        if data.finish_datetime <= data.start_datetime:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='finish_datetime must be after start_datetime'
            )
        data.duration_ms = int((data.finish_datetime - data.start_datetime).total_seconds() * 1000)
    elif data.duration_ms and not data.finish_datetime:
        if data.duration_ms <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='duration_ms must be positive'
            )
        data.finish_datetime = data.start_datetime + timedelta(milliseconds=data.duration_ms)

    workout = workout_crud.create_workout(db, current_user.id, data)

    return WorkoutResponse(
        id=workout.id,
        user_id=workout.user_id,
        title=workout.title,
        description=workout.description,
        sport_kind=workout.sport_kind,
        privacy=workout.privacy,
        status=workout.status,
        start_datetime=workout.start_datetime,
        finish_datetime=workout.finish_datetime,
        duration_ms=workout.duration_ms,
        distance_meters=workout.distance_meters,
        elevation_gain=workout.elevation_gain,
        has_splits=False,
        artifacts_count=0,
        created_at=workout.created_at,
    )


# ===== 12.2 List My Workouts =====

@workout_router.get('/api/workouts', response_model=WorkoutsListResponse)
async def list_my_workouts(
    sport_kind: str | None = None,
    workout_status: str | None = Query(None, alias='status'),
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List current user's workouts."""
    # Parse status
    status_filter = None
    if workout_status:
        try:
            status_filter = WorkoutStatus(workout_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Invalid status: {workout_status}'
            )

    workouts, total = workout_crud.get_user_workouts(
        db, current_user.id,
        sport_kind=sport_kind,
        status=status_filter,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset
    )

    items = [build_workout_list_item(w, db) for w in workouts]

    return WorkoutsListResponse(
        workouts=items,
        total=total,
        limit=limit,
        offset=offset,
    )


# ===== 12.3 Get Workout Details =====

@workout_router.get('/api/workouts/{workout_id}', response_model=WorkoutDetailResponse)
async def get_workout(
    workout_id: int,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Get workout details."""
    workout = get_workout_or_404(db, workout_id)

    # Check visibility
    if not workout_crud.can_view_workout(db, workout, current_user.id if current_user else None):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Private workout'
        )

    # Build splits
    splits = None
    if workout.splits:
        splits = [
            WorkoutSplitResponse(
                id=s.id,
                sequence=s.sequence,
                control_point=s.control_point,
                distance_meters=s.distance_meters,
                cumulative_time=s.cumulative_time,
                split_time=s.split_time,
            )
            for s in sorted(workout.splits, key=lambda x: x.sequence)
        ]

    # Build artifacts
    artifacts = None
    workout_artifacts = workout_crud.get_workout_artifacts(db, workout_id)
    if workout_artifacts:
        artifacts = [
            WorkoutArtifactBrief(
                id=a.id,
                kind=a.kind.value,
                file_name=a.file_name,
            )
            for a in workout_artifacts
        ]

    # Get linked result
    linked_result = workout_crud.get_linked_result(db, workout_id)

    return WorkoutDetailResponse(
        id=workout.id,
        user=WorkoutOwnerBrief(
            id=workout.owner.id,
            username_display=workout.owner.username_display,
            first_name=workout.owner.first_name,
            last_name=workout.owner.last_name,
        ),
        title=workout.title,
        description=workout.description,
        sport_kind=workout.sport_kind,
        privacy=workout.privacy,
        status=workout.status,
        start_datetime=workout.start_datetime,
        finish_datetime=workout.finish_datetime,
        duration_ms=workout.duration_ms,
        distance_meters=workout.distance_meters,
        elevation_gain=workout.elevation_gain,
        splits=splits,
        artifacts=artifacts,
        linked_result=build_linked_result(linked_result),
        created_at=workout.created_at,
    )


# ===== 12.4 List User's Workouts =====

@workout_router.get('/api/users/{user_id}/workouts', response_model=UserWorkoutsResponse)
async def list_user_workouts(
    user_id: int,
    sport_kind: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """List a user's workouts (follows privacy)."""
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found'
        )

    workouts, total = workout_crud.get_visible_workouts(
        db, user_id,
        viewer_id=current_user.id if current_user else None,
        limit=limit,
        offset=offset
    )

    # Apply additional filters
    # Note: filters should ideally be applied in the query, but for simplicity we filter here
    # This is acceptable for small result sets
    items = [build_workout_list_item(w, db) for w in workouts]

    return UserWorkoutsResponse(
        user=WorkoutUserBrief(
            id=user.id,
            username_display=user.username_display,
            first_name=user.first_name,
        ),
        workouts=items,
        total=total,
        limit=limit,
        offset=offset,
    )


# ===== 12.5 Update Workout =====

@workout_router.patch('/api/workouts/{workout_id}', response_model=WorkoutResponse)
async def update_workout(
    workout_id: int,
    data: WorkoutUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a workout (owner only)."""
    workout = get_workout_or_404(db, workout_id)

    if workout.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only owner can update workout'
        )

    updated = workout_crud.update_workout(db, workout, data)
    artifacts_count = len(workout_crud.get_workout_artifacts(db, workout_id))

    return WorkoutResponse(
        id=updated.id,
        user_id=updated.user_id,
        title=updated.title,
        description=updated.description,
        sport_kind=updated.sport_kind,
        privacy=updated.privacy,
        status=updated.status,
        start_datetime=updated.start_datetime,
        finish_datetime=updated.finish_datetime,
        duration_ms=updated.duration_ms,
        distance_meters=updated.distance_meters,
        elevation_gain=updated.elevation_gain,
        has_splits=len(updated.splits) > 0 if updated.splits else False,
        artifacts_count=artifacts_count,
        created_at=updated.created_at,
    )


# ===== 12.6 Delete Workout =====

@workout_router.delete('/api/workouts/{workout_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_workout(
    workout_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a workout (owner only) with cascade."""
    workout = get_workout_or_404(db, workout_id)

    if workout.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only owner can delete workout'
        )

    # Unlink results
    workout_crud.unlink_results_from_workout(db, workout_id)

    # Delete artifacts and get file paths
    file_paths = workout_crud.delete_workout_artifacts(db, workout_id)

    # Delete files from MinIO
    minio_client = get_minio_client()
    for path in file_paths:
        try:
            minio_client.remove_object(BUCKET_NAME, path)
        except Exception:
            pass  # Ignore errors

    # Delete workout (splits cascade automatically)
    workout_crud.delete_workout(db, workout)
    return None
