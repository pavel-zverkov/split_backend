# Sports Service Concept

## Table of Contents

- [Overview](#overview)
- [Features](./features.md)
  - [1. Personal Features](./features.md#1-personal-features)
  - [2. Community Features](./features.md#2-community-features)
  - [3. Authentication](./features.md#3-authentication)
- [Entity Attributes](./entities.md)
  - [User](./entities.md#user)
  - [UserFollow](./entities.md#userfollow)
  - [ClaimRequest](./entities.md#claimrequest)
  - [Workout](./entities.md#workout)
  - [WorkoutSplit](./entities.md#workoutsplit)
  - [ResultSplit](./entities.md#resultsplit)
  - [Club](./entities.md#club)
  - [ClubMembership](./entities.md#clubmembership)
  - [Event](./entities.md#event)
  - [EventParticipation](./entities.md#eventparticipation)
  - [Competition](./entities.md#competition)
  - [CompetitionRegistration](./entities.md#competitionregistration)
  - [Result](./entities.md#result)
  - [Artifact](./entities.md#artifact)
  - [OrientMap](./entities.md#orientmap)
  - [UserQualification](./entities.md#userqualification)
  - [SpectatorSession](./entities.md#spectatorsession)
- [Enum Values](./enums.md)
- [Entity Relationship Diagram](./erd.md)
- [Processes](#processes)
  - [1. User Management](./processes/01-user-management.md)
    - [1.1 User Registration](./processes/01-user-management.md#11-user-registration)
    - [1.2 Login](./processes/01-user-management.md#12-login)
    - [1.3 Refresh Token](./processes/01-user-management.md#13-refresh-token)
    - [1.4 Logout](./processes/01-user-management.md#14-logout)
    - [1.5 Change Password](./processes/01-user-management.md#15-change-password)
    - [1.6 Get Current User](./processes/01-user-management.md#16-get-current-user)
    - [1.7 Update Profile](./processes/01-user-management.md#17-update-profile)
    - [1.8 Upload Avatar](./processes/01-user-management.md#18-upload-avatar)
    - [1.9 Get Public Profile](./processes/01-user-management.md#19-get-public-profile)
    - [1.10 Search Users](./processes/01-user-management.md#110-search-users)
    - [1.11 Create Ghost User](./processes/01-user-management.md#111-create-ghost-user)
    - [1.12 Find Matching Ghost Users](./processes/01-user-management.md#112-find-matching-ghost-users-competition-history)
    - [1.13 Claim Ghost User](./processes/01-user-management.md#113-claim-ghost-user)
    - [1.14 Approve/Reject Claim](./processes/01-user-management.md#114-approvereject-claim-request)
    - [1.15 Get My Claim Requests](./processes/01-user-management.md#115-get-my-claim-requests)
    - [1.16 Get Pending Claims to Approve](./processes/01-user-management.md#116-get-pending-claims-to-approve-for-creators)
    - [1.17 User Deletion](./processes/01-user-management.md#117-user-deletion)
  - [2. Follow System](./processes/02-follow-system.md)
    - [2.1 Follow User](./processes/02-follow-system.md#21-follow-user)
    - [2.2 Accept/Reject Follow Request](./processes/02-follow-system.md#22-acceptreject-follow-request)
    - [2.3 Unfollow User](./processes/02-follow-system.md#23-unfollow-user)
    - [2.4 List Followers](./processes/02-follow-system.md#24-list-followers)
    - [2.5 List Following](./processes/02-follow-system.md#25-list-following)
    - [2.6 Get Pending Follow Requests](./processes/02-follow-system.md#26-get-pending-follow-requests)
  - [3. Club Management](./processes/03-club-management.md)
    - [3.1 Create Club](./processes/03-club-management.md#31-create-club)
    - [3.2 Get Club Details](./processes/03-club-management.md#32-get-club-details)
    - [3.3 List/Search Clubs](./processes/03-club-management.md#33-listsearch-clubs)
    - [3.4 Update Club](./processes/03-club-management.md#34-update-club)
    - [3.5 Upload Club Logo](./processes/03-club-management.md#35-upload-club-logo)
    - [3.6 List Club Members](./processes/03-club-management.md#36-list-club-members)
    - [3.7 Delete Club](./processes/03-club-management.md#37-delete-club)
  - [4. Club Membership](./processes/04-club-membership.md)
    - [4.1 Join Club](./processes/04-club-membership.md#41-join-club)
    - [4.2 Approve/Reject Membership](./processes/04-club-membership.md#42-approvereject-membership-request)
    - [4.3 Leave Club](./processes/04-club-membership.md#43-leave-club)
    - [4.4 Remove Member](./processes/04-club-membership.md#44-remove-member-from-club)
    - [4.5 Assign/Remove Role](./processes/04-club-membership.md#45-assignremove-role)
    - [4.6 Transfer Ownership](./processes/04-club-membership.md#46-transfer-club-ownership)
  - [5. User Qualification](./processes/05-user-qualification.md)
    - [5.1 Add Qualification](./processes/05-user-qualification.md#51-add-qualification)
    - [5.2 List My Qualifications](./processes/05-user-qualification.md#52-list-my-qualifications)
    - [5.3 List User's Qualifications](./processes/05-user-qualification.md#53-list-users-qualifications)
    - [5.4 Update Qualification](./processes/05-user-qualification.md#54-update-qualification)
    - [5.5 Delete Qualification](./processes/05-user-qualification.md#55-delete-qualification)
  - [6. Event Management](./processes/06-event-management.md)
    - [6.1 Create Event](./processes/06-event-management.md#61-create-event)
    - [6.2 Get Event Details](./processes/06-event-management.md#62-get-event-details)
    - [6.3 List/Search Events](./processes/06-event-management.md#63-listsearch-events)
    - [6.4 Update Event](./processes/06-event-management.md#64-update-event)
    - [6.5 Delete Event](./processes/06-event-management.md#65-delete-event)
    - [6.6 List Team Members](./processes/06-event-management.md#66-list-team-members)
    - [6.7 Add Team Member](./processes/06-event-management.md#67-add-team-member)
    - [6.8 Update Team Member](./processes/06-event-management.md#68-update-team-member)
    - [6.9 Remove Team Member](./processes/06-event-management.md#69-remove-team-member)
    - [6.10 Transfer Organizer Role](./processes/06-event-management.md#610-transfer-organizer-role)
  - [7. Event Participation](./processes/07-event-participation.md)
    - [7.1 Join Event](./processes/07-event-participation.md#71-join-event)
    - [7.2 List Participants](./processes/07-event-participation.md#72-list-participants)
    - [7.3 List Requests](./processes/07-event-participation.md#73-list-requests)
    - [7.4 Approve/Reject Request](./processes/07-event-participation.md#74-approvereject-request)
    - [7.5 Get My Participation](./processes/07-event-participation.md#75-get-my-participation)
    - [7.6 Leave Event](./processes/07-event-participation.md#76-leave-event)
    - [7.7 Update Recruitment Settings](./processes/07-event-participation.md#77-update-recruitment-settings)
    - [7.8 Generate Invite Link](./processes/07-event-participation.md#78-generate-invite-link)
    - [7.9 List Active Invites](./processes/07-event-participation.md#79-list-active-invites)
    - [7.10 Revoke Invite](./processes/07-event-participation.md#710-revoke-invite)
  - [8. Competition Management](./processes/08-competition-management.md)
    - [8.1 Create Competition](./processes/08-competition-management.md#81-create-competition)
    - [8.2 List Competitions](./processes/08-competition-management.md#82-list-competitions)
    - [8.3 Get Competition Details](./processes/08-competition-management.md#83-get-competition-details)
    - [8.4 Update Competition](./processes/08-competition-management.md#84-update-competition)
    - [8.5 Delete Competition](./processes/08-competition-management.md#85-delete-competition)
    - [8.6 List Competition Team](./processes/08-competition-management.md#86-list-competition-team)
    - [8.7 Assign Team Member](./processes/08-competition-management.md#87-assign-team-member-to-competition)
    - [8.8 Remove from Team](./processes/08-competition-management.md#88-remove-from-competition-team)
  - [9. Competition Registration](./processes/09-competition-registration.md)
    - [9.1 Register for Competition](./processes/09-competition-registration.md#91-register-for-competition)
    - [9.2 Get My Registration](./processes/09-competition-registration.md#92-get-my-registration)
    - [9.3 List Registrations](./processes/09-competition-registration.md#93-list-registrations)
    - [9.4 Get Start List](./processes/09-competition-registration.md#94-get-start-list)
    - [9.5 Update Registration](./processes/09-competition-registration.md#95-update-registration)
    - [9.6 Batch Assign Bibs](./processes/09-competition-registration.md#96-batch-assign-bibs-and-start-times)
    - [9.7 Cancel My Registration](./processes/09-competition-registration.md#97-cancel-my-registration)
    - [9.8 Remove Participant](./processes/09-competition-registration.md#98-remove-participant-registration)
  - [10. Artifact Management](./processes/10-artifact-management.md)
    - [10.1 Upload Competition Artifact](./processes/10-artifact-management.md#101-upload-competition-artifact)
    - [10.2 List Competition Artifacts](./processes/10-artifact-management.md#102-list-competition-artifacts)
    - [10.3 Get Artifact Details](./processes/10-artifact-management.md#103-get-artifact-details)
    - [10.4 Update Artifact](./processes/10-artifact-management.md#104-update-artifact)
    - [10.5 Delete Artifact](./processes/10-artifact-management.md#105-delete-artifact)
    - [10.6 Download Artifact](./processes/10-artifact-management.md#106-download-artifact-file)
    - [10.7 Upload Workout Artifact](./processes/10-artifact-management.md#107-upload-workout-artifact)
    - [10.8 List Workout Artifacts](./processes/10-artifact-management.md#108-list-workout-artifacts)
  - [11. Result Management](./processes/11-result-management.md)
    - [11.1 Create Result](./processes/11-result-management.md#111-create-result)
    - [11.2 List Results](./processes/11-result-management.md#112-list-results-leaderboard)
    - [11.3 Get Result with Splits](./processes/11-result-management.md#113-get-result-with-splits)
    - [11.4 Get My Result](./processes/11-result-management.md#114-get-my-result)
    - [11.5 Update Result](./processes/11-result-management.md#115-update-result)
    - [11.6 Delete Result](./processes/11-result-management.md#116-delete-result)
    - [11.7 Recalculate Positions](./processes/11-result-management.md#117-recalculate-positions)
    - [11.8 Batch Import Results](./processes/11-result-management.md#118-batch-import-results)
    - [11.9 Link Workout to Result](./processes/11-result-management.md#119-link-workout-to-result)
  - [12. Workout Management](./processes/12-workout-management.md)
    - [12.1 Create Workout](./processes/12-workout-management.md#121-create-workout)
    - [12.2 List My Workouts](./processes/12-workout-management.md#122-list-my-workouts)
    - [12.3 Get Workout Details](./processes/12-workout-management.md#123-get-workout-details)
    - [12.4 List User's Workouts](./processes/12-workout-management.md#124-list-users-workouts)
    - [12.5 Update Workout](./processes/12-workout-management.md#125-update-workout)
    - [12.6 Delete Workout](./processes/12-workout-management.md#126-delete-workout)
  - [13. Split Management (WorkoutSplit)](./processes/13-split-management.md)
    - [13.1 List Workout Splits](./processes/13-split-management.md#131-list-workout-splits)
    - [13.2 Manual Split Entry](./processes/13-split-management.md#132-manual-split-entry)
    - [13.3 Update Single Split](./processes/13-split-management.md#133-update-single-split)
    - [13.4 Delete All Splits](./processes/13-split-management.md#134-delete-all-splits)
- [MVP Scope](./mvp.md)

---

## Overview

A sports service with capabilities for both personal and community purposes.

**Target audience:** Orienteering athletes, coaches, clubs, and event organizers.

**Core features:**
- Workout tracking with FIT/GPX/TCX file support
- Split time analysis and comparison
- Club management with roles (owner, coach, member)
- Event and competition organization
- Ghost user support for unregistered athletes

---

## Quick Links

| Document | Description |
|----------|-------------|
| [Features](./features.md) | Product requirements and features |
| [Entities](./entities.md) | Database schema (17 tables) |
| [Enums](./enums.md) | All enum values |
| [ERD](./erd.md) | Entity relationship diagram |
| [MVP](./mvp.md) | Development phases |

### Processes (99 endpoints)

| # | Process | Endpoints | File |
|---|---------|-----------|------|
| 1 | User Management | 17 | [01-user-management.md](./processes/01-user-management.md) |
| 2 | Follow System | 6 | [02-follow-system.md](./processes/02-follow-system.md) |
| 3 | Club Management | 7 | [03-club-management.md](./processes/03-club-management.md) |
| 4 | Club Membership | 6 | [04-club-membership.md](./processes/04-club-membership.md) |
| 5 | User Qualification | 5 | [05-user-qualification.md](./processes/05-user-qualification.md) |
| 6 | Event Management | 10 | [06-event-management.md](./processes/06-event-management.md) |
| 7 | Event Participation | 10 | [07-event-participation.md](./processes/07-event-participation.md) |
| 8 | Competition Management | 8 | [08-competition-management.md](./processes/08-competition-management.md) |
| 9 | Competition Registration | 8 | [09-competition-registration.md](./processes/09-competition-registration.md) |
| 10 | Artifact Management | 8 | [10-artifact-management.md](./processes/10-artifact-management.md) |
| 11 | Result Management | 9 | [11-result-management.md](./processes/11-result-management.md) |
| 12 | Workout Management | 6 | [12-workout-management.md](./processes/12-workout-management.md) |
| 13 | Split Management | 4 | [13-split-management.md](./processes/13-split-management.md) |
