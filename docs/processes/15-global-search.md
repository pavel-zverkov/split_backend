# 15. Global Search

| # | Endpoint | Method | Description |
|---|----------|--------|-------------|
| 15.1 | `/api/search` | GET | Global search across all entity types |

## Search Concept

A single endpoint that searches across **users**, **events**, **clubs**, and **competitions** simultaneously. Results are grouped by type, each capped at a configurable limit.

### Visibility Rules

| Entity | Visible in search |
|--------|------------------|
| Users | `account_type=registered` + `is_active=true` only |
| Events | `privacy=public` only |
| Clubs | `privacy=public` only |
| Competitions | Parent event must be `privacy=public` |

Private entities never appear in search results regardless of auth state — search is a discovery feature.

---

## 15.1 Global Search

**Endpoint:** `GET /api/search`

**Authorization:** Public

**Query params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `q` | string | required | Search query (min 2 characters) |
| `limit` | int | `5` | Max results per type (1–20) |

**Search fields per type:**

| Type | Fields searched |
|------|----------------|
| Users | `username_display`, `first_name`, `last_name` |
| Events | `name`, `location` |
| Clubs | `name`, `location` |
| Competitions | `name`, `location` |

All searches use case-insensitive `ILIKE %q%` matching.

**Response:** `200 OK`
```json
{
  "query": "moscow",
  "users": [
    {
      "id": 5,
      "username_display": "ivan_petrov",
      "first_name": "Ivan",
      "last_name": "Petrov",
      "logo": "http://minio:9000/avatars/5/abc123.jpg",
      "account_type": "registered"
    }
  ],
  "events": [
    {
      "id": 3,
      "name": "Moscow Spring Cup",
      "start_date": "2024-05-10",
      "end_date": "2024-05-12",
      "location": "Moscow, Izmailovsky Park",
      "sport_kind": "orienteering",
      "status": "planned"
    }
  ],
  "clubs": [
    {
      "id": 1,
      "name": "Moscow Orienteers",
      "location": "Moscow",
      "logo": null
    }
  ],
  "competitions": [
    {
      "id": 7,
      "name": "Moscow City Championship - Long",
      "date": "2024-05-10",
      "location": "Moscow",
      "sport_kind": "orienteering",
      "status": "planned",
      "event": {
        "id": 3,
        "name": "Moscow Spring Cup"
      }
    }
  ]
}
```

**Errors:**
- `422` - Query shorter than 2 characters

**Notes:**
- Each type returns at most `limit` results — there is no pagination within types. If more results are needed, use the type-specific list endpoints with their own `q` param.
- Competitions include a parent `event` brief so the frontend can construct the correct deep link.
- No authentication required. Private users/events/clubs are excluded regardless of caller identity.

---

## Implementation Notes

- All 4 queries run independently against the DB (no joins between types).
- Uses `ILIKE %q%` — sufficient for MVP. For better relevance at scale, consider adding `pg_trgm` GIN indexes:
  ```sql
  CREATE EXTENSION IF NOT EXISTS pg_trgm;
  CREATE INDEX idx_users_search ON users USING GIN (username_display gin_trgm_ops, first_name gin_trgm_ops);
  CREATE INDEX idx_events_search ON events USING GIN (name gin_trgm_ops);
  CREATE INDEX idx_clubs_search ON clubs USING GIN (name gin_trgm_ops);
  CREATE INDEX idx_competitions_search ON competitions USING GIN (name gin_trgm_ops);
  ```
