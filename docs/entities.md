# Entity Attributes

## User
| # | Attribute | Type | Required | Description |
|---|-----------|------|----------|-------------|
| 1 | `id` | int | PK | |
| 2 | `username` | string | yes, unique | Login identifier (see username rules below) |
| 3 | `username_display` | string | yes | Visible username (without unique suffix) |
| 4 | `email` | string | no, unique | Optional email |
| 5 | `password_hash` | string | no | Nullable for ghost users |
| 6 | `first_name` | string | yes | |
| 7 | `last_name` | string | no | |
| 8 | `birthday` | date | no | Used for ghost user matching |
| 9 | `gender` | enum | no | |
| 10 | `logo` | string | no | Avatar URL/path |
| 11 | `bio` | string | no | Profile description |
| 12 | `privacy_default` | enum | no | Default: private |
| 13 | `account_type` | enum | yes | registered/ghost |
| 14 | `created_by` | int | FK → User | Who created ghost user (null for registered) |
| 15 | `is_active` | bool | yes | Account active |
| 16 | `created_at` | datetime | yes | |
| 17 | `updated_at` | datetime | yes | |

**Username rules:**
- Registered users: choose their own username (alphanumeric + underscore)
- Ghost users: auto-generated as `{first_name}_{last_name}`
- If duplicate: internal `username` gets unique suffix (e.g., `ivan_petrov_a3f2`), but `username_display` stays `ivan_petrov`
- Users see `username_display`, system uses `username` for uniqueness

**Account types:**
- `registered` - has password, can login
- `ghost` - placeholder created by coach/organizer, no login

## UserFollow
| # | Attribute | Type | Required | Description |
|---|-----------|------|----------|-------------|
| 1 | `id` | int | PK | |
| 2 | `follower_id` | int | FK → User | Who follows |
| 3 | `following_id` | int | FK → User | Who is followed |
| 4 | `status` | enum | yes | pending/accepted/rejected |
| 5 | `created_at` | datetime | yes | |

*Note: Rejection is hidden from follower (shown as `pending`).*

## ClaimRequest
| # | Attribute | Type | Required | Description |
|---|-----------|------|----------|-------------|
| 1 | `id` | int | PK | |
| 2 | `claimer_id` | int | FK → User | Registered user claiming ghost |
| 3 | `ghost_user_id` | int | FK → User | Ghost user being claimed |
| 4 | `approver_id` | int | FK → User | Creator of ghost user (must approve) |
| 5 | `status` | enum | yes | pending/approved/rejected |
| 6 | `created_at` | datetime | yes | |
| 7 | `resolved_at` | datetime | no | When approved/rejected |

## Workout
| # | Attribute | Type | Required | Description |
|---|-----------|------|----------|-------------|
| 1 | `id` | int | PK | |
| 2 | `user_id` | int | FK → User | Owner |
| 3 | `title` | string | no | User-defined name |
| 4 | `description` | string | no | Notes |
| 5 | `sport_kind` | enum | yes | |
| 6 | `start_datetime` | datetime | yes | |
| 7 | `finish_datetime` | datetime | no | |
| 8 | `duration_seconds` | int | no | Total time (computed) |
| 9 | `distance_meters` | int | no | Total distance (computed) |
| 10 | `elevation_gain` | int | no | Meters climbed (computed) |
| 11 | `status` | enum | yes | draft/processing/ready/error |
| 12 | `privacy` | enum | yes | private/followers/public |
| 13 | `fit_file` | string | no | File path |
| 14 | `gpx_file` | string | no | File path |
| 15 | `tcx_file` | string | no | File path |
| 16 | `created_at` | datetime | yes | |
| 17 | `updated_at` | datetime | yes | |

## WorkoutSplit
| # | Attribute | Type | Required | Description |
|---|-----------|------|----------|-------------|
| 1 | `id` | int | PK | |
| 2 | `workout_id` | int | FK → Workout | Parent workout |
| 3 | `sequence` | int | yes | Order (1, 2, 3...) |
| 4 | `control_point` | string | no | Control code (free-form from file) |
| 5 | `distance_meters` | int | no | Distance marker (running) |
| 6 | `cumulative_time` | int | yes | Seconds from start |
| 7 | `split_time` | int | yes | Seconds for this leg |
| 8 | `position` | geometry | no | GPS point (optional) |

*Note: WorkoutSplit is free-form (parsed from GPS file). For competition analysis, see ResultSplit.*

## ResultSplit
| # | Attribute | Type | Required | Description |
|---|-----------|------|----------|-------------|
| 1 | `id` | int | PK | |
| 2 | `result_id` | int | FK → Result | Parent result |
| 3 | `control_point` | string | yes | Must match competition.control_points_list |
| 4 | `sequence` | int | yes | Order (1, 2, 3...) |
| 5 | `cumulative_time` | int | yes | Seconds from start |
| 6 | `split_time` | int | yes | Seconds for this leg |

*Note: ResultSplit is validated against competition.control_points_list. Position and time_behind_best are calculated dynamically.*

## Club
| # | Attribute | Type | Required | Description |
|---|-----------|------|----------|-------------|
| 1 | `id` | int | PK | |
| 2 | `name` | string | yes, unique | |
| 3 | `description` | string | no | About the club |
| 4 | `logo` | string | no | Logo URL/path |
| 5 | `location` | string | no | City/region |
| 6 | `privacy` | enum | yes | public/by_request |
| 7 | `owner_id` | int | FK → User | Creator |
| 8 | `created_at` | datetime | yes | |

## ClubMembership
| # | Attribute | Type | Required | Description |
|---|-----------|------|----------|-------------|
| 1 | `id` | int | PK | |
| 2 | `user_id` | int | FK → User | |
| 3 | `club_id` | int | FK → Club | |
| 4 | `role` | enum | yes | owner/coach/member |
| 5 | `status` | enum | yes | pending/active/rejected |
| 6 | `joined_at` | datetime | no | When approved |
| 7 | `created_at` | datetime | yes | When requested |

## Event
| # | Attribute | Type | Required | Description |
|---|-----------|------|----------|-------------|
| 1 | `id` | int | PK | |
| 2 | `name` | string | yes | |
| 3 | `logo` | string | no | Logo URL/path |
| 4 | `description` | string | no | Event details |
| 5 | `start_date` | date | yes | |
| 6 | `end_date` | date | yes | |
| 7 | `location` | string | no | Venue/area |
| 8 | `sport_kind` | enum | yes | |
| 9 | `privacy` | enum | yes | public/by_request |
| 10 | `status` | enum | yes | draft/planned/in_progress/finished/cancelled |
| 11 | `max_participants` | int | no | Capacity limit |
| 12 | `recruitment_open` | bool | yes | Team self-registration enabled (default: false) |
| 13 | `needed_roles` | array | no | Roles open for recruitment |
| 14 | `organizer_id` | int | FK → User | Creator |
| 15 | `created_at` | datetime | yes | |
| 16 | `updated_at` | datetime | yes | |

## EventInvite
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
| 9 | `uses_count` | int | yes | Current uses (default: 0) |
| 10 | `created_by` | int | FK → User | |
| 11 | `created_at` | datetime | yes | |

## EventParticipation
| # | Attribute | Type | Required | Description |
|---|-----------|------|----------|-------------|
| 1 | `id` | int | PK | |
| 2 | `user_id` | int | FK → User | |
| 3 | `event_id` | int | FK → Event | |
| 4 | `role` | enum | yes | organizer/secretary/judge/volunteer/participant/spectator |
| 5 | `position` | enum | no | chief/deputy/null (only for team roles) |
| 6 | `status` | enum | yes | pending/approved/rejected |
| 7 | `joined_at` | datetime | no | When approved/joined |
| 8 | `created_at` | datetime | yes | |

## Competition
| # | Attribute | Type | Required | Description |
|---|-----------|------|----------|-------------|
| 1 | `id` | int | PK | |
| 2 | `event_id` | int | FK → Event | Parent event |
| 3 | `name` | string | yes | |
| 4 | `description` | string | no | |
| 5 | `date` | date | yes | |
| 6 | `sport_kind` | enum | no | Inherits from event if null |
| 7 | `start_format` | enum | yes | mass_start/separated_start/click |
| 8 | `class_list` | array | no | Available classes |
| 9 | `control_points_list` | array | no | Checkpoints: control codes (orienteering) or distance markers (running) |
| 10 | `distance_meters` | int | no | Course length |
| 11 | `location` | string | no | |
| 12 | `status` | enum | yes | planned/registration_open/registration_closed/in_progress/finished/cancelled |
| 13 | `created_at` | datetime | yes | |

## CompetitionTeam
| # | Attribute | Type | Required | Description |
|---|-----------|------|----------|-------------|
| 1 | `id` | int | PK | |
| 2 | `competition_id` | int | FK → Competition | |
| 3 | `user_id` | int | FK → User | |
| 4 | `role` | enum | yes | organizer/secretary/judge/volunteer |
| 5 | `excluded` | bool | yes | Excluded from this competition (default: false) |
| 6 | `created_at` | datetime | yes | |

*Note: If no record exists, user inherits from EventParticipation. If `excluded=true`, user doesn't work on this competition.*

## CompetitionRegistration
| # | Attribute | Type | Required | Description |
|---|-----------|------|----------|-------------|
| 1 | `id` | int | PK | |
| 2 | `user_id` | int | FK → User | |
| 3 | `competition_id` | int | FK → Competition | |
| 4 | `class` | string | no | Selected competition class |
| 5 | `bib_number` | string | no | Start number |
| 6 | `start_time` | datetime | no | For separated_start |
| 7 | `status` | enum | yes | pending/registered/confirmed/rejected |
| 8 | `created_at` | datetime | yes | |

*Note: Status inherits from EventParticipation (pending→pending, approved→registered). Rejection is visible to user.*

## Result
| # | Attribute | Type | Required | Description |
|---|-----------|------|----------|-------------|
| 1 | `id` | int | PK | |
| 2 | `user_id` | int | FK → User | |
| 3 | `competition_id` | int | FK → Competition | |
| 4 | `workout_id` | int | FK → Workout | Linked workout (splits accessed via this) |
| 5 | `class` | string | no | Competition class |
| 6 | `position` | int | no | Ranking in class |
| 7 | `position_overall` | int | no | Ranking overall |
| 8 | `time_total` | int | no | Seconds |
| 9 | `time_behind_leader` | int | no | Seconds |
| 10 | `status` | enum | yes | ok/dsq/dns/dnf |
| 11 | `created_at` | datetime | yes | |
| 12 | `updated_at` | datetime | yes | |

*Note: Competition splits are stored in ResultSplit. Training splits (via linked workout) are in WorkoutSplit.*

## Artifact
| # | Attribute | Type | Required | Description |
|---|-----------|------|----------|-------------|
| 1 | `id` | int | PK | |
| 2 | `competition_id` | int | FK → Competition, nullable | For competition artifacts |
| 3 | `workout_id` | int | FK → Workout, nullable | For workout artifacts |
| 4 | `user_id` | int | FK → User | Uploader |
| 5 | `kind` | enum | yes | See artifact_kind enum |
| 6 | `file_path` | string | yes | MinIO path |
| 7 | `file_name` | string | yes | Original filename |
| 8 | `file_size` | int | yes | Size in bytes |
| 9 | `mime_type` | string | yes | MIME type |
| 10 | `tags` | array | no | Tags for filtering |
| 11 | `created_at` | datetime | yes | |

*Constraint: Either `competition_id` OR `workout_id` must be set (mutually exclusive, not both null).*

## OrientMap
| # | Attribute | Type | Required | Description |
|---|-----------|------|----------|-------------|
| 1 | `id` | int | PK | |
| 2 | `artifact_id` | int | FK → Artifact | |
| 3 | `map_name` | string | yes | |
| 4 | `location_name` | string | no | |
| 5 | `location_point` | geometry | no | PostGIS point |
| 6 | `scale` | string | no | e.g., "1:10000" |

## UserQualification
| # | Attribute | Type | Required | Description |
|---|-----------|------|----------|-------------|
| 1 | `id` | int | PK | |
| 2 | `user_id` | int | FK → User | |
| 3 | `type` | enum | yes | athlete/referee/coach |
| 4 | `sport_kind` | enum | yes | |
| 5 | `rank` | string | yes | e.g., "CMS", "MS", "Category 1" |
| 6 | `issued_date` | date | no | When qualification was granted |
| 7 | `valid_until` | date | no | Expiration (null = lifetime) |
| 8 | `document_number` | string | no | Certificate number |
| 9 | `confirmed` | bool | no | Verified (null for MVP) |
| 10 | `created_at` | datetime | yes | |

*Note: A user can have multiple qualifications - e.g., athlete rank AND referee rank for the same sport.*

## SpectatorSession
| # | Attribute | Type | Required | Description |
|---|-----------|------|----------|-------------|
| 1 | `id` | int | PK | |
| 2 | `user_id` | int | FK → User | Nullable for anonymous |
| 3 | `event_id` | int | FK → Event | |
| 4 | `competition_id` | int | FK → Competition | Nullable (watching whole event) |
| 5 | `session_start` | datetime | yes | |
| 6 | `session_end` | datetime | no | Null if still watching |
| 7 | `source` | enum | yes | web/mobile/embed |
| 8 | `ip_hash` | string | no | For anonymous unique counting |
