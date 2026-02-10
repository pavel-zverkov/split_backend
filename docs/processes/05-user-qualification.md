# 5. User Qualification

| # | Endpoint | Method | Description |
|---|----------|--------|-------------|
| 5.1 | `/api/users/me/qualifications` | POST | Add qualification |
| 5.2 | `/api/users/me/qualifications` | GET | List my qualifications |
| 5.3 | `/api/users/{user_id}/qualifications` | GET | List user's qualifications |
| 5.4 | `/api/users/me/qualifications/{qualification_id}` | PATCH | Update qualification |
| 5.5 | `/api/users/me/qualifications/{qualification_id}` | DELETE | Delete qualification |

## 5.1 Add Qualification

**Endpoint:** `POST /api/users/me/qualifications`

**Authorization:** Authenticated user (self only)

**Request:**
```json
{
  "type": "athlete",
  "sport_kind": "orient",
  "rank": "CMS",
  "issued_date": "2023-05-15",
  "valid_until": null,
  "document_number": "123456"
}
```

**Flow:**
1. Validate no duplicate (same `type` + `sport_kind` + `rank`)
2. Create with `confirmed=null`

**Response:** `201 Created`
```json
{
  "id": 1,
  "type": "athlete",
  "sport_kind": "orient",
  "rank": "CMS",
  "issued_date": "2023-05-15",
  "valid_until": null,
  "document_number": "123456",
  "confirmed": null,
  "created_at": "2024-01-15T10:00:00Z"
}
```

**Note (MVP):** `confirmed` is always `null`. Confirmation engine planned for post-MVP.

## 5.2 List My Qualifications

**Endpoint:** `GET /api/users/me/qualifications`

**Authorization:** Authenticated user

**Response:** `200 OK`
```json
{
  "qualifications": [
    {
      "id": 1,
      "type": "athlete",
      "sport_kind": "orient",
      "rank": "CMS",
      "issued_date": "2023-05-15",
      "valid_until": null,
      "document_number": "123456",
      "confirmed": null
    }
  ]
}
```

## 5.3 List User's Qualifications

**Endpoint:** `GET /api/users/{user_id}/qualifications`

**Authorization:** Optional

**Visibility:** Follows target user's `privacy_default` setting:
| Privacy | Who can see |
|---------|-------------|
| `public` | Everyone |
| `followers` | Followers only |
| `private` | Only the user themselves |

**Response:** `200 OK`
```json
{
  "qualifications": [
    {
      "id": 1,
      "type": "athlete",
      "sport_kind": "orient",
      "rank": "CMS",
      "issued_date": "2023-05-15",
      "valid_until": null,
      "confirmed": null
    }
  ]
}
```

**Note:** `document_number` is hidden when viewing other users' qualifications.

## 5.4 Update Qualification

**Endpoint:** `PATCH /api/users/me/qualifications/{qualification_id}`

**Authorization:** Authenticated user (self only)

**Request:**
```json
{
  "rank": "MS",
  "issued_date": "2024-01-10",
  "valid_until": "2029-01-10",
  "document_number": "789012"
}
```

**Updatable fields:** `rank`, `issued_date`, `valid_until`, `document_number`

**Note:** Changing `type` or `sport_kind` requires delete + create new.

**Response:** `200 OK` (updated qualification object)

## 5.5 Delete Qualification

**Endpoint:** `DELETE /api/users/me/qualifications/{qualification_id}`

**Authorization:** Authenticated user (self only)

**Deletion type:** **Hard delete**

**Response:** `204 No Content`

---

