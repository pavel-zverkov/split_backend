# 8. Competition Management

| # | Endpoint | Method | Description |
|---|----------|--------|-------------|
| 8.1 | `/api/events/{event_id}/competitions` | POST | Create competition |
| 8.2 | `/api/events/{event_id}/competitions` | GET | List competitions |
| 8.3 | `/api/events/{event_id}/competitions/{competition_id}` | GET | Get competition details |
| 8.4 | `/api/events/{event_id}/competitions/{competition_id}` | PATCH | Update competition |
| 8.5 | `/api/events/{event_id}/competitions/{competition_id}` | DELETE | Delete competition |
| 8.6 | `/api/competitions/{competition_id}/team` | GET | List competition team |
| 8.7 | `/api/competitions/{competition_id}/team` | POST | Assign team member |
| 8.8 | `/api/competitions/{competition_id}/team/{user_id}` | DELETE | Remove from competition team |

## Competition Concept

A **Competition** is a single race/contest within an event. Events can have one or more competitions (e.g., Day 1 Sprint, Day 2 Long Distance).

### Competition Status

**Multi-stage events:** Competition status is **independent** of event status. Each competition has its own lifecycle, including registration control.

**Single-format events:** Competition status is **auto-synced** with event status (see [06. Event Management](./06-event-management.md#single-vs-multi-stage-events)). The status transitions and conditions below apply only to multi-stage event competitions.

| Status | Description |
|--------|-------------|
| `planned` | Upcoming, registration not open |
| `registration_open` | Athletes can self-register |
| `registration_closed` | Self-registration closed, team members can still register athletes |
| `in_progress` | Currently running |
| `finished` | Completed |
| `cancelled` | Cancelled |

**Status transitions:**
| From | Allowed To |
|------|------------|
| `planned` | `registration_open`, `cancelled` |
| `registration_open` | `registration_closed`, `in_progress`, `cancelled` |
| `registration_closed` | `registration_open`, `in_progress`, `cancelled` |
| `in_progress` | `finished`, `cancelled` |
| `finished` | — (terminal) |
| `cancelled` | — (terminal) |

**Additional transition conditions:**

| Transition | Condition |
|------------|-----------|
| → `in_progress` | `competition.start_time` must be set. Current date must be ≥ `competition.date`. For `separated_start`: all registered/confirmed athletes must have `bib_number` and `start_time` set. For `mass_start`: all registered/confirmed athletes must have `bib_number` set. For `free`: no start list requirements. |
| → `finished` | Current date must be > `competition.date` (cannot finish on competition day). All registered/confirmed athletes must have a Result record. |

**Example (multi-stage):** Event runs Feb 1-8 with daily competitions:
- Event status: `in_progress` (Feb 3)
- Feb 1 competition: `finished`
- Feb 3 competition: `in_progress`
- Feb 5 competition: `registration_open`

**Note (multi-stage):** When the parent event transitions to `finished`, all child competitions are auto-transitioned: `in_progress` → `finished`, others → `cancelled`.

### Control Points

Control points define the course/route checkpoints. Used for:
- **Orienteering:** Control codes (e.g., "31", "45", "78", "finish")
- **Running:** Distance markers (e.g., "1 km", "2 km", "5 km", "finish")
- **Other sports:** Any sequential checkpoints

### Team Assignment

By default, all event team members are assigned to all competitions. This can be overridden per competition.

---

## 8.1 Create Competition

**Endpoint:** `POST /api/events/{event_id}/competitions`

**Authorization:** Chief of: Organizer, Secretary, or Judge

**Request:**
```json
{
  "name": "Day 1 - Long Distance",
  "description": "Classic long distance race",
  "date": "2024-06-15",
  "start_format": "separated_start",
  "start_time": "2024-06-15T10:00:00",
  "class_list": ["M21", "M35", "W21", "W35"],
  "control_points_list": ["31", "45", "78", "92", "finish"],
  "distance_meters": 12500,
  "location": "Losiny Ostrov"
}
```

**Flow:**
1. Validate event exists and user is authorized
2. Validate competition date is in the future (date > now)
3. Create Competition with `status=planned`
4. Inherit `sport_kind` from Event if not specified
5. All event team members are auto-assigned to this competition

**Errors:**
- `400` - Competition date must be in the future
- `403` - Insufficient permissions

**Response:** `201 Created`
```json
{
  "id": 1,
  "event_id": 1,
  "name": "Day 1 - Long Distance",
  "description": "Classic long distance race",
  "date": "2024-06-15",
  "sport_kind": "orient",
  "start_format": "separated_start",
  "class_list": ["M21", "M35", "W21", "W35"],
  "control_points_list": ["31", "45", "78", "92", "finish"],
  "distance_meters": 12500,
  "location": "Losiny Ostrov",
  "status": "planned",
  "start_time": "2024-06-15T10:00:00",
  "registrations_count": 0,
  "created_at": "2024-01-15T10:00:00Z"
}
```

## 8.2 List Competitions

**Endpoint:** `GET /api/events/{event_id}/competitions`

**Authorization:** Optional

**Query params:**
- `status` — filter by status
- `date` — filter by date
- `limit`, `offset` — pagination

**Response:** `200 OK`
```json
{
  "competitions": [
    {
      "id": 1,
      "name": "Day 1 - Long Distance",
      "date": "2024-06-15",
      "sport_kind": "orient",
      "start_format": "separated_start",
      "distance_meters": 12500,
      "location": "Losiny Ostrov",
      "status": "planned",
      "start_time": "2024-06-15T10:00:00",
      "registrations_count": 85,
      "classes_count": 4
    }
  ],
  "total": 3,
  "limit": 20,
  "offset": 0
}
```

## 8.3 Get Competition Details

**Endpoint:** `GET /api/events/{event_id}/competitions/{competition_id}`

**Authorization:** Optional (authenticated for `my_registration` field)

**Response:** `200 OK`
```json
{
  "id": 1,
  "event_id": 1,
  "event": {
    "id": 1,
    "name": "Moscow Open 2024"
  },
  "name": "Day 1 - Long Distance",
  "description": "Classic long distance race",
  "date": "2024-06-15",
  "sport_kind": "orient",
  "start_format": "separated_start",
  "class_list": ["M21", "M35", "W21", "W35"],
  "control_points_list": ["31", "45", "78", "92", "finish"],
  "distance_meters": 12500,
  "location": "Losiny Ostrov",
  "status": "planned",
  "start_time": "2024-06-15T10:00:00",
  "registrations_count": 85,
  "team_count": 5,
  "my_registration": {
    "id": 10,
    "class": "M21",
    "bib_number": "101",
    "start_time": "2024-06-15T10:30:00Z",
    "status": "confirmed"
  },
  "created_at": "2024-01-15T10:00:00Z"
}
```

**`my_registration`:** Only included if current user is registered for this competition.

## 8.4 Update Competition

**Endpoint:** `PATCH /api/events/{event_id}/competitions/{competition_id}`

**Authorization:** Chief of: Organizer, Secretary, or Judge

**Request:**
```json
{
  "name": "Day 1 - Long Distance (Updated)",
  "status": "in_progress"
}
```

**Updatable fields:** `name`, `description`, `date`, `start_format`, `start_time`, `class_list`, `control_points_list`, `distance_meters`, `location`, `status`

**Restrictions:**
- Cannot modify `class_list` or `control_points_list` if Results exist

**Status transition rules:** See status transitions table above. Additional conditions apply for `→ in_progress` (date + start list readiness) and `→ finished` (date + all results present).

**Response:** `200 OK` (updated competition object)

## 8.5 Delete Competition

**Endpoint:** `DELETE /api/events/{event_id}/competitions/{competition_id}`

**Authorization:** Chief of: Organizer or Secretary

**Deletion type:** **Hard delete with cascade**

**Restriction:** Cannot delete if `status=in_progress`

**Cascade behavior:**
| Related Entity | Action |
|----------------|--------|
| CompetitionRegistration | **Cascade delete** |
| Result | **Cascade delete** |
| Artifact | **Cascade delete** + remove files from MinIO |
| SpectatorSession | **Set competition_id=null** |

**Flow:**
1. Check user is authorized
2. Check status is not `in_progress`
3. Notify registered participants: "Competition X has been cancelled/deleted"
4. Delete all related data
5. Return success

**Response:** `204 No Content`

**Errors:**
- `400` - Cannot delete competition in progress
- `403` - Insufficient permissions

## 8.6 List Competition Team

**Endpoint:** `GET /api/competitions/{competition_id}/team`

**Authorization:** Optional

**Query params:**
- `role` — filter by `organizer`, `secretary`, `judge`, `volunteer`
- `limit`, `offset` — pagination

**Response:** `200 OK`
```json
{
  "team": [
    {
      "user": {
        "id": 5,
        "username_display": "ivan_petrov",
        "first_name": "Ivan",
        "last_name": "P."
      },
      "role": "judge",
      "position": "chief",
      "inherited": true
    },
    {
      "user": {
        "id": 12,
        "username_display": "alex_volkov",
        "first_name": "Alex",
        "last_name": "V."
      },
      "role": "volunteer",
      "position": null,
      "inherited": false
    }
  ],
  "total": 5,
  "limit": 20,
  "offset": 0
}
```

**`inherited`:** `true` if assigned via event team, `false` if specifically assigned to this competition.

## 8.7 Assign Team Member to Competition

**Endpoint:** `POST /api/competitions/{competition_id}/team`

**Authorization:** Chief of: Organizer or Secretary

**Request:**
```json
{
  "user_id": 12,
  "role": "volunteer"
}
```

**Note:** User must be an event team member first (EventParticipation with team role).

**Flow:**
1. Verify user is event team member
2. Create CompetitionTeam record (overrides inheritance)
3. Return success

**Response:** `201 Created`
```json
{
  "user_id": 12,
  "competition_id": 1,
  "role": "volunteer",
  "position": null,
  "inherited": false
}
```

**Errors:**
- `400` - User is not an event team member
- `400` - User is already assigned to this competition

## 8.8 Remove from Competition Team

**Endpoint:** `DELETE /api/competitions/{competition_id}/team/{user_id}`

**Authorization:** Chief of: Organizer or Secretary

**Deletion type:** **Soft exclusion**

**Flow:**
- If user was specifically assigned (`inherited=false`): delete record
- If user was inherited (`inherited=true`): create exclusion record (user won't work on this competition)

**Response:** `204 No Content`

**Note:** To restore inherited assignment, use POST endpoint without role (re-inherit).

---

## New Entity: CompetitionTeam

| # | Attribute | Type | Required | Description |
|---|-----------|------|----------|-------------|
| 1 | `id` | int | PK | |
| 2 | `competition_id` | int | FK → Competition | |
| 3 | `user_id` | int | FK → User | |
| 4 | `role` | enum | yes | organizer/secretary/judge/volunteer |
| 5 | `excluded` | bool | yes | If true, user is excluded from this competition (default: false) |
| 6 | `created_at` | datetime | yes | |

**Note:** If no CompetitionTeam record exists for a user, they inherit from EventParticipation. If record exists with `excluded=true`, they don't work on this competition.

---

