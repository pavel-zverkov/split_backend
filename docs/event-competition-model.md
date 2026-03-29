# Event & Competition Model

Architecture decision log and use-case analysis for the event/competition data model.

---

## Decision: Keep Current Model (2026-03-29)

After analysing alternative architectures (standalone competitions, events as optional containers),
the decision was made to **keep the current model** (`event_format: single | multi_stage`)
with one practical fix: relax the CompetitionTeam membership constraint (see below).

---

## Use Case Analysis

### Event Type Examples

| # | Example | One team? | Current model fit | Notes |
|---|---|---|---|---|
| 1 | Club training run | Yes | Needs event wrapper — awkward | Single event overkill |
| 2 | Local 5K race | Yes | Needs event wrapper — awkward | Single event overkill |
| 3 | City marathon | Yes | Needs event wrapper — awkward | Single event overkill |
| 4 | Regional championship (2-day) | Yes | Works perfectly ✓ | multi_stage + 2 competitions |
| 5 | Stage race (5 days) | Yes | Works perfectly ✓ | multi_stage + 5 competitions |
| 6 | Club season cup (1 club runs all races) | Yes | Works perfectly ✓ | multi_stage + N competitions |
| 7 | Federation cup (each race has own local org) | No | Works after constraint fix ✓ | See CompetitionTeam below |
| 8 | Fun starts (mixed sports) | Yes | Works, minor sport_kind per competition | multi_stage |
| 9 | Training camp (multiple sessions) | Yes | Works ✓ | multi_stage |

---

### Team Management

| Case | Who manages | Current behaviour | After constraint fix |
|---|---|---|---|
| Single race | One local club | Event team inherited by competition ✓ | Same ✓ |
| Multi-day (same organiser) | One team | Event team inherited by all competitions ✓ | Same ✓ |
| Stage race | One team | Event team inherited ✓ | Same ✓ |
| Season cup (1 club) | One club | Event team inherited ✓ | Same ✓ |
| Federation cup (different orgs per race) | Different per race | Blocked — all must be on event team first | Each competition team independent ✓ |

**CompetitionTeam constraint fix:**
The check `is_event_team_member` in `competition_controller.py` (`assign_team_member` endpoint)
is application-level only — no DB constraint enforces it. Removing this check allows assigning
any user directly to a competition team without requiring event team membership first.

---

### Status Flow

| Case | Event status | Competition status |
|---|---|---|
| Single event | draft → planned/upcoming → in_progress → finished / cancelled | Auto-synced with event |
| Multi-stage | draft → planned/upcoming → in_progress → finished / cancelled | Independent per competition: planned → reg_open ↔ reg_closed → in_progress → finished |
| Finished + 1 competition | Redirects frontend to competition page directly | Competition status shown |

---

### Registration

| Case | Where registered |
|---|---|
| Single race | Competition level ✓ |
| Multi-day | Per competition ✓ |
| Season cup | Per competition ✓ |
| Bulk season registration | Not implemented — future: event-level bulk creates all child registrations |

---

## What Was Considered But Rejected

### Standalone competitions + optional event container

Proposal: `competition.event_id` becomes nullable; Event becomes a pure series container;
all team/logo/recruitment management moves to competition level.

**Rejected because:**
- Current model already handles all common cases with one team
- The only real gap (different teams per federation cup) is fixed by removing one application check
- Migration cost (nullable event_id, new routes, refactored feed, all hooks) not justified
- `isSingleEvent` frontend workarounds cover the UX gaps adequately

**Revisit if:** standalone competitions (no event wrapper) become a significant friction point
for users creating simple one-day races.
