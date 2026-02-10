from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape

from ..database import get_db
from ..auth.auth_service import get_current_user, get_current_user_optional
from ..user.user_model import User
from . import workout_crud
from . import workout_split_crud
from .workout_split_schema import (
    SplitsCreateRequest,
    SplitUpdate,
    SplitResponse,
    SplitsListResponse,
    PositionSchema,
)

split_router = APIRouter(tags=['workout-splits'])


# ===== Helper Functions =====

def get_workout_or_404(db: Session, workout_id: int):
    workout = workout_crud.get_workout(db, workout_id)
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Workout not found'
        )
    return workout


def build_split_response(split) -> SplitResponse:
    """Build split response with position conversion."""
    position = None
    if split.position:
        point = to_shape(split.position)
        position = PositionSchema(lat=point.y, lng=point.x)

    return SplitResponse(
        id=split.id,
        sequence=split.sequence,
        control_point=split.control_point,
        distance_meters=split.distance_meters,
        cumulative_time=split.cumulative_time,
        split_time=split.split_time,
        position=position,
    )


# ===== 13.1 List Workout Splits =====

@split_router.get('/api/workouts/{workout_id}/splits', response_model=SplitsListResponse)
async def list_workout_splits(
    workout_id: int,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """List workout splits (follows workout privacy)."""
    workout = get_workout_or_404(db, workout_id)

    # Check visibility
    if not workout_crud.can_view_workout(db, workout, current_user.id if current_user else None):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Private workout'
        )

    splits = workout_split_crud.get_workout_splits(db, workout_id)
    items = [build_split_response(s) for s in splits]

    return SplitsListResponse(
        workout_id=workout_id,
        splits=items,
        total=len(items),
    )


# ===== 13.2 Manual Split Entry =====

@split_router.post('/api/workouts/{workout_id}/splits', response_model=SplitsListResponse, status_code=status.HTTP_201_CREATED)
async def create_splits(
    workout_id: int,
    data: SplitsCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manual split entry (replaces all existing splits)."""
    workout = get_workout_or_404(db, workout_id)

    if workout.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only owner can modify splits'
        )

    splits = workout_split_crud.create_splits(db, workout_id, data.splits)
    items = [build_split_response(s) for s in splits]

    return SplitsListResponse(
        workout_id=workout_id,
        splits=items,
        total=len(items),
    )


# ===== 13.3 Update Single Split =====

@split_router.patch('/api/workouts/{workout_id}/splits/{split_id}', response_model=SplitResponse)
async def update_split(
    workout_id: int,
    split_id: int,
    data: SplitUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a single split."""
    workout = get_workout_or_404(db, workout_id)

    if workout.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only owner can modify splits'
        )

    split = workout_split_crud.get_split(db, split_id)
    if not split or split.workout_id != workout_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Split not found'
        )

    updated = workout_split_crud.update_split(db, split, data)
    return build_split_response(updated)


# ===== 13.4 Delete All Splits =====

@split_router.delete('/api/workouts/{workout_id}/splits', status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_splits(
    workout_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete all splits for a workout."""
    workout = get_workout_or_404(db, workout_id)

    if workout.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only owner can modify splits'
        )

    workout_split_crud.delete_all_splits(db, workout_id)
    return None
