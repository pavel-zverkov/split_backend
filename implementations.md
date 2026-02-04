# Implementation Notes

## 1. ~~Missing Role Tables~~ RESOLVED
The current implementation lacks proper tables for participants and judges.
**Participants** and **judges** have qualifications or sports/referee ranks, and may require additional fields.

**Solution**: Added `UserQualification` table in `plan.md`:
- Supports both `athlete` and `referee` qualification types
- Same user can have multiple qualifications (athlete + referee for same sport)
- Tracks rank, issued date, expiration, document number
- Admin confirmation flag for verification

## 2. ~~Missing Competition Spectators~~ RESOLVED
The current design does not account for competition spectators.
A spectator tracking feature is desirable to generate post-competition statistics, such as:
- How many people watched online
- How many of those were also participants in the competition

**Solution**: Added `SpectatorSession` table in `plan.md`:
- Tracks viewing sessions per event/competition
- Supports both authenticated users and anonymous (via ip_hash)
- Records source (web/mobile/embed) and session duration
- Can cross-reference with `EventParticipation` for participant-viewer stats

---

## Open Questions

### 3. Notification System
For approval workflows (closed events, follow requests, club membership), how should notifications be delivered?
- In-app only?
- Email?
- Push notifications (mobile)?

### 4. File Parsing Strategy
For FIT/GPX/TCX uploads:
- Parse synchronously on upload?
- Queue for background processing?
- Which library to use? (fitparse, gpxpy, etc.)

### 5. Live Tracking
For Phase 4 (future):
- WebSocket for real-time positions?
- Polling interval for updates?
- Integration with GPS watch APIs?
