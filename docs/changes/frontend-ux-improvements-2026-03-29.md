# Frontend UX Improvements (2026-03-29)

---

## 1. Ghost User Form (`CreateGhostUserForm`)

- First name + last name moved to **2-column grid** (side by side)
- **Swap detection** — warning shown when first/last name look reversed, with one-click Swap button
- **User search suggestions** — debounced search shows existing users in system as a heads-up
- Shake animation on invalid submit
- Error moved to bottom (below fields)
- `BirthdayPicker` with placeholder `"Athlete's date of birth"`

## 2. Ghost Step (`GhostStep` in AddAthleteModal)

Same name field improvements as above:
- 2-column grid for first/last name
- Swap detection
- `BirthdayPicker` replacing `<Input type="date">`

---

## 3. Event Status Label

`planned` → **`Upcoming`** in all display labels.

Affected: `EventStatusBadge`, `EventStatusControl`, `CreateEventForm`.
Backend enum value remains `planned` — frontend label only.

---

## 4. Status Badge Unification

- `EventStatusBadge` in `EventDetailHeader` had oversized custom classes (`text-2xl px-3 py-1`) — removed, now uses default Badge size matching `CompetitionStatusBadge`
- Both detail headers now place the badge **below the name** (`space-y-1.5`) instead of inline or pushed right

---

## 5. Single Event Display for Finished Multi-Stage Events

If an event is `finished` and has exactly **1 competition**, the frontend now treats it like a single event:

- `EventDetailPage` — redirects to the competition page directly (`<Navigate replace />`)
- `CompetitionDetailPage` — `isSingleEvent=true` when `event.status=finished && event.competitions_count=1`
- `CompetitionManagePage` — same `isSingleEvent` condition, shows full single-event manage layout

---

## 6. Competition Manage Page — Single Event Support

`CompetitionManagePage` now detects `isSingleEvent` (either `event_format=single` OR finished event with 1 competition) and renders a merged manage layout:

**Single event nav:** General · Team · Participants · Distances · Recruitment · Danger Zone

**General section additions:**
- Logo upload (`UploadEventLogo`)
- Event details (`EditEventForm`)
- `EventStatusControl` instead of `CompetitionStatusControl`

**New sections (single event only):**
- **Team** — `TeamRoster` + `AddTeamMemberForm`
- **Participants** — `ParticipantTable` + `AddParticipantForm` + `AddFromClubForm` + `CreateGhostUserForm`
- **Recruitment** — `RecruitmentSettings` + `CreateInviteForm` + invites list

**Danger Zone:**
- Single event: Transfer Ownership + Delete Event (→ `/events`)
- Multi-stage competition: Delete Competition (→ event page) — unchanged
