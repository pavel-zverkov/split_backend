# Entity Relationship Diagram

## Entity Types Legend

| Type | Entities | Description |
|------|----------|-------------|
| **Core** | User, Club, Event, Competition, Workout, Artifact | Main business entities |
| **Relation** | UserFollow, ClaimRequest, ClubMembership, EventParticipation, EventInvite, CompetitionTeam, CompetitionRegistration | Junction tables (many-to-many) |
| **Child** | WorkoutSplit, ResultSplit, Result, OrientMap, UserQualification, SpectatorSession | Dependent on parent entity |

```mermaid
erDiagram
    %% === CORE ENTITIES ===
    User ||--o{ Workout : "owns"
    User ||--o{ Club : "creates"
    User ||--o{ Event : "organizes"
    User ||--o{ Artifact : "uploads"
    Workout ||--o{ Artifact : "has_files"

    Event ||--o{ Competition : "contains"
    Event ||--o{ EventInvite : "has_invites"
    Competition ||--o{ Artifact : "has_files"

    %% === RELATION TABLES (many-to-many) ===
    User ||--o{ UserFollow : "follows"
    User ||--o{ ClaimRequest : "claims"
    User ||--o{ ClubMembership : "joins"
    User ||--o{ EventParticipation : "participates"
    User ||--o{ CompetitionRegistration : "registers"

    Club ||--o{ ClubMembership : "has_members"
    Event ||--o{ EventParticipation : "has_participants"
    Competition ||--o{ CompetitionRegistration : "has_registrations"
    Competition ||--o{ CompetitionTeam : "has_team"

    %% === CHILD TABLES ===
    User ||--o{ UserQualification : "has_qualifications"
    User ||--o{ Result : "achieves"
    User ||--o{ SpectatorSession : "watches"

    Workout ||--o{ WorkoutSplit : "has_splits"
    Workout ||--o| Result : "linked_to"
    Result ||--o{ ResultSplit : "has_splits"

    Competition ||--o{ Result : "produces"
    Competition ||--o{ SpectatorSession : "tracked_by"
    Event ||--o{ SpectatorSession : "tracked_by"

    Artifact ||--o| OrientMap : "extends"

    %% ============================================
    %% CORE ENTITIES
    %% ============================================

    User {
        int id PK
        string username UK
        string username_display
        string email
        string password_hash
        string first_name
        string last_name
        date birthday
        enum gender
        string logo
        string bio
        enum privacy_default
        enum account_type
        int created_by FK
        bool is_active
        datetime created_at
        datetime updated_at
    }

    Club {
        int id PK
        string name UK
        string description
        string logo
        string location
        enum privacy
        int owner_id FK
        datetime created_at
    }

    Event {
        int id PK
        string name
        string description
        date start_date
        date end_date
        string location
        enum sport_kind
        enum privacy "public/by_request"
        enum status "draft/planned/registration_open/in_progress/finished/cancelled"
        int max_participants
        bool recruitment_open
        array needed_roles
        int organizer_id FK
        datetime created_at
        datetime updated_at
    }

    EventInvite {
        int id PK
        int event_id FK
        string token UK
        enum role
        enum position
        array competition_ids
        datetime expires_at
        int max_uses
        int uses_count
        int created_by FK
        datetime created_at
    }

    Competition {
        int id PK
        int event_id FK
        string name
        string description
        date date
        enum sport_kind
        enum start_format
        array class_list
        array control_points_list
        int distance_meters
        string location
        enum status
        datetime created_at
    }

    Workout {
        int id PK
        int user_id FK
        string title
        string description
        enum sport_kind
        datetime start_datetime
        datetime finish_datetime
        int duration_seconds
        int distance_meters
        int elevation_gain
        enum status
        enum privacy
        string fit_file
        string gpx_file
        string tcx_file
        datetime created_at
        datetime updated_at
    }

    Artifact {
        int id PK
        int competition_id FK "nullable"
        int workout_id FK "nullable"
        int user_id FK
        enum kind
        string file_path
        string file_name
        int file_size
        string mime_type
        array tags
        datetime created_at
    }

    %% ============================================
    %% RELATION TABLES (junction/many-to-many)
    %% ============================================

    UserFollow {
        int id PK
        int follower_id FK
        int following_id FK
        enum status
        datetime created_at
    }

    ClaimRequest {
        int id PK
        int claimer_id FK
        int ghost_user_id FK
        int approver_id FK
        enum status
        datetime created_at
        datetime resolved_at
    }

    ClubMembership {
        int id PK
        int user_id FK
        int club_id FK
        enum role "owner/coach/member"
        enum status
        datetime joined_at
        datetime created_at
    }

    EventParticipation {
        int id PK
        int user_id FK
        int event_id FK
        enum role "organizer/secretary/judge/volunteer/participant/spectator"
        enum position "chief/deputy/null"
        enum status
        datetime joined_at
        datetime created_at
    }

    CompetitionTeam {
        int id PK
        int competition_id FK
        int user_id FK
        enum role
        bool excluded
        datetime created_at
    }

    CompetitionRegistration {
        int id PK
        int user_id FK
        int competition_id FK
        string class
        string bib_number
        datetime start_time
        enum status
        datetime created_at
    }

    %% ============================================
    %% CHILD TABLES (dependent entities)
    %% ============================================

    WorkoutSplit {
        int id PK
        int workout_id FK
        int sequence
        string control_point
        int distance_meters
        int cumulative_time
        int split_time
        geometry position
    }

    ResultSplit {
        int id PK
        int result_id FK
        string control_point
        int sequence
        int cumulative_time
        int split_time
    }

    Result {
        int id PK
        int user_id FK
        int competition_id FK
        int workout_id FK
        string class
        int position
        int position_overall
        int time_total
        int time_behind_leader
        enum status
        datetime created_at
        datetime updated_at
    }

    OrientMap {
        int id PK
        int artifact_id FK
        string map_name
        string location_name
        geometry location_point
        string scale
    }

    UserQualification {
        int id PK
        int user_id FK
        enum type
        enum sport_kind
        string rank
        date issued_date
        date valid_until
        string document_number
        bool confirmed
        datetime created_at
    }

    SpectatorSession {
        int id PK
        int user_id FK
        int event_id FK
        int competition_id FK
        datetime session_start
        datetime session_end
        enum source
        string ip_hash
    }
```
