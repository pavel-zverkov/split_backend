from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..enums.result_status import ResultStatus
from ..enums.total_result_status import TotalResultStatus
from ..result.result_model import Result
from .total_config_model import EventTotalConfig
from .total_result_model import EventTotalResult
from .formula_evaluator import evaluate_formula, FormulaError


# Hardcoded presets
PRESETS = {
    'sum_time': {
        'source': {},
        'score': {'type': 'time'},
        'aggregation': {'method': 'sum'},
        'penalties': {'dsq_handling': 'exclude', 'dns_handling': 'exclude'},
        'sort_order': 'asc',
    },
    'sum_positions': {
        'source': {},
        'score': {'type': 'position'},
        'aggregation': {'method': 'sum'},
        'penalties': {'dsq_handling': 'exclude', 'dns_handling': 'exclude'},
        'sort_order': 'asc',
    },
    'best_n_time': {
        'source': {},
        'score': {'type': 'time'},
        'aggregation': {'method': 'sum', 'best_count': 3},
        'penalties': {'dsq_handling': 'exclude', 'dns_handling': 'exclude'},
        'sort_order': 'asc',
    },
    'iof_points': {
        'source': {},
        'score': {'type': 'formula', 'expression': 'max(0, round(1000 * (leader_time / time)))'},
        'aggregation': {'method': 'sum'},
        'penalties': {'dsq_handling': 'exclude', 'dns_handling': 'exclude'},
        'sort_order': 'desc',
    },
}


def get_preset_rules(preset_name: str) -> dict | None:
    return PRESETS.get(preset_name)


def recalculate_total(db: Session, config: EventTotalConfig) -> int:
    """Recalculate total results for a config. Returns number of results."""
    rules = config.rules or {}
    source = rules.get('source', {})
    score_config = rules.get('score', {'type': 'time'})
    aggregation = rules.get('aggregation', {'method': 'sum'})
    penalties = rules.get('penalties', {})
    sort_order = rules.get('sort_order', 'asc')

    # Get source competitions
    from ..competition.competition_model import Competition
    comp_query = db.query(Competition).filter(Competition.event_id == config.event_id)
    if source.get('competition_ids'):
        comp_query = comp_query.filter(Competition.id.in_(source['competition_ids']))
    competitions = comp_query.order_by(Competition.date.asc()).all()

    if not competitions:
        return 0

    comp_ids = [c.id for c in competitions]
    stages_total = len(comp_ids)

    # Get all results for source competitions
    results_query = db.query(Result).filter(Result.competition_id.in_(comp_ids))
    source_classes = source.get('classes')
    if source_classes:
        results_query = results_query.filter(Result.class_.in_(source_classes))
    all_results = results_query.all()

    # Group results by (user_id, class)
    user_results: dict[tuple[int, str], list[Result]] = {}
    for r in all_results:
        key = (r.user_id, r.class_ or '')
        user_results.setdefault(key, []).append(r)

    # Compute leader times per competition+class for formula
    leader_times: dict[tuple[int, str], int] = {}
    max_times: dict[tuple[int, str], int] = {}
    participants_count: dict[tuple[int, str], int] = {}
    for r in all_results:
        key = (r.competition_id, r.class_ or '')
        if r.status == ResultStatus.OK and r.time_total:
            if key not in leader_times or r.time_total < leader_times[key]:
                leader_times[key] = r.time_total
            if key not in max_times or r.time_total > max_times[key]:
                max_times[key] = r.time_total
        participants_count[key] = participants_count.get(key, 0) + 1

    # Calculate scores and aggregate
    calculated: list[dict] = []
    for (user_id, cls), results in user_results.items():
        scores = []
        for result in results:
            score = _calculate_score(
                result, score_config, penalties,
                leader_times.get((result.competition_id, cls)),
                max_times.get((result.competition_id, cls)),
                participants_count.get((result.competition_id, cls), 0),
            )
            if score is not None:
                scores.append(score)

        stages_counted = len(scores)

        # Check min_stages
        min_stages = aggregation.get('min_stages')
        if min_stages and stages_counted < min_stages:
            status = TotalResultStatus.INCOMPLETE
        else:
            status = TotalResultStatus.OK

        # Apply best_count
        best_count = aggregation.get('best_count')
        if best_count and len(scores) > best_count:
            if sort_order == 'asc':
                scores.sort()
            else:
                scores.sort(reverse=True)
            scores = scores[:best_count]
            stages_counted = best_count

        # Aggregate
        total_value = _aggregate(scores, aggregation.get('method', 'sum'))

        calculated.append({
            'user_id': user_id,
            'class_': cls,
            'total_value': total_value,
            'stages_counted': stages_counted,
            'stages_total': stages_total,
            'status': status,
        })

    # Sort and assign positions
    reverse = sort_order == 'desc'
    ok_results = [c for c in calculated if c['status'] == TotalResultStatus.OK and c['total_value'] is not None]
    non_ok = [c for c in calculated if c not in ok_results]

    ok_results.sort(key=lambda x: x['total_value'], reverse=reverse)

    # Per-class positions
    class_positions: dict[str, int] = {}
    for c in ok_results:
        cls = c['class_']
        class_positions[cls] = class_positions.get(cls, 0) + 1
        c['position'] = class_positions[cls]

    # Overall positions
    for i, c in enumerate(ok_results, start=1):
        c['position_overall'] = i

    for c in non_ok:
        c['position'] = None
        c['position_overall'] = None

    # Upsert results
    db.query(EventTotalResult).filter(EventTotalResult.config_id == config.id).delete()

    now = datetime.now(timezone.utc)
    for c in ok_results + non_ok:
        total_result = EventTotalResult(
            config_id=config.id,
            user_id=c['user_id'],
            class_=c['class_'] or None,
            total_value=c['total_value'],
            position=c['position'],
            position_overall=c['position_overall'],
            stages_counted=c['stages_counted'],
            stages_total=c['stages_total'],
            status=c['status'],
            calculated_at=now,
        )
        db.add(total_result)

    db.commit()
    return len(ok_results) + len(non_ok)


def _calculate_score(
    result: Result,
    score_config: dict,
    penalties: dict,
    leader_time: int | None,
    max_time: int | None,
    participants: int,
) -> float | None:
    """Calculate score for a single stage result."""
    if result.status == ResultStatus.DSQ:
        handling = penalties.get('dsq_handling', 'exclude')
        if handling == 'exclude':
            return None
        elif handling == 'max_time' and max_time:
            return float(max_time)
        elif handling == 'penalty':
            return penalties.get('penalty_value', 0)
        return None

    if result.status == ResultStatus.DNS:
        handling = penalties.get('dns_handling', 'exclude')
        if handling == 'exclude':
            return None
        elif handling == 'max_time' and max_time:
            return float(max_time)
        elif handling == 'penalty':
            return penalties.get('penalty_value', 0)
        return None

    if result.status == ResultStatus.DNF:
        return None

    score_type = score_config.get('type', 'time')

    if score_type == 'time':
        return float(result.time_total) if result.time_total else None

    if score_type == 'position':
        return float(result.position) if result.position else None

    if score_type == 'formula':
        expression = score_config.get('expression')
        if not expression:
            return float(result.time_total) if result.time_total else None

        variables = {
            'time': float(result.time_total) if result.time_total else 0,
            'leader_time': float(leader_time) if leader_time else 0,
            'position': float(result.position) if result.position else 0,
            'participants': float(participants),
            'max_time': float(max_time) if max_time else 0,
        }
        try:
            return evaluate_formula(expression, variables)
        except FormulaError:
            return None

    return None


def _aggregate(scores: list[float], method: str) -> float | None:
    if not scores:
        return None

    if method == 'sum':
        return sum(scores)
    elif method == 'min':
        return min(scores)
    elif method == 'max':
        return max(scores)
    elif method == 'avg':
        return sum(scores) / len(scores)

    return sum(scores)


def get_total_configs_for_competition(db: Session, competition_id: int) -> list[EventTotalConfig]:
    """Find total configs that include (or could include) a competition."""
    from ..competition.competition_model import Competition

    competition = db.query(Competition).filter(Competition.id == competition_id).first()
    if not competition:
        return []

    configs = db.query(EventTotalConfig).filter(
        EventTotalConfig.event_id == competition.event_id,
        EventTotalConfig.auto_calculate.is_(True)
    ).all()

    matching = []
    for config in configs:
        rules = config.rules or {}
        source = rules.get('source', {})
        comp_ids = source.get('competition_ids')

        # If no specific comp_ids, includes all competitions
        if not comp_ids or competition_id in comp_ids:
            matching.append(config)

    return matching
