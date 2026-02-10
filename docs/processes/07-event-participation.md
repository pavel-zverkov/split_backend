# 7. Event Participation

| # | Endpoint | Method | Description |
|---|----------|--------|-------------|
| 7.1 | `/api/events/{event_id}/join` | POST | Join event (athlete or team) |
| 7.1b | `/api/events/{event_id}/participants` | POST | Add participant (organizer) |
| 7.2 | `/api/events/{event_id}/participants` | GET | List participants (athletes) |
| 7.3 | `/api/events/{event_id}/requests` | GET | List join requests |
| 7.4 | `/api/events/{event_id}/requests/{participation_id}` | PATCH | Approve/reject request |
| 7.5 | `/api/events/{event_id}/participation/me` | GET | Get my participation |
| 7.6 | `/api/events/{event_id}/participation/me` | DELETE | Leave event |
| 7.7 | `/api/events/{event_id}/recruitment` | PATCH | Update recruitment settings |
| 7.8 | `/api/events/{event_id}/invites` | POST | Generate invite link |
| 7.9 | `/api/events/{event_id}/invites` | GET | List active invites |
| 7.10 | `/api/events/{event_id}/invites/{invite_id}` | DELETE | Revoke invite |

## Participation Concept

Users can join events in different roles through different methods.

### Roles

| Role | Type | Can self-request | Description |
|------|------|------------------|-------------|
| `organizer` | Team | No | Only via transfer ownership |
| `secretary` | Team | Yes (if open) | Manage registrations |
| `judge` | Team | Yes (if open) | Officiate competitions |
| `volunteer` | Team | Yes (if open) | Help with event |
| `participant` | Athlete | Yes | Compete in competitions |
| `spectator` | Viewer | No | Auto-tracked via SpectatorSession |

### Three ways to join

| Method | Who initiates | Approval |
|--------|---------------|----------|
| **Added directly** | Organizer (section 6) | Auto-approved |
| **Self-request** | User | Depends on event privacy |
| **Invite link** | Organizer sends, user clicks | Auto-approved |

### Approval logic

| Event Privacy | Athlete | Team role |
|---------------|---------|-----------|
| `public` | Auto-approved | Pending (needs approval) |
| `by_request` | Pending | Pending |

### Competition assignment

| Competitions | Behavior |
|--------------|----------|
| 1 competition | Auto-assign to that competition |
| >1 competitions | User chooses, or assign to all if not chosen |

---

## 7.1 Join Event

**Endpoint:** `POST /api/events/{event_id}/join`

**Authorization:** Authenticated user

**Request (athlete - specific competitions):**
```json
{
  "role": "participant",
  "competition_ids": [1, 2]
}
```

**Request (athlete - all competitions):**
```json
{
  "role": "participant",
  "competition_ids": "all"
}
```

**Request (team role):**
```json
{
  "role": "judge",
  "competition_ids": [1]
}
```

**Request (via invite link):**
```json
{
  "token": "abc123"
}
```

**Flow:**

```mermaid
flowchart TD
    A[User joins event] --> B{Has invite token?}
    B -->|Yes| C[Validate token]
    C --> D[Auto-approved with token's role]

    B -->|No| E{Role type?}
    E -->|Athlete| F{Event privacy?}
    F -->|public| G[Status = approved]
    F -->|by_request| H[Status = pending]

    E -->|Team role| I{Role in needed_roles?}
    I -->|No| J[400 Error: Role not open]
    I -->|Yes| H

    G --> K{Competitions count?}
    H --> K
    D --> K

    K -->|1| L[Auto-assign to competition]
    K -->|>1| M{competition_ids provided?}
    M -->|Yes, specific| N[Assign to selected planned competitions]
    M -->|Yes, "all"| O[Assign to all planned competitions]
    M -->|No| O
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "user_id": 15,
  "event_id": 1,
  "role": "participant",
  "position": null,
  "status": "approved",
  "competitions": [
    {"id": 1, "name": "Day 1 - Sprint"},
    {"id": 2, "name": "Day 2 - Long"}
  ],
  "joined_at": "2024-01-20T10:00:00Z"
}
```

**Errors:**
- `400` - Already participating (with `approved` or `pending` status)
- `400` - Role not open for recruitment (team roles)
- `400` - Invalid invite token
- `400` - Event status does not allow registration (must be `registration_open` or `in_progress`)
- `400` - All selected competitions have already started

**Note:** Users with `rejected` status can re-apply by sending a new request.

**Registration rules:**
- Event must be in `registration_open` or `in_progress` status
- Can only register for competitions with status `planned` (not yet started)
- Can use `competition_ids: "all"` to register for all upcoming competitions

## 7.1b Add Participant (Organizer)

**Endpoint:** `POST /api/events/{event_id}/participants`

**Authorization:** Organizer only

**Purpose:** Add a user directly to the event. Useful for adding ghost users.

**Request:**
```json
{
  "user_id": 15,
  "role": "participant",
  "position": null
}
```

**Role values:** `secretary`, `judge`, `volunteer`, `participant` (cannot set `organizer` - use transfer ownership)

**Flow:**
1. Verify caller is organizer
2. Verify target user exists
3. Verify user is not already participating
4. Create participation with `status=approved` (immediate join)

**Response:** `201 Created`
```json
{
  "id": 1,
  "user_id": 15,
  "event_id": 1,
  "role": "participant",
  "position": null,
  "status": "approved",
  "joined_at": "2024-01-15T10:00:00Z",
  "created_at": "2024-01-15T10:00:00Z"
}
```

**Errors:**
- `400` - User already participating, or trying to set organizer role
- `403` - Caller is not organizer
- `404` - Event or user not found

## 7.2 List Participants

**Endpoint:** `GET /api/events/{event_id}/participants`

**Authorization:** Optional

**Query params:**
- `competition_id` — filter by competition
- `status` — filter by `approved`, `pending`, `rejected` (pending/rejected only for organizer/secretary)
- `club_id` — filter by club
- `gender` — filter by gender (`male`, `female`)
- `limit`, `offset` — pagination

**Response:** `200 OK`
```json
{
  "participants": [
    {
      "id": 1,
      "user": {
        "id": 15,
        "username_display": "ivan_petrov",
        "first_name": "Ivan",
        "last_name": "P.",
        "logo": "https://minio.../avatars/15.jpg"
      },
      "status": "approved",
      "competitions": [
        {"id": 1, "name": "Day 1 - Sprint"},
        {"id": 2, "name": "Day 2 - Long"}
      ],
      "joined_at": "2024-01-20T10:00:00Z"
    }
  ],
  "total": 120,
  "limit": 20,
  "offset": 0
}
```

**Visibility:**
| Viewer | Can see |
|--------|---------|
| Anyone | `approved` participants |
| Organizer/Chief | `approved` + `pending` participants |

## 7.3 List Requests

**Endpoint:** `GET /api/events/{event_id}/requests`

**Authorization:** Organizer (chief or deputy) or Secretary (chief)

**Query params:**
- `status` — filter by `pending` (default), `rejected`
- `role` — filter by role
- `limit`, `offset` — pagination

**Response:** `200 OK`
```json
{
  "requests": [
    {
      "id": 5,
      "user": {
        "id": 20,
        "username_display": "maria_smith",
        "first_name": "Maria",
        "last_name": "S."
      },
      "role": "judge",
      "competitions": [
        {"id": 1, "name": "Day 1 - Sprint"}
      ],
      "created_at": "2024-01-22T10:00:00Z"
    }
  ],
  "total": 3,
  "limit": 20,
  "offset": 0
}
```

## 7.4 Approve/Reject Request

**Endpoint:** `PATCH /api/events/{event_id}/requests/{participation_id}`

**Authorization:** Organizer (chief or deputy) or Secretary (chief)

**Request:**
```json
{
  "status": "approved"
}
```

**Status values:** `approved`, `rejected`

**Flow:**
- If `approved`: Set `joined_at=now()`, create CompetitionRegistration records, notify user "Your request to join X was approved"
- If `rejected`: Update status to `rejected`, notify user "Your request to join X was rejected"

**Rejection behavior** (different from follow/club systems):
| User | What they see |
|------|---------------|
| **Requester** | Status = `rejected` (visible), can send new request |
| **Organizer** | Record in rejected list |

**Note:** Rejected users can re-apply by sending a new join request.

**Response:** `200 OK`

## 7.5 Get My Participation

**Endpoint:** `GET /api/events/{event_id}/participation/me`

**Authorization:** Authenticated user

**Response:** `200 OK`
```json
{
  "id": 1,
  "event_id": 1,
  "role": "participant",
  "position": null,
  "status": "approved",
  "competitions": [
    {
      "id": 1,
      "name": "Day 1 - Sprint",
      "registration_id": 10,
      "class": "M21",
      "bib_number": "101",
      "start_time": "2024-06-15T10:30:00Z"
    }
  ],
  "joined_at": "2024-01-20T10:00:00Z"
}
```

**Response if not participating:** `404 Not Found`

## 7.6 Leave Event

**Endpoint:** `DELETE /api/events/{event_id}/participation/me`

**Authorization:** Authenticated user (self)

**Deletion type:** **Hard delete**

**Restrictions:**
- Cannot leave if user has Results in any of event's competitions
- Cannot leave if user is chief organizer (must transfer ownership first)

**Flow:**
1. Check restrictions
2. Delete EventParticipation record
3. Delete related CompetitionRegistration records
4. No notification

**Response:** `204 No Content`

**Errors:**
- `400` - Cannot leave: you have results in this event
- `400` - Cannot leave: transfer organizer role first

## 7.7 Update Recruitment Settings

**Endpoint:** `PATCH /api/events/{event_id}/recruitment`

**Authorization:** Organizer (chief or deputy)

**Request:**
```json
{
  "recruitment_open": true,
  "needed_roles": ["judge", "volunteer"]
}
```

**Fields:**
- `recruitment_open` — enable/disable self-registration for team roles
- `needed_roles` — array of roles open for recruitment (`secretary`, `judge`, `volunteer`)

**Response:** `200 OK`
```json
{
  "recruitment_open": true,
  "needed_roles": ["judge", "volunteer"]
}
```

**Note:** This affects only team roles. Athletes can always self-register (subject to event privacy).

## 7.8 Generate Invite Link

**Endpoint:** `POST /api/events/{event_id}/invites`

**Authorization:** Organizer (chief or deputy) or role's Chief

**Request:**
```json
{
  "role": "judge",
  "position": "deputy",
  "competition_ids": [1, 2],
  "expires_at": "2024-06-01T00:00:00Z",
  "max_uses": 1
}
```

**Fields:**
- `role` — role for invited user (required)
- `position` — position for team roles (optional, default: null)
- `competition_ids` — pre-selected competitions (optional)
- `expires_at` — expiration datetime (optional)
- `max_uses` — maximum number of uses (optional, default: 1)

**Flow:**
1. Generate unique token
2. Create invite record
3. Return invite link

**Response:** `201 Created`
```json
{
  "id": 1,
  "token": "abc123xyz",
  "role": "judge",
  "position": "deputy",
  "competition_ids": [1, 2],
  "expires_at": "2024-06-01T00:00:00Z",
  "max_uses": 1,
  "uses_count": 0,
  "link": "https://app.example.com/events/1/join?token=abc123xyz",
  "created_at": "2024-01-20T10:00:00Z"
}
```

## 7.9 List Active Invites

**Endpoint:** `GET /api/events/{event_id}/invites`

**Authorization:** Organizer (chief or deputy)

**Response:** `200 OK`
```json
{
  "invites": [
    {
      "id": 1,
      "token": "abc123xyz",
      "role": "judge",
      "position": "deputy",
      "competition_ids": [1, 2],
      "expires_at": "2024-06-01T00:00:00Z",
      "max_uses": 1,
      "uses_count": 0,
      "created_by": {
        "id": 5,
        "username_display": "ivan_petrov"
      },
      "created_at": "2024-01-20T10:00:00Z"
    }
  ],
  "total": 5
}
```

**Note:** Only shows active (not expired, not fully used) invites.

## 7.10 Revoke Invite

**Endpoint:** `DELETE /api/events/{event_id}/invites/{invite_id}`

**Authorization:** Organizer (chief or deputy) or invite creator

**Deletion type:** **Hard delete**

**Response:** `204 No Content`

---

## New Entity: EventInvite

| # | Attribute | Type | Required | Description |
|---|-----------|------|----------|-------------|
| 1 | `id` | int | PK | |
| 2 | `event_id` | int | FK → Event | |
| 3 | `token` | string | yes, unique | Invite token |
| 4 | `role` | enum | yes | Role for invited user |
| 5 | `position` | enum | no | Position for team roles |
| 6 | `competition_ids` | array | no | Pre-selected competitions |
| 7 | `expires_at` | datetime | no | Expiration |
| 8 | `max_uses` | int | no | Max uses (null = unlimited) |
| 9 | `uses_count` | int | yes | Current uses |
| 10 | `created_by` | int | FK → User | |
| 11 | `created_at` | datetime | yes | |

---

