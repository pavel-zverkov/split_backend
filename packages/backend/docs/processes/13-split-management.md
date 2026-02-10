# 13. Split Management (WorkoutSplit)

| # | Endpoint | Method | Description |
|---|----------|--------|-------------|
| 13.1 | `/api/workouts/{workout_id}/splits` | GET | List workout splits |
| 13.2 | `/api/workouts/{workout_id}/splits` | POST | Manual split entry |
| 13.3 | `/api/workouts/{workout_id}/splits/{split_id}` | PATCH | Update single split |
| 13.4 | `/api/workouts/{workout_id}/splits` | DELETE | Delete all splits |

## Split Architecture

There are two separate split entities:

| Entity | Section | Purpose |
|--------|---------|---------|
| **WorkoutSplit** | This section (13) | Training analysis, free-form from GPS files |
| **ResultSplit** | Section 11 | Competition analysis, validated against control_points_list |

This section covers **WorkoutSplit** only. For ResultSplit, see [11. Result Management](./11-result-management.md).

---

## 13.0 Auto-Create Splits (on workout upload)

WorkoutSplits are created automatically during workout file parsing.

**Parser extracts:**
| File Type | Split Source |
|-----------|--------------|
| FIT | Lap records with timestamps |
| GPX | Waypoints marked as control points |
| TCX | Lap data |

**Note:** Auto-created splits are free-form and may not match competition control points.

---

## 13.1 List Workout Splits

**Endpoint:** `GET /api/workouts/{workout_id}/splits`

**Authorization:** Follows workout privacy

**Response:** `200 OK`
```json
{
  "workout_id": 5,
  "splits": [
    {
      "id": 1,
      "sequence": 1,
      "control_point": "31",
      "distance_meters": 1200,
      "cumulative_time": 150,
      "split_time": 150,
      "position": {"lat": 55.7558, "lng": 37.6173}
    },
    {
      "id": 2,
      "sequence": 2,
      "control_point": "45",
      "distance_meters": 2400,
      "cumulative_time": 312,
      "split_time": 162,
      "position": {"lat": 55.7560, "lng": 37.6180}
    }
  ],
  "total": 2
}
```

## 13.2 Manual Split Entry

**Endpoint:** `POST /api/workouts/{workout_id}/splits`

**Authorization:** Workout owner

**Request:**
```json
{
  "splits": [
    {
      "sequence": 1,
      "control_point": "31",
      "distance_meters": 1200,
      "cumulative_time": 150,
      "split_time": 150
    },
    {
      "sequence": 2,
      "control_point": "45",
      "distance_meters": 2400,
      "cumulative_time": 312,
      "split_time": 162
    }
  ]
}
```

**Flow:**
1. Delete all existing WorkoutSplits for this workout
2. Create new WorkoutSplit records
3. Return created splits

**Note:** This replaces all existing splits (PUT semantics).

**Response:** `201 Created`
```json
{
  "workout_id": 5,
  "splits": [
    {"id": 10, "sequence": 1, "control_point": "31", "cumulative_time": 150, "split_time": 150},
    {"id": 11, "sequence": 2, "control_point": "45", "cumulative_time": 312, "split_time": 162}
  ],
  "total": 2
}
```

## 13.3 Update Single Split

**Endpoint:** `PATCH /api/workouts/{workout_id}/splits/{split_id}`

**Authorization:** Workout owner

**Request:**
```json
{
  "control_point": "32",
  "cumulative_time": 155,
  "split_time": 155,
  "distance_meters": 1250
}
```

**Updatable fields:** `control_point`, `distance_meters`, `cumulative_time`, `split_time`, `position`

**Response:** `200 OK`
```json
{
  "id": 10,
  "sequence": 1,
  "control_point": "32",
  "distance_meters": 1250,
  "cumulative_time": 155,
  "split_time": 155,
  "position": null
}
```

## 13.4 Delete All Splits

**Endpoint:** `DELETE /api/workouts/{workout_id}/splits`

**Authorization:** Workout owner

**Deletion type:** **Hard delete** all WorkoutSplits for workout

**Response:** `204 No Content`

---
