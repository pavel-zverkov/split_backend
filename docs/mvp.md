# MVP Scope

## Phase 1: Core
- [ ] User registration/auth (username + password)
- [ ] Workout CRUD with file upload (FIT/GPX/TCX)
- [ ] Basic privacy settings
- [ ] User profile
- [ ] Ghost user support

## Phase 2: Social
- [ ] Follow system
- [ ] View other users' workouts (respecting privacy)
- [ ] Clubs (create, join, leave)
- [ ] Club roles (owner, coach, member)

## Phase 3: Events
- [ ] Event/Competition CRUD
- [ ] Event participation with roles
- [ ] Competition registration
- [ ] Results and rankings
- [ ] Ghost user claiming

## Phase 4: Analysis
- [ ] Split comparison between users
- [ ] Artifact management (maps, courses)

---

## Post-MVP: Future Enhancements

### Automatic Timing System Integration

**Problem:** MVP assumes manual result entry by team members. Real competitions use automatic timing systems (SPORTident, Emit, chip timing) that provide real-time splits.

**Requirements:**
- Real-time splits as athlete passes each control point
- Both push (timing system calls API) and pull (we poll timing system) mechanisms
- Track data source (manual, import, timing_system)
- One timing system per competition (initially)

**Proposed changes:**

1. **New Result status:** `in_progress` (athlete started, receiving splits)

2. **New entity: TimingSystem**
   ```
   TimingSystem
   ├── id
   ├── competition_id (FK)
   ├── name ("SPORTident", "Emit", etc.)
   ├── api_key (for push authentication)
   ├── pull_endpoint (URL for polling, nullable)
   ├── pull_credentials (JSON, nullable)
   ├── is_active
   ├── created_at
   ```

3. **Result entity changes:**
   ```
   Result
   ├── source (enum: manual, import, timing_system)
   ├── timing_system_id (FK → TimingSystem, nullable)
   ```

4. **New endpoints:**
   | Endpoint | Method | Auth | Description |
   |----------|--------|------|-------------|
   | `/api/competitions/{id}/timing-system` | POST | Organizer | Register timing system |
   | `/api/competitions/{id}/timing-system` | GET | Organizer | Get timing system config |
   | `/api/competitions/{id}/timing-system` | PATCH | Organizer | Update timing system |
   | `/api/competitions/{id}/timing-system` | DELETE | Organizer | Remove timing system |
   | `/api/timing/split` | POST | API Key | Receive single split (push) |
   | `/api/timing/batch` | POST | API Key | Receive multiple splits (push) |

5. **Real-time split flow (push):**
   ```
   Timing System                         API
        |                                 |
        |-- POST /api/timing/split ------>|
        |   {bib: "101", cp: "31", time}  |
        |                                 |-- Find registration by bib
        |                                 |-- Create Result (in_progress) if not exists
        |                                 |-- Create ResultSplit
        |                                 |-- If cp="finish" → status=ok
        |<------ 201 Created -------------|
   ```

6. **Pull mechanism:** Background job polls `timing_system.pull_endpoint`

### Live Tracking

- WebSocket for real-time result/split updates to spectators
- GPS position streaming from athletes
- Map visualization with athlete positions
