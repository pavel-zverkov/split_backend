# 14. Event Feed

| # | Endpoint | Method | Description |
|---|----------|--------|-------------|
| 14.1 | `/api/feed` | GET | Get chronological event feed |

## Feed Concept

The **Feed** provides a chronologically sorted, grouped view of events and competitions for the frontend. It flattens all events into date-keyed items and groups consecutive competitions from the same multi-stage event together.

### Feed Item Types

| Type | Description |
|------|-------------|
| `single` | A single-format event with one competition |
| `multi_stage_group` | A group of consecutive competitions from one multi-stage event |

### Grouping Algorithm

1. **Flatten**: Single events produce one item (keyed by `event.start_date`). Multi-stage events produce N items, one per competition (keyed by `competition.date`).
2. **Sort** all items by date ascending.
3. **Group** consecutive items from the same multi-stage event into a single `multi_stage_group`.

If another event's competition falls between two competitions of the same multi-stage event, they are split into separate groups.

**Example:**
```
Date-sorted feed:
  Mar 15: [Sprint Championship]    ← type: single
  Sep 20: [Autumn Cup - Day 1]  ─┐
  Sep 21: [Autumn Cup - Day 2]  ─┤ type: multi_stage_group (consecutive, same event)
  Sep 22: [Autumn Cup - Day 3]  ─┘
  Apr 18: [Spring Cup - Day 1]  ─┐
  Apr 19: [Spring Cup - Day 2]  ─┘ type: multi_stage_group
  May 01: [City Run - Stage 1]     ← type: multi_stage_group (group of 1, next stage on May 15)
  May 10: [Park Race]              ← type: single (breaks City Run grouping)
  May 15: [City Run - Stage 2]     ← type: multi_stage_group (group of 1, separated by Park Race)
```

---

## 14.1 Get Event Feed

**Endpoint:** `GET /api/feed`

**Authorization:** Public (optional authentication for draft event visibility)

**Query params:**
- `q` — search query (matches event name, description, location)
- `sport_kind` — filter by sport kind
- `status` — filter by event status
- `privacy` — filter by privacy
- `start_date_from` — filter events starting from this date
- `start_date_to` — filter events starting up to this date
- `limit` — pagination limit (default: 20, max: 100)
- `offset` — pagination offset (default: 0)

**Flow:**
1. Query all matching events using `event_crud.search_events` (no pagination — all matching events needed for correct grouping)
2. Flatten events into date-keyed items
3. Sort by date ascending
4. Group consecutive multi-stage competitions from the same event
5. Apply `limit`/`offset` to the resulting feed items

**Response:** `200 OK`
```json
{
  "items": [
    {
      "type": "single",
      "event": {
        "id": 1,
        "name": "Sprint Championship",
        "logo": null,
        "sport_kind": "orienteering",
        "status": "planned",
        "location": "Moscow",
        "participants_count": 42
      },
      "date": "2024-03-15",
      "competition": {
        "id": 10,
        "name": "Sprint Championship",
        "date": "2024-03-15",
        "status": "registration_open",
        "registrations_count": 38,
        "distances_count": 3
      },
      "competitions": []
    },
    {
      "type": "multi_stage_group",
      "event": {
        "id": 2,
        "name": "Autumn Cup",
        "logo": "https://example.com/logo.png",
        "sport_kind": "orienteering",
        "status": "in_progress",
        "location": "Saint Petersburg",
        "participants_count": 120
      },
      "date": "2024-09-20",
      "competition": null,
      "competitions": [
        {
          "id": 20,
          "name": "Day 1 - Long Distance",
          "date": "2024-09-20",
          "status": "finished",
          "registrations_count": 95,
          "distances_count": 4
        },
        {
          "id": 21,
          "name": "Day 2 - Middle Distance",
          "date": "2024-09-21",
          "status": "in_progress",
          "registrations_count": 92,
          "distances_count": 3
        },
        {
          "id": 22,
          "name": "Day 3 - Sprint",
          "date": "2024-09-22",
          "status": "planned",
          "registrations_count": 88,
          "distances_count": 2
        }
      ]
    }
  ],
  "total": 15,
  "limit": 20,
  "offset": 0
}
```

### Schemas

**FeedEventBrief:**
| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Event ID |
| `name` | string | Event name |
| `logo` | string? | Event logo URL |
| `sport_kind` | SportKind | Sport kind enum |
| `status` | EventStatus | Event status |
| `location` | string? | Event location |
| `participants_count` | int | Number of approved participants |

**FeedCompetitionItem:**
| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Competition ID |
| `name` | string | Competition name |
| `date` | date | Competition date |
| `status` | CompetitionStatus | Competition status |
| `registrations_count` | int | Number of registrations |
| `distances_count` | int | Number of distances |

**FeedItem:**
| Field | Type | Description |
|-------|------|-------------|
| `type` | `"single"` \| `"multi_stage_group"` | Item type |
| `event` | FeedEventBrief | Event summary |
| `date` | date | Sort key (event start_date for single, first competition date for group) |
| `competition` | FeedCompetitionItem? | Competition details (single type only) |
| `competitions` | FeedCompetitionItem[] | Grouped competitions (multi_stage_group type only) |

### Pagination Note

All matching events are fetched first, then grouping is applied, and finally `limit`/`offset` paginate the resulting feed items. This is acceptable for the current scale (tens of events). For larger datasets, server-side optimization may be needed.

---
