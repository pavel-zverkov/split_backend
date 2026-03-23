from sqlalchemy.orm import Session, joinedload, selectinload
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
    distance_id: int | None = None,
) -> Result:
    result = Result(
        user_id=user_id,
        competition_id=competition_id,
        distance_id=distance_id,
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
    splits_data: list[dict],
    distance=None
) -> list[ResultSplit]:
    """Create splits for a result. Expects list of {control_point, cumulative_time}."""
    # Build CP code -> id map if distance provided
    cp_map = {}
    if distance and distance.control_points:
        cp_map = {cp.code: cp.id for cp in distance.control_points}

    splits = []
    prev_cumulative = 0

    for i, split_data in enumerate(splits_data, start=1):
        cumulative = split_data['cumulative_time']
        split_time = cumulative - prev_cumulative
        cp_code = split_data['control_point']

        split = ResultSplit(
            result_id=result_id,
            control_point=cp_code,
            control_point_id=cp_map.get(cp_code),
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
    splits_data: list[dict],
    distance=None
) -> list[ResultSplit]:
    """Replace all splits for a result."""
    delete_splits(db, result_id)
    return create_splits(db, result_id, splits_data, distance=distance)


def get_bulk_splits(
    db: Session,
    competition_id: int,
    competition_class: str | None = None,
    distance_id: int | None = None,
) -> tuple[list[Result], dict[int, list[ResultSplit]], dict[int, dict[int, dict]], list[str]]:
    """Get all results with splits for a competition in one pass.

    Returns:
        results: ordered list of Result objects
        splits_by_result: {result_id: [ResultSplit, ...]}
        positions_map: {result_id: {sequence: {position, time_behind_best, ...}}}
            Keyed by split sequence (int) so butterfly courses with duplicate CP codes
            are handled correctly.
        control_points_ordered: ordered list of CP codes (union across all athletes,
            preserving duplicates for butterfly courses)
    """
    from collections import defaultdict

    q = db.query(Result).options(
        joinedload(Result.user),
    ).filter(Result.competition_id == competition_id)
    if competition_class:
        q = q.filter(Result.class_ == competition_class)
    if distance_id:
        q = q.filter(Result.distance_id == distance_id)
    results = q.order_by(Result.position.asc().nullslast()).all()

    if not results:
        return [], {}, {}, []

    result_ids = [r.id for r in results]
    result_map = {r.id: r for r in results}

    all_splits = db.query(ResultSplit).filter(
        ResultSplit.result_id.in_(result_ids)
    ).order_by(ResultSplit.result_id, ResultSplit.sequence).all()

    splits_by_result: dict[int, list] = defaultdict(list)
    for split in all_splits:
        splits_by_result[split.result_id].append(split)

    # Group by (class, control_point, sequence) and (distance_id, control_point, sequence).
    # Including sequence in the key correctly separates butterfly visits to the same CP.
    cp_class_data: dict[tuple, list] = defaultdict(list)
    cp_dist_data: dict[tuple, list] = defaultdict(list)
    for split in all_splits:
        result = result_map[split.result_id]
        if result.status == ResultStatus.OK:
            entry = (split.result_id, split.split_time, split.cumulative_time)
            cp_class_data[(result.class_, split.control_point, split.sequence)].append(entry)
            if result.distance_id is not None:
                cp_dist_data[(result.distance_id, split.control_point, split.sequence)].append(entry)

    # positions_map keyed by sequence (not control_point) to support butterfly courses
    positions_map: dict[int, dict[int, dict]] = defaultdict(dict)

    for (cls, cp, seq), entries in cp_class_data.items():
        by_split = sorted(entries, key=lambda x: x[1])
        best_split = by_split[0][1]
        for i, (rid, st, _) in enumerate(by_split, 1):
            positions_map[rid].setdefault(seq, {})
            positions_map[rid][seq]['position'] = i
            positions_map[rid][seq]['time_behind_best'] = st - best_split

        by_cum = sorted(entries, key=lambda x: x[2])
        best_cum = by_cum[0][2]
        for i, (rid, _, ct) in enumerate(by_cum, 1):
            positions_map[rid].setdefault(seq, {})
            positions_map[rid][seq]['cumulative_position'] = i
            positions_map[rid][seq]['cumulative_time_behind_best'] = ct - best_cum

    for (dist_id, cp, seq), entries in cp_dist_data.items():
        by_split = sorted(entries, key=lambda x: x[1])
        best_split = by_split[0][1]
        for i, (rid, st, _) in enumerate(by_split, 1):
            positions_map[rid].setdefault(seq, {})
            positions_map[rid][seq]['position_in_distance'] = i
            positions_map[rid][seq]['time_behind_best_in_distance'] = st - best_split

        by_cum = sorted(entries, key=lambda x: x[2])
        best_cum = by_cum[0][2]
        for i, (rid, _, ct) in enumerate(by_cum, 1):
            positions_map[rid].setdefault(seq, {})
            positions_map[rid][seq]['cumulative_position_in_distance'] = i
            positions_map[rid][seq]['cumulative_time_behind_best_in_distance'] = ct - best_cum

    # Build ordered CP list preserving duplicate codes for butterfly courses.
    # Deduplicate by (sequence, cp) so we get one entry per CP visit, in order.
    seen_seq_cp: set[tuple] = set()
    cps_ordered: list[str] = []
    for split in sorted(all_splits, key=lambda s: s.sequence):
        key = (split.sequence, split.control_point)
        if key not in seen_seq_cp:
            cps_ordered.append(split.control_point)
            seen_seq_cp.add(key)

    return results, dict(splits_by_result), dict(positions_map), cps_ordered


# ===== Athlete Index =====

def get_athlete_index(db: Session, competition_id: int) -> list[dict]:
    """Minimal athlete list for cross-distance search. One query, no splits."""
    from ..competition.competition_registration_model import CompetitionRegistration
    from ..competition.distance_model import Distance
    from ..user.user_model import User

    rows = (
        db.query(
            Result.id,
            User.first_name,
            User.last_name,
            CompetitionRegistration.bib_number,
            Result.class_,
            Result.distance_id,
            Distance.name.label('distance_name'),
        )
        .join(User, User.id == Result.user_id)
        .outerjoin(
            CompetitionRegistration,
            (CompetitionRegistration.user_id == Result.user_id) &
            (CompetitionRegistration.competition_id == Result.competition_id),
        )
        .outerjoin(Distance, Distance.id == Result.distance_id)
        .filter(Result.competition_id == competition_id)
        .order_by(Result.id)
        .all()
    )

    return [
        {
            'result_id': r[0],
            'first_name': r[1],
            'last_name': r[2],
            'bib_number': r[3],
            'class': r[4],
            'distance_id': r[5],
            'distance_name': r[6],
        }
        for r in rows
    ]


# ===== Queries =====

def get_results(
    db: Session,
    competition_id: int,
    competition_class: str | None = None,
    distance_id: int | None = None,
    status: ResultStatus | None = None,
    limit: int = 20,
    offset: int = 0
) -> tuple[list[Result], int]:
    q = db.query(Result).options(
        joinedload(Result.user),
        joinedload(Result.distance),
        selectinload(Result.splits),
    ).filter(Result.competition_id == competition_id)

    if competition_class:
        q = q.filter(Result.class_ == competition_class)
    if distance_id:
        q = q.filter(Result.distance_id == distance_id)
    if status:
        q = q.filter(Result.status == status)

    total = q.count()
    if distance_id and not competition_class:
        order = Result.position_in_distance.asc().nullslast()
    elif competition_class:
        order = Result.position.asc().nullslast()
    else:
        order = Result.position_in_distance.asc().nullslast()
    results = q.order_by(order).offset(offset).limit(limit).all()
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


def get_distance_summaries(db: Session, competition_id: int) -> list[dict]:
    """Get distance summaries with counts and leader times."""
    from ..competition.distance_model import Distance

    rows = db.query(
        Result.distance_id,
        Distance.name,
        func.count(Result.id).label('count'),
        func.min(Result.time_total).filter(Result.status == ResultStatus.OK).label('leader_time')
    ).join(Distance, Result.distance_id == Distance.id).filter(
        Result.competition_id == competition_id,
        Result.distance_id.isnot(None),
    ).group_by(
        Result.distance_id,
        Distance.name,
    ).all()

    return [
        {
            'distance_id': r[0],
            'distance_name': r[1],
            'count': r[2],
            'leader_time': r[3],
        }
        for r in rows
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

    # Calculate distance positions and time_behind_distance_leader
    from collections import defaultdict
    dist_groups: dict[int, list] = defaultdict(list)
    for result in results:
        if result.distance_id is not None:
            dist_groups[result.distance_id].append(result)
        else:
            result.position_in_distance = None
            result.time_behind_distance_leader = None

    for dist_results in dist_groups.values():
        dist_sorted = sorted(
            dist_results,
            key=lambda r: (r.status != ResultStatus.OK, r.time_total or float('inf'))
        )
        dist_leader_time = None
        for i, result in enumerate(dist_sorted, start=1):
            result.position_in_distance = i
            if result.status == ResultStatus.OK and result.time_total:
                if dist_leader_time is None:
                    dist_leader_time = result.time_total
                result.time_behind_distance_leader = result.time_total - dist_leader_time
            else:
                result.time_behind_distance_leader = None

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
    """Get position and time_behind_best for each result at a control point within a class.
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


def get_split_positions_by_distance(
    db: Session,
    competition_id: int,
    distance_id: int,
    control_point: str
) -> dict[int, tuple[int, int]]:
    """Get position and time_behind_best for each result at a control point within a distance.
    Returns {result_id: (position, time_behind_best)}
    """
    splits = db.query(
        ResultSplit.result_id,
        ResultSplit.split_time
    ).join(Result).filter(
        Result.competition_id == competition_id,
        Result.distance_id == distance_id,
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


def get_cumulative_positions(
    db: Session,
    competition_id: int,
    competition_class: str,
    control_point: str
) -> dict[int, tuple[int, int]]:
    """Get position and time_behind_best by cumulative_time at a control point within a class.
    Returns {result_id: (position, time_behind_best)}
    """
    splits = db.query(
        ResultSplit.result_id,
        ResultSplit.cumulative_time
    ).join(Result).filter(
        Result.competition_id == competition_id,
        Result.class_ == competition_class,
        Result.status == ResultStatus.OK,
        ResultSplit.control_point == control_point
    ).order_by(
        ResultSplit.cumulative_time.asc()
    ).all()

    if not splits:
        return {}

    best_time = splits[0][1]
    return {result_id: (i, cum - best_time) for i, (result_id, cum) in enumerate(splits, start=1)}


def get_cumulative_positions_by_distance(
    db: Session,
    competition_id: int,
    distance_id: int,
    control_point: str
) -> dict[int, tuple[int, int]]:
    """Get position and time_behind_best by cumulative_time at a control point within a distance.
    Returns {result_id: (position, time_behind_best)}
    """
    splits = db.query(
        ResultSplit.result_id,
        ResultSplit.cumulative_time
    ).join(Result).filter(
        Result.competition_id == competition_id,
        Result.distance_id == distance_id,
        Result.status == ResultStatus.OK,
        ResultSplit.control_point == control_point
    ).order_by(
        ResultSplit.cumulative_time.asc()
    ).all()

    if not splits:
        return {}

    best_time = splits[0][1]
    return {result_id: (i, cum - best_time) for i, (result_id, cum) in enumerate(splits, start=1)}


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
