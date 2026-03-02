import csv
import io
import re
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth.auth_service import get_current_user, get_current_user_optional
from ..user.user_model import User
from ..competition.competition_crud import get_competition
from ..competition.registration_crud import get_registration_by_user
from ..club import club_crud
from . import result_crud
from .result_schema import (
    ResultCreate,
    ResultUpdate,
    ResultResponse,
    ResultListItem,
    ResultDetailResponse,
    ResultsListResponse,
    ResultUserBrief,
    CompetitionBrief,
    ClassSummary,
    DistanceSummary,
    SplitResponse,
    SplitDetailResponse,
    RecalculateResponse,
    ImportResponse,
    ImportResultItem,
    LinkWorkoutRequest,
    LinkWorkoutResponse,
    ClubBrief,
)

result_router = APIRouter(tags=['results'])


def parse_time_to_ms(value: str) -> int:
    """Parse a time string to milliseconds.

    Accepts:
      - Raw integer (ms):   "2415300"
      - MM:SS:              "40:15"
      - MM:SS.s:            "40:15.3"  (tenths/hundredths/ms)
      - HH:MM:SS:           "1:40:15"
      - HH:MM:SS.s:         "1:40:15.35"
    """
    value = value.strip()

    # Raw integer — treat as milliseconds
    try:
        return int(value)
    except ValueError:
        pass

    # [H:]MM:SS[.frac]
    m = re.fullmatch(r'(?:(\d+):)?(\d{1,2}):(\d{2})(?:\.(\d+))?', value)
    if not m:
        raise ValueError(f'Cannot parse time: {value!r}')

    hours = int(m.group(1) or 0)
    minutes = int(m.group(2))
    seconds = int(m.group(3))
    frac = m.group(4) or '0'

    # Normalise fraction to milliseconds (pad or truncate to 3 digits)
    frac_ms = int(frac[:3].ljust(3, '0'))

    return (hours * 3600 + minutes * 60 + seconds) * 1000 + frac_ms


def trigger_total_recalculation(db: Session, competition_id: int) -> None:
    """Find auto_calculate total configs and recalculate them."""
    from ..event.total_calculator import get_total_configs_for_competition, recalculate_total
    configs = get_total_configs_for_competition(db, competition_id)
    for config in configs:
        recalculate_total(db, config)


# ===== Helper Functions =====

def get_competition_or_404(db: Session, competition_id: int):
    competition = get_competition(db, competition_id)
    if not competition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Competition not found'
        )
    return competition


def get_result_or_404(db: Session, result_id: int):
    result = result_crud.get_result(db, result_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Result not found'
        )
    return result


def build_user_brief(db: Session, user: User) -> ResultUserBrief:
    # Get user's club (if any)
    club = None
    user_club = club_crud.get_user_active_club(db, user.id)
    if user_club:
        club = ClubBrief(id=user_club.id, name=user_club.name)
    return ResultUserBrief(
        id=user.id,
        username_display=user.username_display,
        first_name=user.first_name,
        last_name=user.last_name,
        club=club,
    )


def get_bib_number(db: Session, user_id: int, competition_id: int) -> str | None:
    reg = get_registration_by_user(db, user_id, competition_id)
    return reg.bib_number if reg else None


def build_splits_response(splits) -> list[SplitResponse]:
    return [
        SplitResponse(
            control_point=s.control_point,
            sequence=s.sequence,
            cumulative_time=s.cumulative_time,
            split_time=s.split_time,
        )
        for s in sorted(splits, key=lambda x: x.sequence)
    ]


# ===== 11.1 Create Result =====

@result_router.post('/api/competitions/{competition_id}/results', response_model=ResultResponse, status_code=status.HTTP_201_CREATED)
async def create_result(
    competition_id: int,
    data: ResultCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a result for a competition."""
    competition = get_competition_or_404(db, competition_id)

    # Check permissions
    if not result_crud.can_manage_results(db, current_user.id, competition.event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only organizer, secretary, or judge can create results'
        )

    # Check if user has registration
    registration = get_registration_by_user(db, data.user_id, competition_id)
    if not registration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='User not registered for this competition'
        )

    # Check if result already exists
    existing = result_crud.get_result_by_user(db, data.user_id, competition_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Result already exists for this user'
        )

    # Validate start time based on start format
    from ..enums.start_format import StartFormat
    if competition.start_format == StartFormat.SEPARATED_START:
        if not registration.start_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Cannot create result: athlete has no start time assigned'
            )
    elif competition.start_format == StartFormat.MASS_START:
        if not competition.start_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Cannot create result: competition start time is not set'
            )

    # Validate class against distances
    from ..competition import distance_crud
    distance = None
    if data.competition_class:
        all_classes = distance_crud.get_all_classes_for_competition(db, competition_id)
        if all_classes and data.competition_class not in all_classes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Invalid class. Available: {", ".join(all_classes)}'
            )
        distance = distance_crud.get_distance_by_class(db, competition_id, data.competition_class)

    # Validate splits against distance control points
    if data.splits and distance and distance.control_points:
        expected_codes = [cp.code for cp in distance.control_points]
        split_points = [s.control_point for s in data.splits]
        if split_points != expected_codes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Invalid control points. Expected: {", ".join(expected_codes)}'
            )

    # Auto-DSQ if time exceeds distance control time
    result_status = data.status
    if distance and distance.control_time and data.time_total and data.time_total > distance.control_time:
        from ..enums.result_status import ResultStatus
        result_status = ResultStatus.DSQ

    # Create result
    result = result_crud.create_result(
        db,
        user_id=data.user_id,
        competition_id=competition_id,
        competition_class=data.competition_class,
        time_total=data.time_total,
        status=result_status,
        distance_id=distance.id if distance else None,
    )

    # Create splits
    if data.splits:
        splits_data = [{'control_point': s.control_point, 'cumulative_time': s.cumulative_time} for s in data.splits]
        result_crud.create_splits(db, result.id, splits_data, distance=distance)
        db.refresh(result)

    # Recalculate positions
    if data.competition_class:
        result_crud.recalculate_class_positions(db, competition_id, data.competition_class)
    result_crud.recalculate_positions(db, competition_id)
    trigger_total_recalculation(db, competition_id)
    db.refresh(result)

    return ResultResponse(
        id=result.id,
        user_id=result.user_id,
        competition_id=result.competition_id,
        distance_id=result.distance_id,
        workout_id=result.workout_id,
        bib_number=registration.bib_number,
        competition_class=result.class_,
        position=result.position,
        position_overall=result.position_overall,
        time_total=result.time_total,
        time_behind_leader=result.time_behind_leader,
        status=result.status,
        splits=build_splits_response(result.splits) if result.splits else None,
        created_at=result.created_at,
    )


# ===== 11.2 List Results (Leaderboard) =====

@result_router.get('/api/competitions/{competition_id}/results', response_model=ResultsListResponse)
async def list_results(
    competition_id: int,
    competition_class: str | None = Query(None, alias='class'),
    distance_id: int | None = Query(None),
    result_status: str | None = Query(None, alias='status'),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """List competition results (leaderboard)."""
    competition = get_competition_or_404(db, competition_id)

    # Parse status
    status_filter = None
    if result_status:
        from ..enums.result_status import ResultStatus
        try:
            status_filter = ResultStatus(result_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Invalid status: {result_status}'
            )

    results, total = result_crud.get_results(
        db, competition_id,
        competition_class=competition_class,
        distance_id=distance_id,
        status=status_filter,
        limit=limit,
        offset=offset
    )

    # Build response items
    items = []
    for r in results:
        items.append(ResultListItem(
            id=r.id,
            user=build_user_brief(db, r.user),
            bib_number=get_bib_number(db, r.user_id, competition_id),
            distance_id=r.distance_id,
            distance_name=r.distance.name if r.distance else None,
            competition_class=r.class_,
            position_in_class=r.position,
            position_in_distance=r.position_in_distance,
            time_total=r.time_total,
            time_behind_leader=r.time_behind_leader,
            time_behind_distance_leader=r.time_behind_distance_leader,
            status=r.status,
            has_splits=len(r.splits) > 0 if r.splits else False,
        ))

    # Get summaries
    class_summaries = result_crud.get_class_summaries(db, competition_id)
    distance_summaries = result_crud.get_distance_summaries(db, competition_id)

    return ResultsListResponse(
        competition=CompetitionBrief(
            id=competition.id,
            name=competition.name,
            date=str(competition.date),
        ),
        results=items,
        classes=[
            ClassSummary(
                competition_class=s['class'],
                count=s['count'],
                leader_time=s['leader_time'],
            )
            for s in class_summaries
        ],
        distances=[
            DistanceSummary(
                distance_id=s['distance_id'],
                distance_name=s['distance_name'],
                count=s['count'],
                leader_time=s['leader_time'],
            )
            for s in distance_summaries
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


# ===== 11.4 Get My Result =====
# NOTE: This must be defined BEFORE the /{result_id} route to avoid "me" being captured as result_id

@result_router.get('/api/competitions/{competition_id}/results/me', response_model=ResultDetailResponse)
async def get_my_result(
    competition_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's result."""
    competition = get_competition_or_404(db, competition_id)

    result = result_crud.get_result_by_user(db, current_user.id, competition_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='No result found for this competition'
        )

    # Build splits with positions
    splits_response = []
    if result.splits and result.class_:
        for split in sorted(result.splits, key=lambda x: x.sequence):
            positions = result_crud.get_split_positions(
                db, competition_id, result.class_, split.control_point
            )
            pos_data = positions.get(result.id, (None, None))

            splits_response.append(SplitDetailResponse(
                control_point=split.control_point,
                sequence=split.sequence,
                cumulative_time=split.cumulative_time,
                split_time=split.split_time,
                position=pos_data[0],
                time_behind_best=pos_data[1],
            ))

    return ResultDetailResponse(
        id=result.id,
        user=build_user_brief(db, result.user),
        competition=CompetitionBrief(
            id=competition.id,
            name=competition.name,
            date=str(competition.date),
        ),
        workout_id=result.workout_id,
        bib_number=get_bib_number(db, result.user_id, competition_id),
        competition_class=result.class_,
        position=result.position,
        position_overall=result.position_overall,
        time_total=result.time_total,
        time_behind_leader=result.time_behind_leader,
        status=result.status,
        splits=splits_response if splits_response else None,
        created_at=result.created_at,
    )


# ===== 11.3 Get Result with Splits =====

@result_router.get('/api/competitions/{competition_id}/results/{result_id}', response_model=ResultDetailResponse)
async def get_result_detail(
    competition_id: int,
    result_id: int,
    db: Session = Depends(get_db)
):
    """Get result with splits."""
    competition = get_competition_or_404(db, competition_id)
    result = get_result_or_404(db, result_id)

    if result.competition_id != competition_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Result not found in this competition'
        )

    # Build splits with positions
    splits_response = []
    if result.splits and result.class_:
        for split in sorted(result.splits, key=lambda x: x.sequence):
            # Get position for this split
            positions = result_crud.get_split_positions(
                db, competition_id, result.class_, split.control_point
            )
            pos_data = positions.get(result.id, (None, None))

            splits_response.append(SplitDetailResponse(
                control_point=split.control_point,
                sequence=split.sequence,
                cumulative_time=split.cumulative_time,
                split_time=split.split_time,
                position=pos_data[0],
                time_behind_best=pos_data[1],
            ))

    return ResultDetailResponse(
        id=result.id,
        user=build_user_brief(db, result.user),
        competition=CompetitionBrief(
            id=competition.id,
            name=competition.name,
            date=str(competition.date),
        ),
        workout_id=result.workout_id,
        bib_number=get_bib_number(db, result.user_id, competition_id),
        competition_class=result.class_,
        position=result.position,
        position_overall=result.position_overall,
        time_total=result.time_total,
        time_behind_leader=result.time_behind_leader,
        status=result.status,
        splits=splits_response if splits_response else None,
        created_at=result.created_at,
    )


# ===== 11.5 Update Result =====

@result_router.patch('/api/competitions/{competition_id}/results/{result_id}', response_model=ResultResponse)
async def update_result(
    competition_id: int,
    result_id: int,
    data: ResultUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a result."""
    competition = get_competition_or_404(db, competition_id)

    # Check permissions
    if not result_crud.can_manage_results(db, current_user.id, competition.event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only organizer, secretary, or judge can update results'
        )

    result = get_result_or_404(db, result_id)
    if result.competition_id != competition_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Result not found in this competition'
        )

    # Validate class against distances
    from ..competition import distance_crud
    if data.competition_class:
        all_classes = distance_crud.get_all_classes_for_competition(db, competition_id)
        if all_classes and data.competition_class not in all_classes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Invalid class. Available: {", ".join(all_classes)}'
            )

    # Validate and replace splits
    if data.splits:
        effective_class = data.competition_class or result.class_
        distance = distance_crud.get_distance_by_class(db, competition_id, effective_class) if effective_class else None
        if distance and distance.control_points:
            expected_codes = [cp.code for cp in distance.control_points]
            split_points = [s.control_point for s in data.splits]
            if split_points != expected_codes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f'Invalid control points. Expected: {", ".join(expected_codes)}'
                )
        splits_data = [{'control_point': s.control_point, 'cumulative_time': s.cumulative_time} for s in data.splits]
        result_crud.replace_splits(db, result.id, splits_data, distance=distance)

    # Track if we need to recalculate
    old_class = result.class_
    needs_recalc = False

    # Auto-DSQ if updated time exceeds distance control time
    update_status = data.status
    if data.time_total is not None:
        effective_class = data.competition_class or result.class_
        dist = distance_crud.get_distance_by_class(db, competition_id, effective_class) if effective_class else None
        if dist and dist.control_time and data.time_total > dist.control_time:
            from ..enums.result_status import ResultStatus
            update_status = ResultStatus.DSQ

    # Update result
    if data.time_total is not None or update_status is not None or data.competition_class is not None:
        needs_recalc = True

    updated = result_crud.update_result(
        db, result,
        time_total=data.time_total,
        status=update_status,
        competition_class=data.competition_class,
    )

    # Recalculate positions if needed
    if needs_recalc:
        result_crud.recalculate_positions(db, competition_id)
        trigger_total_recalculation(db, competition_id)
        db.refresh(updated)

    return ResultResponse(
        id=updated.id,
        user_id=updated.user_id,
        competition_id=updated.competition_id,
        distance_id=updated.distance_id,
        workout_id=updated.workout_id,
        bib_number=get_bib_number(db, updated.user_id, competition_id),
        competition_class=updated.class_,
        position=updated.position,
        position_overall=updated.position_overall,
        time_total=updated.time_total,
        time_behind_leader=updated.time_behind_leader,
        status=updated.status,
        splits=build_splits_response(updated.splits) if updated.splits else None,
        created_at=updated.created_at,
    )


# ===== 11.6 Delete Result =====

@result_router.delete('/api/competitions/{competition_id}/results/{result_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_result(
    competition_id: int,
    result_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a result."""
    competition = get_competition_or_404(db, competition_id)

    # Check permissions (only organizer or secretary)
    if not result_crud.can_delete_results(db, current_user.id, competition.event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only organizer or secretary can delete results'
        )

    result = get_result_or_404(db, result_id)
    if result.competition_id != competition_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Result not found in this competition'
        )

    competition_class = result.class_
    result_crud.delete_result(db, result)

    # Recalculate positions
    result_crud.recalculate_positions(db, competition_id)
    trigger_total_recalculation(db, competition_id)

    return None


# ===== 11.7 Recalculate Positions =====

@result_router.post('/api/competitions/{competition_id}/results/recalculate', response_model=RecalculateResponse)
async def recalculate_positions(
    competition_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually recalculate positions for all results."""
    competition = get_competition_or_404(db, competition_id)

    # Check permissions
    if not result_crud.can_delete_results(db, current_user.id, competition.event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only organizer or secretary can recalculate positions'
        )

    results_count, classes_count = result_crud.recalculate_positions(db, competition_id)
    trigger_total_recalculation(db, competition_id)

    return RecalculateResponse(
        recalculated=True,
        results_count=results_count,
        classes_count=classes_count,
    )


# ===== 11.8 Batch Import Results =====

@result_router.post('/api/competitions/{competition_id}/results/import', response_model=ImportResponse)
async def import_results(
    competition_id: int,
    file: Annotated[UploadFile, File()],
    format: Annotated[str, Form()] = 'csv',
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Batch import results from CSV file."""
    competition = get_competition_or_404(db, competition_id)

    # Check permissions
    if not result_crud.can_delete_results(db, current_user.id, competition.event_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only organizer or secretary can import results'
        )

    if format != 'csv':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Only CSV format is supported'
        )

    # Read file
    content = await file.read()
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        text = content.decode('latin-1')

    # Parse CSV
    reader = csv.DictReader(io.StringIO(text))

    imported = 0
    updated = 0
    skipped = 0
    errors = []

    # Get control points from distances for split columns
    from ..competition import distance_crud
    all_distances = distance_crud.get_distances_by_competition(db, competition_id)

    # Build a map of class -> distance for resolving CPs
    class_to_distance = {}
    all_cp_codes = []
    for dist in all_distances:
        if dist.classes:
            for cls in dist.classes:
                class_to_distance[cls] = dist
        if dist.control_points:
            for cp in dist.control_points:
                if cp.code not in all_cp_codes:
                    all_cp_codes.append(cp.code)

    # Use all CP codes as split columns (for generic import)
    control_points = all_cp_codes

    for row_num, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
        bib_number = row.get('bib_number', '').strip()
        if not bib_number:
            skipped += 1
            continue

        # Find registration by bib number
        from ..competition.competition_registration_model import CompetitionRegistration
        registration = db.query(CompetitionRegistration).filter(
            CompetitionRegistration.competition_id == competition_id,
            CompetitionRegistration.bib_number == bib_number
        ).first()

        if not registration:
            errors.append(ImportResultItem(
                row=row_num,
                bib_number=bib_number,
                error='Registration not found'
            ))
            continue

        # Parse time and status
        time_total = None
        if row.get('time_total'):
            try:
                time_total = parse_time_to_ms(row['time_total'])
            except ValueError:
                errors.append(ImportResultItem(
                    row=row_num,
                    bib_number=bib_number,
                    error='Invalid time_total — use ms integer or MM:SS[.s] / HH:MM:SS[.s]'
                ))
                continue

        from ..enums.result_status import ResultStatus
        status_str = row.get('status', 'ok').lower()
        try:
            result_status = ResultStatus(status_str)
        except ValueError:
            result_status = ResultStatus.OK

        # Parse splits
        splits_data = []
        for i, cp in enumerate(control_points):
            col = f'split_{cp}'
            if col in row and row[col]:
                try:
                    cumulative = parse_time_to_ms(row[col])
                    splits_data.append({
                        'control_point': cp,
                        'cumulative_time': cumulative
                    })
                except ValueError:
                    pass  # Skip unparseable split value

        # Resolve distance for this registration's class
        reg_distance = class_to_distance.get(registration.class_) if registration.class_ else None

        # Auto-DSQ if time exceeds distance control time
        if reg_distance and reg_distance.control_time and time_total and time_total > reg_distance.control_time:
            from ..enums.result_status import ResultStatus
            result_status = ResultStatus.DSQ

        # Create or update result
        existing = result_crud.get_result_by_user(db, registration.user_id, competition_id)
        if existing:
            result_crud.update_result(
                db, existing,
                time_total=time_total,
                status=result_status,
                competition_class=registration.class_,
            )
            if splits_data:
                result_crud.replace_splits(db, existing.id, splits_data, distance=reg_distance)
            updated += 1
        else:
            result = result_crud.create_result(
                db,
                user_id=registration.user_id,
                competition_id=competition_id,
                competition_class=registration.class_,
                time_total=time_total,
                status=result_status,
                distance_id=reg_distance.id if reg_distance else None,
            )
            if splits_data:
                result_crud.create_splits(db, result.id, splits_data, distance=reg_distance)
            imported += 1

    # Recalculate positions after import
    result_crud.recalculate_positions(db, competition_id)
    trigger_total_recalculation(db, competition_id)

    return ImportResponse(
        imported=imported,
        updated=updated,
        skipped=skipped,
        errors=errors,
    )


# ===== 11.9 Link Workout to Result =====

@result_router.patch('/api/results/{result_id}/link-workout', response_model=LinkWorkoutResponse)
async def link_workout_to_result(
    result_id: int,
    data: LinkWorkoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Link a workout to a result."""
    result = get_result_or_404(db, result_id)
    competition = get_competition(db, result.competition_id)

    # Check permissions (result owner or organizer/secretary)
    is_owner = result.user_id == current_user.id
    is_manager = result_crud.can_manage_results(db, current_user.id, competition.event_id)

    if not is_owner and not is_manager:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only result owner or organizer can link workout'
        )

    # Get workout
    from ..workout.workout_crud import get_workout
    workout = get_workout(db, data.workout_id)
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Workout not found'
        )

    # Verify workout belongs to result's user
    if workout.user_id != result.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Workout does not belong to user'
        )

    # Verify date match (±1 day tolerance)
    from datetime import datetime
    workout_date = workout.start_datetime.date()
    comp_date = competition.date
    if abs((workout_date - comp_date).days) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Workout date does not match competition date (±1 day allowed)'
        )

    # Link workout
    result_crud.link_workout(db, result, data.workout_id)

    return LinkWorkoutResponse(
        id=result.id,
        workout_id=data.workout_id,
        message='Workout linked successfully',
    )
