from sqlalchemy.orm import Session
from sqlalchemy import func

from .result_model import Result
from .result_split_model import ResultSplit
from ..enums.result_status import ResultStatus
from ..enums.event_role import EventRole
from ..enums.participation_status import ParticipationStatus


def get_result(db: Session, result_id: int) -> Result | None:
    return db.query(Result).filter(Result.id == result_id).first()


def get_result_by_user(db: Session, user_id: int, competition_id: int) -> Result | None:
    return db.query(Result).filter(
        Result.user_id == user_id,
        Result.competition_id == competition_id
    ).first()


def create_result(
    db: Session,
    user_id: int,
    competition_id: int,
    competition_class: str | None = None,
    time_total: int | None = None,
    status: ResultStatus = ResultStatus.OK,
) -> Result:
    result = Result(
        user_id=user_id,
        competition_id=competition_id,
        class_=competition_class,
        time_total=time_total,
        status=status,
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


def update_result(
    db: Session,
    result: Result,
    time_total: int | None = None,
    status: ResultStatus | None = None,
    competition_class: str | None = None,
) -> Result:
    if time_total is not None:
        result.time_total = time_total
    if status is not None:
        result.status = status
    if competition_class is not None:
        result.class_ = competition_class
    db.commit()
    db.refresh(result)
    return result


def delete_result(db: Session, result: Result) -> None:
    db.delete(result)
    db.commit()


def link_workout(db: Session, result: Result, workout_id: int) -> Result:
    result.workout_id = workout_id
    db.commit()
    db.refresh(result)
    return result


# ===== Splits =====

def create_splits(
    db: Session,
    result_id: int,
    splits_data: list[dict]
) -> list[ResultSplit]:
    """Create splits for a result. Expects list of {control_point, cumulative_time}."""
    splits = []
    prev_cumulative = 0

    for i, split_data in enumerate(splits_data, start=1):
        cumulative = split_data['cumulative_time']
        split_time = cumulative - prev_cumulative

        split = ResultSplit(
            result_id=result_id,
            control_point=split_data['control_point'],
            sequence=i,
            cumulative_time=cumulative,
            split_time=split_time,
        )
        db.add(split)
        splits.append(split)
        prev_cumulative = cumulative

    db.commit()
    for s in splits:
        db.refresh(s)
    return splits


def delete_splits(db: Session, result_id: int) -> None:
    """Delete all splits for a result."""
    db.query(ResultSplit).filter(ResultSplit.result_id == result_id).delete()
    db.commit()


def replace_splits(
    db: Session,
    result_id: int,
    splits_data: list[dict]
) -> list[ResultSplit]:
    """Replace all splits for a result."""
    delete_splits(db, result_id)
    return create_splits(db, result_id, splits_data)


# ===== Queries =====

def get_results(
    db: Session,
    competition_id: int,
    competition_class: str | None = None,
    status: ResultStatus | None = None,
    limit: int = 20,
    offset: int = 0
) -> tuple[list[Result], int]:
    q = db.query(Result).filter(Result.competition_id == competition_id)

    if competition_class:
        q = q.filter(Result.class_ == competition_class)
    if status:
        q = q.filter(Result.status == status)

    total = q.count()
    results = q.order_by(Result.position.asc().nullslast()).offset(offset).limit(limit).all()
    return results, total


def get_class_summaries(db: Session, competition_id: int) -> list[dict]:
    """Get class summaries with counts and leader times."""
    results = db.query(
        Result.class_,
        func.count(Result.id).label('count'),
        func.min(Result.time_total).filter(Result.status == ResultStatus.OK).label('leader_time')
    ).filter(
        Result.competition_id == competition_id
    ).group_by(
        Result.class_
    ).all()

    return [
        {
            'class': r[0] or '',
            'count': r[1],
            'leader_time': r[2]
        }
        for r in results
    ]


# ===== Position Calculation =====

def recalculate_positions(db: Session, competition_id: int) -> tuple[int, int]:
    """Recalculate positions for all results in a competition. Returns (results_count, classes_count)."""
    # Get all results grouped by class
    results = db.query(Result).filter(
        Result.competition_id == competition_id
    ).order_by(
        Result.class_,
        # OK status first, then others
        Result.status != ResultStatus.OK,
        Result.time_total.asc().nullslast()
    ).all()

    if not results:
        return 0, 0

    # Calculate class positions
    class_leaders = {}
    class_positions = {}
    for result in results:
        cls = result.class_ or ''
        if cls not in class_positions:
            class_positions[cls] = 0
            class_leaders[cls] = None

        class_positions[cls] += 1
        result.position = class_positions[cls]

        # Track leader time for time_behind_leader
        if result.status == ResultStatus.OK and result.time_total:
            if class_leaders[cls] is None:
                class_leaders[cls] = result.time_total
            result.time_behind_leader = result.time_total - class_leaders[cls]
        else:
            result.time_behind_leader = None

    # Calculate overall positions
    all_sorted = sorted(
        results,
        key=lambda r: (r.status != ResultStatus.OK, r.time_total or float('inf'))
    )
    for i, result in enumerate(all_sorted, start=1):
        result.position_overall = i

    db.commit()

    return len(results), len(class_positions)


def recalculate_class_positions(db: Session, competition_id: int, competition_class: str) -> None:
    """Recalculate positions for a single class."""
    results = db.query(Result).filter(
        Result.competition_id == competition_id,
        Result.class_ == competition_class
    ).order_by(
        Result.status != ResultStatus.OK,
        Result.time_total.asc().nullslast()
    ).all()

    leader_time = None
    for i, result in enumerate(results, start=1):
        result.position = i
        if result.status == ResultStatus.OK and result.time_total:
            if leader_time is None:
                leader_time = result.time_total
            result.time_behind_leader = result.time_total - leader_time
        else:
            result.time_behind_leader = None

    db.commit()


# ===== Split Analysis =====

def get_split_positions(
    db: Session,
    competition_id: int,
    competition_class: str,
    control_point: str
) -> dict[int, tuple[int, int]]:
    """Get position and time_behind_best for each result at a control point.
    Returns {result_id: (position, time_behind_best)}
    """
    splits = db.query(
        ResultSplit.result_id,
        ResultSplit.split_time
    ).join(Result).filter(
        Result.competition_id == competition_id,
        Result.class_ == competition_class,
        Result.status == ResultStatus.OK,
        ResultSplit.control_point == control_point
    ).order_by(
        ResultSplit.split_time.asc()
    ).all()

    if not splits:
        return {}

    best_time = splits[0][1]
    positions = {}
    for i, (result_id, split_time) in enumerate(splits, start=1):
        positions[result_id] = (i, split_time - best_time)

    return positions


# ===== Permission Checks =====

def can_manage_results(db: Session, user_id: int, event_id: int) -> bool:
    """Check if user can manage results (organizer, secretary, or judge)."""
    from ..event.event_crud import get_participation

    participation = get_participation(db, user_id, event_id)
    if not participation or participation.status != ParticipationStatus.APPROVED:
        return False

    return participation.role in [EventRole.ORGANIZER, EventRole.SECRETARY, EventRole.JUDGE]


def can_delete_results(db: Session, user_id: int, event_id: int) -> bool:
    """Check if user can delete results (organizer or secretary only)."""
    from ..event.event_crud import get_participation

    participation = get_participation(db, user_id, event_id)
    if not participation or participation.status != ParticipationStatus.APPROVED:
        return False

    return participation.role in [EventRole.ORGANIZER, EventRole.SECRETARY]
