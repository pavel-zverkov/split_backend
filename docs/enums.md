# Enum Values

## sport_kind
| Value | Description |
|-------|-------------|
| `orient` | Orienteering |
| `run` | Running |
| `bike` | Cycling |
| `cx_ski` | Cross-country skiing |
| `sport_tourism` | Sport tourism |

## start_format
| Value | Description | Registration during in_progress |
|-------|-------------|--------------------------------|
| `mass_start` | All start together | No |
| `separated_start` | Individual start times (protocol) | No |
| `free` | Free start (independent) | Yes |

## privacy (user/workout)
| Value | Description |
|-------|-------------|
| `public` | Visible to everyone |
| `private` | Visible only to owner |
| `followers` | Visible to followers |

## privacy (club/event)
| Value | Description |
|-------|-------------|
| `public` | Open to everyone |
| `by_request` | Requires approval to join |

## event_status
| Value | Description |
|-------|-------------|
| `draft` | Event created, not visible to public |
| `planned` | Visible (default). Requires at least one competition to transition from draft. |
| `in_progress` | Event running |
| `finished` | Completed. Auto-finishes/cancels all child competitions. |
| `cancelled` | Cancelled |

## competition_status
| Value | Description |
|-------|-------------|
| `planned` | Upcoming, registration not open |
| `registration_open` | Athletes can self-register |
| `registration_closed` | Self-registration closed, team members can still register athletes |
| `in_progress` | Currently active |
| `finished` | Completed |
| `cancelled` | Cancelled |

## workout_status
| Value | Description |
|-------|-------------|
| `draft` | Being recorded |
| `processing` | File uploaded, parsing |
| `ready` | Available |
| `error` | Failed to parse |

## result_status
| Value | Description |
|-------|-------------|
| `ok` | Finished normally |
| `dsq` | Disqualified |
| `dns` | Did not start |
| `dnf` | Did not finish |

## follow_status
| Value | Description |
|-------|-------------|
| `pending` | Awaiting approval |
| `accepted` | Active follow |
| `rejected` | Denied (hidden from target, shown as `pending` to follower) |

## membership_status
| Value | Description |
|-------|-------------|
| `pending` | Awaiting approval |
| `active` | Active member |
| `rejected` | Denied (hidden from owner/coach, shown as `pending` to requester) |

## participation_status (EventParticipation)
| Value | Description |
|-------|-------------|
| `pending` | Awaiting approval |
| `approved` | Confirmed |
| `rejected` | Denied (visible to user, can re-apply) |

*Note: Different from follow/membership — rejection is visible and users can re-apply.*

## registration_status (CompetitionRegistration)
| Value | Description |
|-------|-------------|
| `pending` | Inherited from EventParticipation.pending |
| `registered` | Inherited from EventParticipation.approved, awaiting bib/start_time |
| `confirmed` | Bib and start_time assigned |
| `rejected` | Denied (visible to user, can re-apply) |

*Note: Status inherits from EventParticipation at creation time.*

## club_role
| Value | Description |
|-------|-------------|
| `owner` | Club creator, full control |
| `coach` | Can manage members, training, view member workouts |
| `member` | Regular member |

## event_role
| Value | Has position | Description |
|-------|--------------|-------------|
| `organizer` | Yes | Full control, manage team, delete event |
| `secretary` | Yes | Manage registrations, approve athletes, upload results |
| `judge` | Yes | View registrations, manage results, mark DSQ/DNF |
| `volunteer` | No | View-only access to event data |
| `participant` | No | Athletes competing in the event |
| `spectator` | No | Viewers |

## event_position
| Value | Description |
|-------|-------------|
| `chief` | Chief of this role (max 1 per role) |
| `deputy` | Deputy chief (unlimited) |
| `null` | Regular member (unlimited) |

## gender
| Value | Description |
|-------|-------------|
| `male` | Male |
| `female` | Female |

## account_type
| Value | Description |
|-------|-------------|
| `registered` | Full account, can login |
| `ghost` | Placeholder, no login, awaiting claim |

## claim_status
| Value | Description |
|-------|-------------|
| `pending` | Awaiting creator approval |
| `approved` | Approved, ghost merged |
| `rejected` | Rejected by creator |

## artifact_kind

**Competition artifacts** (uploaded by organizer):
| Value | Description |
|-------|-------------|
| `map` | Orienteering map image |
| `course` | Course file (OCAD, Purple Pen) |
| `results_file` | Results export file |
| `photo` | Event photos |

**Workout artifacts** (uploaded by user):
| Value | Description |
|-------|-------------|
| `gps_track` | GPS track file (GPX) |
| `fit_file` | Garmin FIT file |
| `tcx_file` | TCX file |

## qualification_type
| Value | Description |
|-------|-------------|
| `athlete` | Sports rank (CMS, MS, MSIC, etc.) |
| `referee` | Referee category |
| `coach` | Coaching license/certification |

## spectator_source
| Value | Description |
|-------|-------------|
| `web` | Web browser |
| `mobile` | Mobile app |
| `embed` | Embedded widget |

## event_format
| Value | Description |
|-------|-------------|
| `single` | Single-competition event. Auto-creates one competition at event creation. Competition cannot be added/removed manually. Competition status syncs with event status. |
| `multi_stage` | Multi-stage event with multiple competitions. Requires ≥2 competitions to transition from draft→planned. |

## control_point_type
| Value | Description |
|-------|-------------|
| `start` | Start point |
| `control` | Intermediate control |
| `finish` | Finish point |

## total_result_status
| Value | Description |
|-------|-------------|
| `ok` | All required stages completed |
| `incomplete` | Fewer stages than required (min_stages not met) |
| `dsq` | Disqualified (DSQ in one of the source stages)
