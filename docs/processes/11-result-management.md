# 11. Result Management

| # | Endpoint | Method | Description |
|---|----------|--------|-------------|
| 11.1 | `/api/competitions/{competition_id}/results` | POST | Create result |
| 11.2 | `/api/competitions/{competition_id}/results` | GET | List results (leaderboard) |
| 11.3 | `/api/competitions/{competition_id}/results/{result_id}` | GET | Get result with splits |
| 11.4 | `/api/competitions/{competition_id}/results/me` | GET | Get my result |
| 11.5 | `/api/competitions/{competition_id}/results/{result_id}` | PATCH | Update result |
| 11.6 | `/api/competitions/{competition_id}/results/{result_id}` | DELETE | Delete result |
| 11.7 | `/api/competitions/{competition_id}/results/recalculate` | POST | Recalculate positions |
| 11.8 | `/api/competitions/{competition_id}/results/import` | POST | Batch import results |
| 11.9 | `/api/results/{result_id}/link-workout` | PATCH | Link workout to result |

## Result Concept

A **Result** records a participant's performance in a competition: time, position, and status.

### Result Status

| Status | Description |
|--------|-------------|
| `ok` | Finished normally |
| `dsq` | Disqualified |
| `dns` | Did not start |
| `dnf` | Did not finish |

### Splits Architecture

Results have their own splits (**ResultSplit**), separate from workout splits (**WorkoutSplit**):

| Entity | Linked to | Validation | Purpose |
|--------|-----------|------------|---------|
| **WorkoutSplit** | Workout | Free-form (from GPS file) | Training analysis |
| **ResultSplit** | Result | Must match `competition.control_points_list` | Competition analysis |

This separation allows:
- Competition analysis without linked workout
- Manual split entry by organizer
- Validation against official control points

---

## 11.1 Create Result

**Endpoint:** `POST /api/competitions/{competition_id}/results`

**Authorization:** Organizer, Secretary, or Judge

**Request:**
```json
{
  "user_id": 5,
  "class": "M21",
  "time_total": 3845,
  "status": "ok",
  "splits": [
    {"control_point": "31", "cumulative_time": 245},
    {"control_point": "45", "cumulative_time": 512},
    {"control_point": "78", "cumulative_time": 890},
    {"control_point": "finish", "cumulative_time": 3845}
  ]
}
```

**Flow:**
1. Verify user has CompetitionRegistration for this competition
2. Verify no existing Result for this user/competition
3. Validate class is in `competition.class_list`
4. Validate splits control_points match `competition.control_points_list`
5. Calculate `split_time` for each split (current - previous cumulative)
6. Create Result record
7. Create ResultSplit records
8. Recalculate positions for the class

**Response:** `201 Created`
```json
{
  "id": 1,
  "user_id": 5,
  "competition_id": 1,
  "workout_id": null,
  "class": "M21",
  "position": 3,
  "position_overall": 5,
  "time_total": 3845,
  "time_behind_leader": 120,
  "status": "ok",
  "splits": [
    {"control_point": "31", "sequence": 1, "cumulative_time": 245, "split_time": 245},
    {"control_point": "45", "sequence": 2, "cumulative_time": 512, "split_time": 267},
    {"control_point": "78", "sequence": 3, "cumulative_time": 890, "split_time": 378},
    {"control_point": "finish", "sequence": 4, "cumulative_time": 3845, "split_time": 2955}
  ],
  "created_at": "2024-06-15T14:30:00Z"
}
```

**Errors:**
- `400` - User not registered for this competition
- `400` - Result already exists for this user
- `400` - Invalid class
- `400` - Invalid control points (don't match competition)
- `403` - Insufficient permissions

## 11.2 List Results (Leaderboard)

**Endpoint:** `GET /api/competitions/{competition_id}/results`

**Authorization:** Public

**Query params:**
- `class` — filter by class (e.g., `M21`)
- `status` — filter by status (`ok`, `dsq`, `dns`, `dnf`)
- `club_id` — filter by club
- `gender` — filter by gender
- `sort_by` — `position` (default), `time_total`, `name`
- `order` — `asc` (default), `desc`
- `limit`, `offset` — pagination

**Priority logic (no class param):**
1. If user authenticated → user's class first, then others
2. If not authenticated → all classes sorted by position

**Response:** `200 OK`
```json
{
  "competition": {
    "id": 1,
    "name": "Day 1 - Long Distance",
    "date": "2024-06-15",
    "control_points_list": ["31", "45", "78", "finish"]
  },
  "results": [
    {
      "id": 1,
      "user": {
        "id": 5,
        "username_display": "ivan_petrov",
        "first_name": "Ivan",
        "last_name": "P.",
        "club": {"id": 1, "name": "Moscow Orienteers"}
      },
      "class": "M21",
      "position": 1,
      "time_total": 3725,
      "time_behind_leader": 0,
      "status": "ok",
      "has_splits": true
    },
    {
      "id": 2,
      "user": {
        "id": 8,
        "username_display": "petr_sidorov",
        "first_name": "Petr",
        "last_name": "S.",
        "club": null
      },
      "class": "M21",
      "position": 2,
      "time_total": 3800,
      "time_behind_leader": 75,
      "status": "ok",
      "has_splits": true
    }
  ],
  "classes": [
    {"class": "M21", "count": 25, "leader_time": 3725},
    {"class": "W21", "count": 18, "leader_time": 4120}
  ],
  "total": 85,
  "limit": 20,
  "offset": 0
}
```

## 11.3 Get Result with Splits

**Endpoint:** `GET /api/competitions/{competition_id}/results/{result_id}`

**Authorization:** Public

**Response:** `200 OK`
```json
{
  "id": 1,
  "user": {
    "id": 5,
    "username_display": "ivan_petrov",
    "first_name": "Ivan",
    "last_name": "Petrov",
    "club": {"id": 1, "name": "Moscow Orienteers"}
  },
  "competition": {
    "id": 1,
    "name": "Day 1 - Long Distance",
    "control_points_list": ["31", "45", "78", "finish"]
  },
  "workout_id": 123,
  "class": "M21",
  "position": 1,
  "position_overall": 1,
  "time_total": 3725,
  "time_behind_leader": 0,
  "status": "ok",
  "splits": [
    {
      "control_point": "31",
      "sequence": 1,
      "cumulative_time": 240,
      "split_time": 240,
      "position": 2,
      "time_behind_best": 15
    },
    {
      "control_point": "45",
      "sequence": 2,
      "cumulative_time": 500,
      "split_time": 260,
      "position": 1,
      "time_behind_best": 0
    },
    {
      "control_point": "78",
      "sequence": 3,
      "cumulative_time": 870,
      "split_time": 370,
      "position": 1,
      "time_behind_best": 0
    },
    {
      "control_point": "finish",
      "sequence": 4,
      "cumulative_time": 3725,
      "split_time": 2855,
      "position": 1,
      "time_behind_best": 0
    }
  ],
  "created_at": "2024-06-15T14:30:00Z"
}
```

**Note:** `position` and `time_behind_best` for each split are calculated dynamically by comparing with other results in the same class.

## 11.4 Get My Result

**Endpoint:** `GET /api/competitions/{competition_id}/results/me`

**Authorization:** Authenticated user

**Response:** `200 OK` (same format as 11.3)

**Response if no result:** `404 Not Found`

## 11.5 Update Result

**Endpoint:** `PATCH /api/competitions/{competition_id}/results/{result_id}`

**Authorization:** Organizer, Secretary, or Judge

**Request:**
```json
{
  "time_total": 3850,
  "status": "ok",
  "class": "M35",
  "splits": [
    {"control_point": "31", "cumulative_time": 250},
    {"control_point": "45", "cumulative_time": 520},
    {"control_point": "78", "cumulative_time": 900},
    {"control_point": "finish", "cumulative_time": 3850}
  ]
}
```

**Updatable fields:** `time_total`, `status`, `class`, `splits`

**Flow:**
1. Validate changes
2. If splits provided, replace all ResultSplit records
3. Update Result
4. If `time_total`, `status`, or `class` changed → recalculate positions

**Response:** `200 OK` (updated result object)

## 11.6 Delete Result

**Endpoint:** `DELETE /api/competitions/{competition_id}/results/{result_id}`

**Authorization:** Organizer or Secretary

**Deletion type:** **Hard delete with cascade**

**Cascade behavior:**
| Related Entity | Action |
|----------------|--------|
| ResultSplit | **Cascade delete** |

**Flow:**
1. Delete all ResultSplit records
2. Delete Result record
3. Recalculate positions for the class

**Response:** `204 No Content`

## 11.7 Recalculate Positions

**Endpoint:** `POST /api/competitions/{competition_id}/results/recalculate`

**Authorization:** Organizer or Secretary

**Description:** Manually trigger position recalculation for all results.

**Flow:**
```sql
-- For each class: calculate position
UPDATE results SET position = subq.pos
FROM (
  SELECT id, ROW_NUMBER() OVER (
    PARTITION BY class
    ORDER BY
      CASE WHEN status = 'ok' THEN 0 ELSE 1 END,
      time_total
  ) as pos
  FROM results
  WHERE competition_id = ?
) subq
WHERE results.id = subq.id;

-- Calculate position_overall (all classes combined)
UPDATE results SET position_overall = subq.pos
FROM (
  SELECT id, ROW_NUMBER() OVER (
    ORDER BY
      CASE WHEN status = 'ok' THEN 0 ELSE 1 END,
      time_total
  ) as pos
  FROM results
  WHERE competition_id = ?
) subq
WHERE results.id = subq.id;

-- Calculate time_behind_leader per class
UPDATE results r SET time_behind_leader = r.time_total - leader.time_total
FROM (
  SELECT class, MIN(time_total) as time_total
  FROM results
  WHERE competition_id = ? AND status = 'ok'
  GROUP BY class
) leader
WHERE r.class = leader.class AND r.competition_id = ?;
```

**Response:** `200 OK`
```json
{
  "recalculated": true,
  "results_count": 85,
  "classes_count": 4
}
```

## 11.8 Batch Import Results

**Endpoint:** `POST /api/competitions/{competition_id}/results/import`

**Authorization:** Organizer or Secretary

**Request:** `multipart/form-data`
```
file: <CSV or XML file>
format: "csv"
```

**CSV format:**
```csv
bib_number,time_total,status,split_31,split_45,split_78,split_finish
101,3725,ok,240,500,870,3725
102,3800,ok,225,490,860,3800
103,,dns,,,
```

**Flow:**
1. Parse file
2. Match `bib_number` to CompetitionRegistration
3. Validate all control points
4. Create/update Result records
5. Create ResultSplit records
6. Recalculate positions

**Response:** `200 OK`
```json
{
  "imported": 45,
  "updated": 5,
  "skipped": 2,
  "errors": [
    {"row": 15, "bib_number": "999", "error": "Registration not found"}
  ]
}
```

**Errors:**
- `400` - Invalid file format
- `400` - Missing required columns

## 11.9 Link Workout to Result

**Endpoint:** `PATCH /api/results/{result_id}/link-workout`

**Authorization:** Result owner (athlete) OR Organizer/Secretary

**Request:**
```json
{
  "workout_id": 123
}
```

**Flow:**
1. Verify workout belongs to result's user
2. Verify workout date matches competition date (±1 day tolerance)
3. Update `result.workout_id`

**Response:** `200 OK`
```json
{
  "id": 1,
  "workout_id": 123,
  "message": "Workout linked successfully"
}
```

**Errors:**
- `400` - Workout does not belong to user
- `400` - Workout date does not match competition date
- `403` - Not authorized (not owner and not organizer)

**Note:** Linking workout does NOT copy WorkoutSplits to ResultSplits. They remain separate for independent analysis.

---

## New Entity: ResultSplit

| # | Attribute | Type | Required | Description |
|---|-----------|------|----------|-------------|
| 1 | `id` | int | PK | |
| 2 | `result_id` | int | FK → Result | |
| 3 | `control_point` | string | yes | Must match competition.control_points_list |
| 4 | `sequence` | int | yes | Order (1, 2, 3...) |
| 5 | `cumulative_time` | int | yes | Seconds from start |
| 6 | `split_time` | int | yes | Seconds for this leg |

*Note: `position` and `time_behind_best` are calculated dynamically, not stored.*

---
