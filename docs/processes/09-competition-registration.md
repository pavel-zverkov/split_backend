# 9. Competition Registration

| # | Endpoint | Method | Description |
|---|----------|--------|-------------|
| 9.1 | `/api/competitions/{competition_id}/register` | POST | Register for competition |
| 9.1b | `/api/competitions/{competition_id}/registrations` | POST | Add registration (organizer) |
| 9.2 | `/api/competitions/{competition_id}/registrations/me` | GET | Get my registration |
| 9.3 | `/api/competitions/{competition_id}/registrations` | GET | List registrations |
| 9.4 | `/api/competitions/{competition_id}/start-list` | GET | Get start list |
| 9.5 | `/api/competitions/{competition_id}/registrations/{registration_id}` | PATCH | Update registration |
| 9.6 | `/api/competitions/{competition_id}/registrations/batch` | POST | Batch assign bibs/start times |
| 9.7 | `/api/competitions/{competition_id}/registrations/me` | DELETE | Cancel my registration |
| 9.8 | `/api/competitions/{competition_id}/registrations/{registration_id}` | DELETE | Remove participant |

## Registration Concept

A **CompetitionRegistration** links a participant to a specific competition with class assignment, bib number, and start time.

### Registration Status

| Status | Description |
|--------|-------------|
| `pending` | Awaiting event approval |
| `registered` | Approved, awaiting bib/start_time |
| `confirmed` | Bib and start_time assigned |
| `rejected` | Rejected (visible to user) |

### Status Flow

```
pending ──► registered ──► confirmed
   │
   ▼
rejected ──► (can re-apply) ──► pending
```

**Status inheritance from EventParticipation:**

| EventParticipation.status | CompetitionRegistration.status |
|---------------------------|--------------------------------|
| `pending` | `pending` |
| `approved` | `registered` |

### Registration Blocking by Start Format

| start_format | Can register during `in_progress`? |
|--------------|-------------------------------------|
| `separated_start` | No |
| `mass_start` | No |
| `free` | Yes |

---

## 9.1 Register for Competition

**Endpoint:** `POST /api/competitions/{competition_id}/register`

**Authorization:** User with `approved` EventParticipation as `participant`

**Request:**
```json
{
  "class": "M21"
}
```

**Flow:**
1. Verify user has approved event participation
2. Verify competition allows registration:
   - `status=planned`, OR
   - `status=in_progress` AND `start_format=free`
3. Verify no existing registration (or previous was `rejected`)
4. Verify class is in `class_list`
5. Create CompetitionRegistration with `status=registered`
6. `bib_number` and `start_time` are null (set by organizer)

**Response:** `201 Created`
```json
{
  "id": 10,
  "user_id": 15,
  "competition_id": 1,
  "class": "M21",
  "bib_number": null,
  "start_time": null,
  "status": "registered",
  "created_at": "2024-01-20T10:00:00Z"
}
```

**Errors:**
- `400` - Already registered for this competition
- `400` - Invalid class (not in class_list)
- `400` - Registration closed (competition started with non-free format)
- `403` - No approved event participation
- `403` - Previous request rejected (can re-apply)

## 9.1b Add Registration (Organizer)

**Endpoint:** `POST /api/competitions/{competition_id}/registrations`

**Authorization:** Organizer or Secretary

**Purpose:** Add a registration for a user directly. Useful for adding ghost users.

**Request:**
```json
{
  "user_id": 15,
  "class": "M21",
  "bib_number": "101",
  "start_time": "2024-06-15T10:30:00Z"
}
```

**Flow:**
1. Verify caller is organizer or secretary
2. Verify target user exists
3. Verify user is not already registered
4. Validate class is in `class_list`
5. Validate bib_number is unique (if provided)
6. Create registration with `status=registered`

**Response:** `201 Created`
```json
{
  "id": 10,
  "user_id": 15,
  "competition_id": 1,
  "class": "M21",
  "bib_number": "101",
  "start_time": "2024-06-15T10:30:00Z",
  "status": "registered",
  "created_at": "2024-01-20T10:00:00Z"
}
```

**Errors:**
- `400` - User already registered for this competition
- `400` - Invalid class (not in class_list)
- `400` - Bib number already assigned
- `403` - Caller is not organizer or secretary
- `404` - Competition or user not found

## 9.2 Get My Registration

**Endpoint:** `GET /api/competitions/{competition_id}/registrations/me`

**Authorization:** Authenticated user

**Response:** `200 OK`
```json
{
  "id": 10,
  "competition_id": 1,
  "class": "M21",
  "bib_number": "142",
  "start_time": "2024-06-15T10:30:00Z",
  "status": "confirmed",
  "created_at": "2024-01-20T10:00:00Z"
}
```

**Response if not registered:** `404 Not Found`

## 9.3 List Registrations

**Endpoint:** `GET /api/competitions/{competition_id}/registrations`

**Authorization:** Optional (more details for organizer/secretary)

**Query params:**
- `class` — filter by class (e.g., `M21`)
- `status` — filter by status
- `limit`, `offset` — pagination

**Response:** `200 OK`
```json
{
  "registrations": [
    {
      "id": 10,
      "user": {
        "id": 15,
        "username_display": "ivan_petrov",
        "first_name": "Ivan",
        "last_name": "P.",
        "logo": "https://minio.../avatars/15.jpg"
      },
      "class": "M21",
      "bib_number": "142",
      "start_time": "2024-06-15T10:30:00Z",
      "status": "confirmed"
    }
  ],
  "total": 85,
  "limit": 20,
  "offset": 0
}
```

**Visibility:**
| Viewer | Can see |
|--------|---------|
| Anyone | `confirmed` registrations |
| Organizer/Secretary | All statuses |

## 9.4 Get Start List

**Endpoint:** `GET /api/competitions/{competition_id}/start-list`

**Authorization:** Public

**Query params:**
- `class` — filter by class
- `club_id` — filter by club
- `gender` — filter by gender (`male`, `female`)
- `sort_by` — `start_time` (default), `bib_number`, `class`
- `order` — `asc` (default), `desc`

**Priority logic (no class param):**
1. If user authenticated → user's class first, then others
2. If not authenticated → all sorted by `start_time`

**Response:** `200 OK`
```json
{
  "competition": {
    "id": 1,
    "name": "Day 1 - Long Distance",
    "date": "2024-06-15"
  },
  "start_list": [
    {
      "bib_number": "101",
      "start_time": "2024-06-15T10:00:00Z",
      "class": "M21",
      "user": {
        "id": 5,
        "username_display": "ivan_petrov",
        "first_name": "Ivan",
        "last_name": "P.",
        "club": {
          "id": 1,
          "name": "Moscow Orienteers"
        }
      }
    },
    {
      "bib_number": "102",
      "start_time": "2024-06-15T10:01:00Z",
      "class": "M21",
      "user": {
        "id": 8,
        "username_display": "petr_sidorov",
        "first_name": "Petr",
        "last_name": "S.",
        "club": null
      }
    }
  ],
  "classes": [
    {"class": "M21", "count": 25, "first_start": "2024-06-15T10:00:00Z"},
    {"class": "W21", "count": 18, "first_start": "2024-06-15T11:00:00Z"}
  ],
  "total": 85
}
```

## 9.5 Update Registration

**Endpoint:** `PATCH /api/competitions/{competition_id}/registrations/{registration_id}`

**Authorization:** Organizer or Secretary

**Request:**
```json
{
  "bib_number": "142",
  "start_time": "2024-06-15T10:30:00Z",
  "status": "confirmed",
  "class": "M35"
}
```

**Updatable fields:** `bib_number`, `start_time`, `status`, `class`

**Flow:**
1. Validate bib_number is unique within competition (if provided)
2. Validate start_time is within competition date (if provided)
3. Validate class is in `class_list` (if provided)
4. Update registration
5. Notify participant if bib/start_time assigned

**Response:** `200 OK` (updated registration object)

**Errors:**
- `400` - Bib number already assigned
- `400` - Invalid start time
- `400` - Invalid class

## 9.6 Batch Assign Bibs and Start Times

**Endpoint:** `POST /api/competitions/{competition_id}/registrations/batch`

**Authorization:** Organizer or Secretary

**Request:**
```json
{
  "registrations": [
    {"registration_id": 10, "bib_number": "101", "start_time": "2024-06-15T10:00:00Z"},
    {"registration_id": 11, "bib_number": "102", "start_time": "2024-06-15T10:01:00Z"},
    {"registration_id": 12, "bib_number": "103", "start_time": "2024-06-15T10:02:00Z"}
  ],
  "set_status": "confirmed"
}
```

**Flow:**
1. Validate all bib_numbers are unique within batch and competition
2. Validate all start_times are within competition date
3. Update all registrations
4. Optionally set status for all (default: `confirmed`)
5. Notify all affected participants

**Response:** `200 OK`
```json
{
  "updated": 3,
  "registrations": [
    {"registration_id": 10, "bib_number": "101", "status": "confirmed"},
    {"registration_id": 11, "bib_number": "102", "status": "confirmed"},
    {"registration_id": 12, "bib_number": "103", "status": "confirmed"}
  ]
}
```

**Errors:**
- `400` - Duplicate bib numbers in batch
- `400` - Invalid registration_id

## 9.7 Cancel My Registration

**Endpoint:** `DELETE /api/competitions/{competition_id}/registrations/me`

**Authorization:** Self

**Deletion type:** **Hard delete**

**Restrictions:**
- Cannot cancel if Result exists
- Cannot cancel if competition `status=in_progress` (except `start_format=free`)

**Flow:**
1. Check if Result exists → block if yes
2. Check competition status and start_format
3. Hard delete registration

**Response:** `204 No Content`

**Errors:**
- `400` - Cannot delete: result exists
- `400` - Cannot cancel: competition in progress

## 9.8 Remove Participant Registration

**Endpoint:** `DELETE /api/competitions/{competition_id}/registrations/{registration_id}`

**Authorization:** Organizer or Secretary

**Deletion type:** **Hard delete**

**Restrictions:**
- Cannot delete if Result exists

**Flow:**
1. Check if Result exists → block if yes
2. Hard delete registration
3. Notify participant: "Your registration for X has been cancelled"

**Response:** `204 No Content`

**Errors:**
- `400` - Cannot delete: result exists

---
