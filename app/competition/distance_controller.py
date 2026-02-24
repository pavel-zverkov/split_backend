from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth.auth_service import get_current_user
from ..user.user_model import User
from . import competition_crud, distance_crud
from .distance_schema import (
    DistanceCreate,
    DistanceUpdate,
    DistanceResponse,
    DistanceListItem,
    DistanceListResponse,
    ControlPointInput,
    ControlPointResponse,
)

distance_router = APIRouter(tags=['distances'])


def get_competition_or_404(db: Session, competition_id: int):
    competition = competition_crud.get_competition(db, competition_id)
    if not competition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Competition not found'
        )
    return competition


def get_distance_or_404(db: Session, distance_id: int):
    distance = distance_crud.get_distance(db, distance_id)
    if not distance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Distance not found'
        )
    return distance


@distance_router.post(
    '/api/competitions/{competition_id}/distances',
    response_model=DistanceResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_distance(
    competition_id: int,
    data: DistanceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a distance with optional inline control points."""
    competition = get_competition_or_404(db, competition_id)

    if not competition_crud.can_manage_competition(db, current_user.id, competition.event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only chief organizer, secretary, or judge can manage distances'
        )

    distance = distance_crud.create_distance(db, competition_id, data)

    return DistanceResponse(
        id=distance.id,
        competition_id=distance.competition_id,
        name=distance.name,
        distance_meters=distance.distance_meters,
        climb_meters=distance.climb_meters,
        classes=distance.classes,
        control_points=[
            ControlPointResponse(
                id=cp.id, code=cp.code, sequence=cp.sequence, type=cp.type
            ) for cp in distance.control_points
        ],
        created_at=distance.created_at,
    )


@distance_router.get(
    '/api/competitions/{competition_id}/distances',
    response_model=DistanceListResponse
)
async def list_distances(
    competition_id: int,
    db: Session = Depends(get_db)
):
    """List distances for a competition."""
    get_competition_or_404(db, competition_id)

    distances = distance_crud.get_distances_by_competition(db, competition_id)

    items = [
        DistanceListItem(
            id=d.id,
            name=d.name,
            distance_meters=d.distance_meters,
            climb_meters=d.climb_meters,
            classes=d.classes,
            control_points_count=len(d.control_points),
        )
        for d in distances
    ]

    return DistanceListResponse(distances=items, total=len(items))


@distance_router.get(
    '/api/distances/{distance_id}',
    response_model=DistanceResponse
)
async def get_distance(
    distance_id: int,
    db: Session = Depends(get_db)
):
    """Get distance detail with control points."""
    distance = get_distance_or_404(db, distance_id)

    return DistanceResponse(
        id=distance.id,
        competition_id=distance.competition_id,
        name=distance.name,
        distance_meters=distance.distance_meters,
        climb_meters=distance.climb_meters,
        classes=distance.classes,
        control_points=[
            ControlPointResponse(
                id=cp.id, code=cp.code, sequence=cp.sequence, type=cp.type
            ) for cp in distance.control_points
        ],
        created_at=distance.created_at,
    )


@distance_router.patch(
    '/api/distances/{distance_id}',
    response_model=DistanceResponse
)
async def update_distance(
    distance_id: int,
    data: DistanceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update distance metadata."""
    distance = get_distance_or_404(db, distance_id)
    competition = get_competition_or_404(db, distance.competition_id)

    if not competition_crud.can_manage_competition(db, current_user.id, competition.event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only chief organizer, secretary, or judge can manage distances'
        )

    updated = distance_crud.update_distance(db, distance, data)

    return DistanceResponse(
        id=updated.id,
        competition_id=updated.competition_id,
        name=updated.name,
        distance_meters=updated.distance_meters,
        climb_meters=updated.climb_meters,
        classes=updated.classes,
        control_points=[
            ControlPointResponse(
                id=cp.id, code=cp.code, sequence=cp.sequence, type=cp.type
            ) for cp in updated.control_points
        ],
        created_at=updated.created_at,
    )


@distance_router.delete(
    '/api/distances/{distance_id}',
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_distance(
    distance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a distance (cascades control points)."""
    distance = get_distance_or_404(db, distance_id)
    competition = get_competition_or_404(db, distance.competition_id)

    if not competition_crud.can_manage_competition(db, current_user.id, competition.event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only chief organizer, secretary, or judge can manage distances'
        )

    distance_crud.delete_distance(db, distance)
    return None


@distance_router.put(
    '/api/distances/{distance_id}/control-points',
    response_model=list[ControlPointResponse]
)
async def replace_control_points(
    distance_id: int,
    control_points: list[ControlPointInput],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Replace all control points for a distance."""
    distance = get_distance_or_404(db, distance_id)
    competition = get_competition_or_404(db, distance.competition_id)

    if not competition_crud.can_manage_competition(db, current_user.id, competition.event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only chief organizer, secretary, or judge can manage distances'
        )

    new_cps = distance_crud.replace_control_points(db, distance, control_points)

    return [
        ControlPointResponse(
            id=cp.id, code=cp.code, sequence=cp.sequence, type=cp.type
        ) for cp in new_cps
    ]
