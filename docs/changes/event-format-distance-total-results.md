# Plan: Event Format + Distance/ControlPoint + Event Total Results

## Context

Three interconnected features to improve event/competition UX and data model:

1. **Event Format** — distinguish single-competition events from multi-stage events. Single events auto-create a competition, simplifying the creation flow.
2. **Distance & ControlPoint** — extract `class_list`, `control_points_list`, `distance_meters` from Competition into proper entities. One competition can have many distances, each with its own classes and ordered control points.
3. **Event Total Results** — configurable aggregate results across competitions in multi-stage events, with flexible formula-based rules stored as JSONB.

**Implementation order:** Feature 1 → Feature 2 → Feature 3 (each depends on the previous being stable).

**Migration strategy:** Drop all existing migrations and DB data, recreate a single fresh initial migration with all new models.

---

## Feature 1: Event Format (`single` / `multi_stage`)

### New files
- `app/enums/event_format.py` — `EventFormat` enum: `SINGLE`, `MULTI_STAGE`

### Modified files

**`app/event/event_model.py`** — add column:
```python
event_format = Column(Enum(EventFormat), nullable=False, default=EventFormat.MULTI_STAGE)
```

**`app/event/event_schema.py`**:
- Add `SingleCompetitionCreate(BaseModel)`: `description`, `start_format`, `location` (inline comp data)
- Add `event_format` + optional `competition: SingleCompetitionCreate` to `EventCreate`
- Add `event_format: EventFormat` to `EventResponse`, `EventDetailResponse`, `EventListItem`
- Add `SingleEventCompetitionBrief` (id, start_format, distance_meters, registrations_count) to `EventListItem` as optional field

**`app/event/event_crud.py`**:
- `validate_event_for_planned(db, event)` — `single`: exactly 1 comp, `multi_stage`: ≥2 comps
- `sync_single_event_competition_status(db, event, old_status, new_status)` — auto-sync comp status on event status change for single events:
  - draft→planned: comp→registration_open
  - planned→in_progress: comp→in_progress
  - in_progress→finished: comp→finished
  - any→cancelled: comp→cancelled
- `get_single_event_competition(db, event_id)` — get the one competition

**`app/event/event_controller.py`**:
- `create_event`: if `event_format=SINGLE`, auto-create competition (name=event name, date=start_date, sport_kind=event sport_kind + inline fields)
- `update_event`: replace DRAFT→PLANNED guard with `validate_event_for_planned()`. After status change on single events, call `sync_single_event_competition_status()`
- All response builders: add `event_format` field
- `list_events`: add `competition_brief` for single events

**`app/competition/competition_contoller.py`**:
- `create_competition`: block if event is `SINGLE` format
- `delete_competition`: block if event is `SINGLE` format

---

## Feature 2: Distance & ControlPoint Entities

### New files
- `app/enums/control_point_type.py` — `ControlPointType` enum: `START`, `CONTROL`, `FINISH`
- `app/competition/distance_model.py` — `Distance` model: id, competition_id (FK CASCADE), name, distance_meters, climb_meters, classes (ARRAY), created_at. Relationships: competition, control_points (cascade), results
- `app/competition/control_point_model.py` — `ControlPoint` model: id, distance_id (FK CASCADE), code, sequence, type. Unique constraints: (distance_id, sequence), (distance_id, code)
- `app/competition/distance_schema.py` — schemas: ControlPointInput, DistanceCreate (with inline CPs), DistanceUpdate, ControlPointResponse, DistanceResponse, DistanceListItem, DistanceListResponse
- `app/competition/distance_crud.py` — CRUD: create_distance (with inline CPs), get_distance, get_distances_by_competition, update_distance, delete_distance, replace_control_points, `get_distance_by_class(db, competition_id, class_name)`, `get_all_classes_for_competition(db, competition_id)`
- `app/competition/distance_controller.py` — endpoints:
  - `POST /api/competitions/{id}/distances` — create with inline CPs
  - `GET /api/competitions/{id}/distances` — list
  - `GET /api/distances/{id}` — detail with CPs
  - `PATCH /api/distances/{id}` — update metadata
  - `DELETE /api/distances/{id}` — delete (cascade CPs)
  - `PUT /api/distances/{id}/control-points` — replace CP list

### Modified files

**`app/competition/competition_model.py`**:
- Remove columns: `class_list`, `control_points_list`, `distance_meters`
- Add relationship: `distances = relationship('Distance', back_populates='competition', cascade='all, delete-orphan')`

**`app/result/result_model.py`**:
- Add: `distance_id = Column(Integer, ForeignKey('distances.id'), nullable=True)`
- Add relationship: `distance = relationship('Distance')`

**`app/result/result_split_model.py`**:
- Replace `control_point` (String) with `control_point_id = Column(Integer, ForeignKey('control_points.id'), nullable=True)`
- Keep `sequence` (Integer)

**`app/competition/competition_schema.py`**:
- Remove `class_list`, `control_points_list`, `distance_meters` from create/update/response schemas
- Add `distances_count: int = 0` to response schemas

**`app/competition/competition_contoller.py`**:
- Remove references to removed columns in response building
- Add `distances_count` from `distance_crud`

**`app/competition/competition_crud.py`**:
- Remove `class_list`, `control_points_list`, `distance_meters` from `create_competition()`

**`app/competition/registration_controller.py`**:
- Replace `competition.class_list` validation with `distance_crud.get_all_classes_for_competition()`

**`app/result/result_controller.py`**:
- In `create_result()`: resolve distance by class via `distance_crud.get_distance_by_class()`, set `result.distance_id`, validate splits against distance's control points
- Same pattern in `update_result()` and `import_results()`
- Replace all `competition.control_points_list` references

**`app/result/result_crud.py`**:
- In `create_splits()`: accept optional distance to resolve `control_point_id` from CP code

**`app/result/result_schema.py`**:
- Add `distance_id: int | None = None` to result responses

**`app/split_comparer/split_comparer_entity.py`**:
- Fix bug: `control_point_list` → use distances relationship
- Rewrite `__compare_competition()` to get CPs from `competition.distances[].control_points`

**`app/database/tables.py`** — register `Distance`, `ControlPoint`

**`app/main.py`** — register `distance_router`

---

## Feature 3: Event Total Results

### New files
- `app/enums/total_result_status.py` — `TotalResultStatus` enum: `OK`, `INCOMPLETE`, `DSQ`
- `app/event/total_config_model.py` — `EventTotalConfig`: id, event_id (FK CASCADE), name, rules (JSONB), auto_calculate (bool, default true), created_at. Relationships: event, results (cascade)
- `app/event/total_result_model.py` — `EventTotalResult`: id, config_id (FK CASCADE), user_id (FK), class_, total_value (float), position, position_overall, stages_counted, stages_total, status (enum), calculated_at. Unique: (config_id, user_id, class_)
- `app/event/total_config_schema.py` — Pydantic schemas:
  - Rules sub-models: `TotalRulesSource` (competition_ids, classes), `TotalRulesScore` (type: time/position/formula, expression), `TotalRulesAggregation` (method: sum/min/max/avg, best_count, min_stages), `TotalRulesPenalties` (dsq/dns handling, penalty_value), `TotalRules` (source, score, aggregation, penalties, sort_order)
  - Request/response: TotalConfigCreate (name, rules, auto_calculate, preset), TotalConfigUpdate, TotalConfigResponse, TotalConfigListResponse
  - Result schemas: TotalResultItem, TotalResultsListResponse, StageBreakdownItem (from joins), TotalResultDetailResponse
- `app/event/formula_evaluator.py` — safe AST-based math evaluator. Whitelisted operators: `+`, `-`, `*`, `/`, `**`. Whitelisted functions: `max`, `min`, `round`, `abs`. Known variables: `time`, `leader_time`, `position`, `participants`, `max_time`
- `app/event/total_calculator.py` — calculation engine:
  - `recalculate_total(db, config)` — collect results from source competitions, calculate scores per stage, aggregate, assign positions, upsert EventTotalResult
  - `get_total_configs_for_competition(db, competition_id)` — find configs that include this competition
  - Hardcoded presets dict: `sum_time`, `sum_positions`, `best_n_time`, `iof_points`
- `app/event/total_config_crud.py` — CRUD for configs and results
- `app/event/total_config_controller.py` — endpoints:
  1. `POST /api/events/{event_id}/total-configs` — create (from preset or custom). Guard: only multi_stage events
  2. `GET /api/events/{event_id}/total-configs` — list
  3. `GET /api/events/{event_id}/total-configs/{config_id}` — get with rules
  4. `PATCH /api/events/{event_id}/total-configs/{config_id}` — update
  5. `DELETE /api/events/{event_id}/total-configs/{config_id}` — delete (cascade results)
  6. `POST /api/events/{event_id}/total-configs/{config_id}/recalculate` — manual trigger
  7. `GET /api/events/{event_id}/total-configs/{config_id}/results` — leaderboard (query: class, limit, offset)
  8. `GET /api/events/{event_id}/total-configs/{config_id}/results/me` — my total
  9. `GET /api/events/{event_id}/total-configs/{config_id}/results/{result_id}` — detail with per-stage breakdown (joined from Result table, NOT denormalized)

### Modified files

**`app/result/result_controller.py`**:
- Add `trigger_total_recalculation(db, competition_id)` helper — finds auto_calculate configs, calls `recalculate_total()`
- Call after: `create_result`, `update_result`, `delete_result`, `import_results`, `recalculate_positions`

**`app/database/tables.py`** — register `EventTotalConfig`, `EventTotalResult`

**`app/main.py`** — register `total_config_router`

---

## All new files (15)

| # | File | Feature |
|---|------|---------|
| 1 | `app/enums/event_format.py` | F1 |
| 2 | `app/enums/control_point_type.py` | F2 |
| 3 | `app/enums/total_result_status.py` | F3 |
| 4 | `app/competition/distance_model.py` | F2 |
| 5 | `app/competition/control_point_model.py` | F2 |
| 6 | `app/competition/distance_schema.py` | F2 |
| 7 | `app/competition/distance_crud.py` | F2 |
| 8 | `app/competition/distance_controller.py` | F2 |
| 9 | `app/event/total_config_model.py` | F3 |
| 10 | `app/event/total_result_model.py` | F3 |
| 11 | `app/event/total_config_schema.py` | F3 |
| 12 | `app/event/total_config_crud.py` | F3 |
| 13 | `app/event/total_config_controller.py` | F3 |
| 14 | `app/event/total_calculator.py` | F3 |
| 15 | `app/event/formula_evaluator.py` | F3 |

## All modified files (18)

| # | File | Features |
|---|------|----------|
| 1 | `app/event/event_model.py` | F1 |
| 2 | `app/event/event_schema.py` | F1 |
| 3 | `app/event/event_controller.py` | F1 |
| 4 | `app/event/event_crud.py` | F1 |
| 5 | `app/competition/competition_model.py` | F2 |
| 6 | `app/competition/competition_schema.py` | F2 |
| 7 | `app/competition/competition_contoller.py` | F1, F2 |
| 8 | `app/competition/competition_crud.py` | F2 |
| 9 | `app/competition/registration_controller.py` | F2 |
| 10 | `app/result/result_model.py` | F2 |
| 11 | `app/result/result_split_model.py` | F2 |
| 12 | `app/result/result_controller.py` | F2, F3 |
| 13 | `app/result/result_crud.py` | F2 |
| 14 | `app/result/result_schema.py` | F2 |
| 15 | `app/split_comparer/split_comparer_entity.py` | F2 |
| 16 | `app/database/tables.py` | F2, F3 |
| 17 | `app/main.py` | F2, F3 |
| 18 | `docs/` (entities.md, erd.md, process docs) | F1, F2, F3 |

## Verification

- **F1**: Create single event → verify competition auto-created. Try adding 2nd competition → 400. Update event status → verify competition syncs. Create multi_stage event → verify DRAFT→PLANNED blocked with <2 competitions.
- **F2**: Create distance with CPs → verify stored. Create result → verify distance_id auto-set. Import CSV → verify CP validation against distance. Split comparer → verify no crash.
- **F3**: Create total config with preset → verify rules filled. Create with custom formula → verify evaluation. Trigger recalculate → verify positions. Modify stage result → verify auto-recalculation. Detail endpoint → verify per-stage breakdown from joins.
- **Migration**: Delete all existing migrations in `migrations/versions/`, drop DB, run `poetry run alembic revision --autogenerate -m "initial"` then `poetry run alembic upgrade head`.
