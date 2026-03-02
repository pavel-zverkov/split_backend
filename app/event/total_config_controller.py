from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth.auth_service import get_current_user, get_current_user_optional
from ..user.user_model import User
from ..enums.event_format import EventFormat
from . import event_crud, total_config_crud
from .total_calculator import recalculate_total, get_preset_rules
from .total_config_schema import (
    TotalConfigCreate,
    TotalConfigUpdate,
    TotalConfigResponse,
    TotalConfigListResponse,
    TotalResultItem,
    TotalResultsListResponse,
    TotalResultUserBrief,
    TotalResultDetailResponse,
    StageBreakdownItem,
)

total_config_router = APIRouter(prefix='/api/events/{event_id}/total-configs', tags=['event-total-results'])


def get_event_or_404(db: Session, event_id: int):
    event = event_crud.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Event not found'
        )
    return event


def get_config_or_404(db: Session, config_id: int, event_id: int):
    config = total_config_crud.get_config(db, config_id)
    if not config or config.event_id != event_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Total config not found'
        )
    return config


def build_user_brief(user) -> TotalResultUserBrief:
    return TotalResultUserBrief(
        id=user.id,
        username_display=user.username_display,
        first_name=user.first_name,
        last_name=user.last_name,
    )


# ===== 1. Create Total Config =====

@total_config_router.post('', response_model=TotalConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_total_config(
    event_id: int,
    data: TotalConfigCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a total results config. Only for multi_stage events."""
    event = get_event_or_404(db, event_id)

    if event.event_format == EventFormat.SINGLE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Total configs are only available for multi-stage events'
        )

    if not event_crud.can_update_event(db, current_user.id, event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only organizer or chief secretary can manage total configs'
        )

    # Resolve rules from preset or custom
    if data.preset:
        rules_dict = get_preset_rules(data.preset)
        if not rules_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Unknown preset: {data.preset}'
            )
    elif data.rules:
        rules_dict = data.rules.model_dump()
    else:
        rules_dict = get_preset_rules('sum_time')

    config = total_config_crud.create_config(
        db,
        event_id=event_id,
        name=data.name,
        rules=rules_dict,
        auto_calculate=data.auto_calculate,
    )

    return TotalConfigResponse(
        id=config.id,
        event_id=config.event_id,
        name=config.name,
        rules=config.rules,
        auto_calculate=config.auto_calculate,
        results_count=0,
        created_at=config.created_at,
    )


# ===== 2. List Total Configs =====

@total_config_router.get('', response_model=TotalConfigListResponse)
async def list_total_configs(
    event_id: int,
    db: Session = Depends(get_db)
):
    """List total configs for an event."""
    get_event_or_404(db, event_id)

    configs = total_config_crud.get_configs_by_event(db, event_id)

    items = [
        TotalConfigResponse(
            id=c.id,
            event_id=c.event_id,
            name=c.name,
            rules=c.rules,
            auto_calculate=c.auto_calculate,
            results_count=total_config_crud.get_results_count(db, c.id),
            created_at=c.created_at,
        )
        for c in configs
    ]

    return TotalConfigListResponse(configs=items, total=len(items))


# ===== 3. Get Total Config =====

@total_config_router.get('/{config_id}', response_model=TotalConfigResponse)
async def get_total_config(
    event_id: int,
    config_id: int,
    db: Session = Depends(get_db)
):
    """Get total config with rules."""
    get_event_or_404(db, event_id)
    config = get_config_or_404(db, config_id, event_id)

    return TotalConfigResponse(
        id=config.id,
        event_id=config.event_id,
        name=config.name,
        rules=config.rules,
        auto_calculate=config.auto_calculate,
        results_count=total_config_crud.get_results_count(db, config.id),
        created_at=config.created_at,
    )


# ===== 4. Update Total Config =====

@total_config_router.patch('/{config_id}', response_model=TotalConfigResponse)
async def update_total_config(
    event_id: int,
    config_id: int,
    data: TotalConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a total config."""
    get_event_or_404(db, event_id)
    config = get_config_or_404(db, config_id, event_id)

    if not event_crud.can_update_event(db, current_user.id, event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only organizer or chief secretary can manage total configs'
        )

    rules_dict = data.rules.model_dump() if data.rules else None

    updated = total_config_crud.update_config(
        db, config,
        name=data.name,
        rules=rules_dict,
        auto_calculate=data.auto_calculate,
    )

    return TotalConfigResponse(
        id=updated.id,
        event_id=updated.event_id,
        name=updated.name,
        rules=updated.rules,
        auto_calculate=updated.auto_calculate,
        results_count=total_config_crud.get_results_count(db, updated.id),
        created_at=updated.created_at,
    )


# ===== 5. Delete Total Config =====

@total_config_router.delete('/{config_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_total_config(
    event_id: int,
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a total config (cascades results)."""
    get_event_or_404(db, event_id)
    config = get_config_or_404(db, config_id, event_id)

    if not event_crud.can_update_event(db, current_user.id, event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only organizer or chief secretary can manage total configs'
        )

    total_config_crud.delete_config(db, config)
    return None


# ===== 6. Manual Recalculate =====

@total_config_router.post('/{config_id}/recalculate')
async def trigger_recalculate(
    event_id: int,
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually trigger recalculation of total results."""
    get_event_or_404(db, event_id)
    config = get_config_or_404(db, config_id, event_id)

    if not event_crud.can_update_event(db, current_user.id, event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only organizer or chief secretary can trigger recalculation'
        )

    count = recalculate_total(db, config)

    return {'recalculated': True, 'results_count': count}


# ===== 7. Get Total Results (Leaderboard) =====

@total_config_router.get('/{config_id}/results', response_model=TotalResultsListResponse)
async def get_total_results(
    event_id: int,
    config_id: int,
    class_filter: str | None = Query(None, alias='class'),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get total results leaderboard."""
    get_event_or_404(db, event_id)
    config = get_config_or_404(db, config_id, event_id)

    results, total = total_config_crud.get_total_results(
        db, config.id,
        class_filter=class_filter,
        limit=limit,
        offset=offset,
    )

    items = [
        TotalResultItem(
            id=r.id,
            user=build_user_brief(r.user),
            class_=r.class_,
            total_value=r.total_value,
            position=r.position,
            position_overall=r.position_overall,
            stages_counted=r.stages_counted,
            stages_total=r.stages_total,
            status=r.status,
        )
        for r in results
    ]

    return TotalResultsListResponse(
        results=items,
        total=total,
        limit=limit,
        offset=offset,
    )


# ===== 8. Get My Total Result =====

@total_config_router.get('/{config_id}/results/me', response_model=TotalResultDetailResponse)
async def get_my_total_result(
    event_id: int,
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's total result."""
    get_event_or_404(db, event_id)
    config = get_config_or_404(db, config_id, event_id)

    result = total_config_crud.get_my_total_result(db, config.id, current_user.id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='No total result found'
        )

    stages = _build_stage_breakdown(db, config, result)

    return TotalResultDetailResponse(
        id=result.id,
        user=build_user_brief(result.user),
        class_=result.class_,
        total_value=result.total_value,
        position=result.position,
        position_overall=result.position_overall,
        stages_counted=result.stages_counted,
        stages_total=result.stages_total,
        status=result.status,
        stages=stages,
        calculated_at=result.calculated_at,
    )


# ===== 9. Get Total Result Detail =====

@total_config_router.get('/{config_id}/results/{result_id}', response_model=TotalResultDetailResponse)
async def get_total_result_detail(
    event_id: int,
    config_id: int,
    result_id: int,
    db: Session = Depends(get_db)
):
    """Get total result detail with per-stage breakdown."""
    get_event_or_404(db, event_id)
    config = get_config_or_404(db, config_id, event_id)

    result = total_config_crud.get_total_result(db, result_id)
    if not result or result.config_id != config.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Total result not found'
        )

    stages = _build_stage_breakdown(db, config, result)

    return TotalResultDetailResponse(
        id=result.id,
        user=build_user_brief(result.user),
        class_=result.class_,
        total_value=result.total_value,
        position=result.position,
        position_overall=result.position_overall,
        stages_counted=result.stages_counted,
        stages_total=result.stages_total,
        status=result.status,
        stages=stages,
        calculated_at=result.calculated_at,
    )


def _build_stage_breakdown(db: Session, config, total_result) -> list[StageBreakdownItem]:
    """Build per-stage breakdown by joining from Result table."""
    from ..competition.competition_model import Competition
    from ..result.result_model import Result

    rules = config.rules or {}
    source = rules.get('source', {})

    comp_query = db.query(Competition).filter(Competition.event_id == config.event_id)
    if source.get('competition_ids'):
        comp_query = comp_query.filter(Competition.id.in_(source['competition_ids']))
    competitions = comp_query.order_by(Competition.date.asc()).all()

    stages = []
    for comp in competitions:
        result = db.query(Result).filter(
            Result.competition_id == comp.id,
            Result.user_id == total_result.user_id,
        ).first()

        stages.append(StageBreakdownItem(
            competition_id=comp.id,
            competition_name=comp.name,
            result_id=result.id if result else None,
            time_total=result.time_total if result else None,
            position=result.position if result else None,
            status=result.status.value if result else None,
        ))

    return stages
