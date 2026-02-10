# 2. Follow System

| # | Endpoint | Method | Description |
|---|----------|--------|-------------|
| 2.1 | `/api/users/{user_id}/follow` | POST | Follow user |
| 2.2 | `/api/users/follow-requests/{follow_id}` | PATCH | Accept/reject follow request |
| 2.3 | `/api/users/{user_id}/follow` | DELETE | Unfollow user |
| 2.4 | `/api/users/{user_id}/followers` | GET | List user's followers |
| 2.5 | `/api/users/{user_id}/following` | GET | List who user follows |
| 2.6 | `/api/users/me/follow-requests` | GET | Get pending follow requests |

## 2.1 Follow User

**Endpoint:** `POST /api/users/{user_id}/follow`

**Authorization:** Authenticated user

**Flow:**
1. Check target user exists and is active
2. Check not already following (including rejected status)
3. Check target user's privacy settings
4. Create UserFollow record

**Privacy handling:**
| Target Privacy | UserFollow Status | Notification |
|----------------|-------------------|--------------|
| `public` | `accepted` | "X started following you" |
| `private` | `pending` | "X requested to follow you" |
| `followers` | `pending` | "X requested to follow you" |

**Request:** (empty body)

**Response:** `201 Created`
```json
{
  "id": 1,
  "follower_id": 5,
  "following_id": 10,
  "status": "pending",
  "created_at": "2024-01-15T10:00:00Z"
}
```

**Errors:**
- `400` - Already following or previous request was rejected
- `404` - User not found

## 2.2 Accept/Reject Follow Request

**Endpoint:** `PATCH /api/users/follow-requests/{follow_id}`

**Authorization:** Target user only

**Request:**
```json
{
  "status": "accepted"
}
```

**Status values:** `accepted`, `rejected`

**Flow:**
- If `accepted`: Update status, notify follower "X accepted your follow request"
- If `rejected`: Update status to `rejected` (soft delete — hidden from target, shown as `pending` to follower)

**Response:** `200 OK`

## 2.3 Unfollow User

**Endpoint:** `DELETE /api/users/{user_id}/follow`

**Authorization:** Follower only

**Deletion type:** **Hard delete**

**Flow:**
1. Find UserFollow where `follower_id=current_user` and `following_id=user_id`
2. Delete record (regardless of status: accepted, pending, or rejected)
3. No notification

**Note:** Hard delete allows the user to send a new follow request later.

**Response:** `204 No Content`

## 2.4 List Followers

**Endpoint:** `GET /api/users/{user_id}/followers`

**Authorization:** Optional (authenticated for `is_following` field)

**Query params:**
- `limit`, `offset` — pagination

**Visibility:** Returns only `accepted` followers for all viewers.

**Response:** `200 OK`
```json
{
  "followers": [
    {
      "id": 5,
      "username_display": "ivan_petrov",
      "first_name": "Ivan",
      "last_name": "P.",
      "logo": "https://minio.../avatars/5.jpg",
      "is_following": true
    }
  ],
  "total": 120,
  "limit": 20,
  "offset": 0
}
```

## 2.5 List Following

**Endpoint:** `GET /api/users/{user_id}/following`

**Authorization:** Optional (authenticated for `is_following` field)

**Query params:**
- `limit`, `offset` — pagination

**Visibility by viewer:**
| Viewer | Filter | Status Display |
|--------|--------|----------------|
| **Self** (`user_id` = current user) | `status IN (accepted, pending, rejected)` | `rejected` shown as `pending` |
| **Other user** | `status = accepted` | As-is |

**Response:** `200 OK`
```json
{
  "following": [
    {
      "id": 10,
      "username_display": "maria_smith",
      "first_name": "Maria",
      "last_name": "S.",
      "logo": "https://minio.../avatars/10.jpg",
      "status": "pending"
    }
  ],
  "total": 85,
  "limit": 20,
  "offset": 0
}
```

**Note:** `status` field only included when viewing own following list.

## 2.6 Get Pending Follow Requests

**Endpoint:** `GET /api/users/me/follow-requests`

**Authorization:** Authenticated user

**Query params:**
- `limit`, `offset` — pagination

**Description:** Returns incoming follow requests awaiting approval. Excludes already rejected requests.

**Response:** `200 OK`
```json
{
  "requests": [
    {
      "id": 1,
      "follower": {
        "id": 5,
        "username_display": "ivan_petrov",
        "first_name": "Ivan",
        "last_name": "P.",
        "logo": "https://minio.../avatars/5.jpg"
      },
      "created_at": "2024-01-15T10:00:00Z"
    }
  ],
  "total": 3,
  "limit": 20,
  "offset": 0
}
```

---

