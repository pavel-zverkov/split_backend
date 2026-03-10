"""
Seed script for populating the database with realistic fake data.

Usage:
    poetry run python -m scripts.seed
"""

import random
from datetime import date, datetime, timedelta, timezone

from app.auth.auth_service import hash_password
from app.database import SessionLocal
from app.database.tables import (
    Club,
    ClubMembership,
    Competition,
    CompetitionRegistration,
    CompetitionTeam,
    ControlPoint,
    Distance,
    Event,
    EventParticipation,
    EventTotalConfig,
    EventTotalResult,
    Result,
    ResultSplit,
    User,
    UserFollow,
)
from app.enums.account_type import AccountType
from app.enums.club_role import ClubRole
from app.enums.competition_status import CompetitionStatus
from app.enums.control_point_type import ControlPointType
from app.enums.event_format import EventFormat
from app.enums.event_position import EventPosition
from app.enums.event_role import EventRole
from app.enums.event_status import EventStatus
from app.enums.follow_status import FollowStatus
from app.enums.gender import Gender
from app.enums.membership_status import MembershipStatus
from app.enums.participation_status import ParticipationStatus
from app.enums.privacy import Privacy
from app.enums.registration_status import RegistrationStatus
from app.enums.result_status import ResultStatus
from app.enums.sport_kind import SportKind
from app.enums.start_format import StartFormat
from app.event.total_calculator import recalculate_total

# Fixed seed for reproducibility
random.seed(42)

PASSWORD_HASH = hash_password("password123")

# ── Main users ──────────────────────────────────────────────────────────────

MAIN_USERS = [
    {
        "username": "ivanov_ivan",
        "username_display": "Ivanov Ivan",
        "email": "user1@test.com",
        "first_name": "Ivan",
        "last_name": "Ivanov",
        "birthday": date(1995, 3, 15),
        "gender": Gender.MALE,
        "bio": "Orienteering enthusiast since 2010. M21 competitor.",
    },
    {
        "username": "petrova_maria",
        "username_display": "Petrova Maria",
        "email": "user2@test.com",
        "first_name": "Maria",
        "last_name": "Petrova",
        "birthday": date(1998, 7, 22),
        "gender": Gender.FEMALE,
        "bio": "Trail runner and orienteer. Love forest navigation.",
    },
    {
        "username": "sidorov_alexey",
        "username_display": "Sidorov Alexey",
        "email": "user3@test.com",
        "first_name": "Alexey",
        "last_name": "Sidorov",
        "birthday": date(1990, 11, 5),
        "gender": Gender.MALE,
        "bio": "Running coach and event organizer.",
    },
    {
        "username": "kuznetsova_elena",
        "username_display": "Kuznetsova Elena",
        "email": "user4@test.com",
        "first_name": "Elena",
        "last_name": "Kuznetsova",
        "birthday": date(2000, 1, 30),
        "gender": Gender.FEMALE,
        "bio": "Young orienteering talent. W21 class.",
    },
    {
        "username": "volkov_dmitry",
        "username_display": "Volkov Dmitry",
        "email": "user5@test.com",
        "first_name": "Dmitry",
        "last_name": "Volkov",
        "birthday": date(1985, 9, 12),
        "gender": Gender.MALE,
        "bio": "Veteran athlete. Mountain biking and orienteering.",
    },
]

GHOST_USERS = [
    ("Nikolay", "Sokolov", date(1992, 4, 10), Gender.MALE),
    ("Anna", "Popova", date(1997, 8, 3), Gender.FEMALE),
    ("Sergey", "Lebedev", date(1988, 12, 25), Gender.MALE),
    ("Olga", "Morozova", date(1995, 6, 17), Gender.FEMALE),
    ("Andrey", "Novikov", date(1993, 2, 8), Gender.MALE),
    ("Tatiana", "Fedorova", date(1999, 10, 14), Gender.FEMALE),
    ("Pavel", "Mikhailov", date(1991, 5, 29), Gender.MALE),
    ("Ekaterina", "Voloshina", date(1996, 3, 7), Gender.FEMALE),
    ("Maxim", "Kozlov", date(1994, 11, 21), Gender.MALE),
    ("Irina", "Zaitseva", date(2001, 7, 1), Gender.FEMALE),
    ("Roman", "Orlov", date(1989, 1, 19), Gender.MALE),
    ("Natalia", "Belova", date(1998, 9, 6), Gender.FEMALE),
    ("Viktor", "Gusev", date(1987, 4, 28), Gender.MALE),
    ("Svetlana", "Titova", date(2000, 12, 11), Gender.FEMALE),
    ("Denis", "Karpov", date(1993, 8, 15), Gender.MALE),
]


def clear_data(db):
    """Truncate all tables in reverse FK order."""
    print("Clearing existing data...")
    db.query(ResultSplit).delete()
    db.query(Result).delete()
    db.query(EventTotalResult).delete()
    db.query(EventTotalConfig).delete()
    db.query(CompetitionRegistration).delete()
    db.query(CompetitionTeam).delete()
    db.query(ControlPoint).delete()
    db.query(Distance).delete()
    db.query(Competition).delete()
    db.query(EventParticipation).delete()
    db.query(Event).delete()
    db.query(ClubMembership).delete()
    db.query(Club).delete()
    db.query(UserFollow).delete()
    db.query(User).delete()
    db.commit()
    print("  Done.")


def create_users(db):
    """Create 5 main users + 15 ghost users."""
    print("Creating users...")
    users = []

    for data in MAIN_USERS:
        user = User(
            username=data["username"],
            username_display=data["username_display"],
            email=data["email"],
            password_hash=PASSWORD_HASH,
            first_name=data["first_name"],
            last_name=data["last_name"],
            birthday=data["birthday"],
            gender=data["gender"],
            bio=data["bio"],
            account_type=AccountType.REGISTERED,
            privacy_default=Privacy.PUBLIC,
        )
        db.add(user)
        users.append(user)

    db.flush()

    creator_ids = [u.id for u in users]
    for first, last, bday, gender in GHOST_USERS:
        ghost = User(
            username=f"{first.lower()}_{last.lower()}",
            username_display=f"{last} {first}",
            first_name=first,
            last_name=last,
            birthday=bday,
            gender=gender,
            account_type=AccountType.GHOST,
            privacy_default=Privacy.PUBLIC,
            created_by=random.choice(creator_ids),
        )
        db.add(ghost)
        users.append(ghost)

    db.flush()
    print(f"  Created {len(users)} users ({len(MAIN_USERS)} main, {len(GHOST_USERS)} ghost).")
    return users


def create_follows(db, users):
    """Create follow relationships between main users."""
    print("Creating follows...")
    main = users[:5]
    pairs = [
        (main[0], main[1], FollowStatus.ACCEPTED),
        (main[1], main[0], FollowStatus.ACCEPTED),
        (main[0], main[2], FollowStatus.ACCEPTED),
        (main[2], main[3], FollowStatus.ACCEPTED),
        (main[3], main[0], FollowStatus.PENDING),
        (main[4], main[1], FollowStatus.ACCEPTED),
    ]
    count = 0
    for follower, following, status in pairs:
        db.add(UserFollow(
            follower_id=follower.id,
            following_id=following.id,
            status=status,
        ))
        count += 1
    db.flush()
    print(f"  Created {count} follow relationships.")


def create_clubs(db, users):
    """Create 3 clubs."""
    print("Creating clubs...")
    clubs_data = [
        ("Forest Runners", SportKind.ORIENT, users[0], "Orienteering club for all levels"),
        ("City Runners", SportKind.RUN, users[2], "Urban running club"),
        ("Mountain Bikers", SportKind.BIKE, users[4], "MTB and adventure club"),
    ]
    clubs = []
    for name, sport, owner, desc in clubs_data:
        club = Club(
            name=name,
            description=desc,
            privacy=Privacy.PUBLIC,
            owner_id=owner.id,
        )
        db.add(club)
        clubs.append(club)
    db.flush()
    print(f"  Created {len(clubs)} clubs.")
    return clubs


def create_memberships(db, clubs, users):
    """Create club memberships."""
    print("Creating club memberships...")
    main = users[:5]
    all_users = users

    count = 0
    for club_idx, club in enumerate(clubs):
        owner = main[club_idx * 2] if club_idx < 2 else main[4]
        # Owner membership
        db.add(ClubMembership(
            user_id=owner.id,
            club_id=club.id,
            role=ClubRole.OWNER,
            status=MembershipStatus.ACTIVE,
            joined_at=datetime.now(timezone.utc),
        ))
        count += 1

        # Add 3-5 other members
        potential = [u for u in all_users if u.id != owner.id]
        members = random.sample(potential, random.randint(3, 5))
        for member in members:
            status = random.choice([MembershipStatus.ACTIVE, MembershipStatus.ACTIVE, MembershipStatus.PENDING])
            db.add(ClubMembership(
                user_id=member.id,
                club_id=club.id,
                role=ClubRole.MEMBER,
                status=status,
                joined_at=datetime.now(timezone.utc) if status == MembershipStatus.ACTIVE else None,
            ))
            count += 1

    db.flush()
    print(f"  Created {count} memberships.")


# ── Events & Competitions ──────────────────────────────────────────────────

EVENT_DEFS = [
    {
        "name": "Autumn Cup 2025",
        "format": EventFormat.MULTI_STAGE,
        "sport": SportKind.ORIENT,
        "status": EventStatus.FINISHED,
        "start_date": date(2025, 9, 20),
        "end_date": date(2025, 9, 22),
        "location": "Losiny Ostrov National Park",
        "organizer_idx": 0,
        "competitions": [
            {"name": "Day 1 - Sprint", "status": CompetitionStatus.FINISHED, "date_offset": 0},
            {"name": "Day 2 - Middle", "status": CompetitionStatus.FINISHED, "date_offset": 1},
            {"name": "Day 3 - Long", "status": CompetitionStatus.FINISHED, "date_offset": 2},
        ],
    },
    {
        "name": "Sprint Championship",
        "format": EventFormat.SINGLE,
        "sport": SportKind.ORIENT,
        "status": EventStatus.IN_PROGRESS,
        "start_date": date(2026, 3, 15),
        "end_date": date(2026, 3, 15),
        "location": "Sokolniki Park",
        "organizer_idx": 1,
        "competitions": [
            {"name": "Sprint Final", "status": CompetitionStatus.REGISTRATION_OPEN, "date_offset": 0},
        ],
    },
    {
        "name": "City Run Series",
        "format": EventFormat.MULTI_STAGE,
        "sport": SportKind.RUN,
        "status": EventStatus.PLANNED,
        "start_date": date(2026, 5, 1),
        "end_date": date(2026, 5, 15),
        "location": "Moscow City Center",
        "organizer_idx": 2,
        "competitions": [
            {"name": "Stage 1 - 5K", "status": CompetitionStatus.PLANNED, "date_offset": 0},
            {"name": "Stage 2 - 10K", "status": CompetitionStatus.PLANNED, "date_offset": 14},
        ],
    },
    {
        "name": "Park Run #42",
        "format": EventFormat.SINGLE,
        "sport": SportKind.RUN,
        "status": EventStatus.DRAFT,
        "start_date": date(2026, 4, 5),
        "end_date": date(2026, 4, 5),
        "location": "Gorky Park",
        "organizer_idx": 2,
        "competitions": [
            {"name": "Park Run", "status": CompetitionStatus.PLANNED, "date_offset": 0},
        ],
    },
    {
        "name": "Spring Cup 2026",
        "format": EventFormat.MULTI_STAGE,
        "sport": SportKind.ORIENT,
        "status": EventStatus.IN_PROGRESS,
        "start_date": date(2026, 4, 18),
        "end_date": date(2026, 4, 19),
        "location": "Meshchersky Park",
        "organizer_idx": 0,
        "competitions": [
            {"name": "Day 1 - Middle", "status": CompetitionStatus.FINISHED, "date_offset": 0},
            {"name": "Day 2 - Long", "status": CompetitionStatus.IN_PROGRESS, "date_offset": 1},
        ],
    },
]

# Distance templates per sport
ORIENT_DISTANCES = [
    {"name": "M21 Long", "meters": 8500, "climb": 250, "classes": ["M21"], "cp_count": 15},
    {"name": "W21 Middle", "meters": 5200, "climb": 150, "classes": ["W21", "W35"], "cp_count": 12},
    {"name": "Open Short", "meters": 3000, "climb": 80, "classes": ["M10", "W10", "OPEN"], "cp_count": 8},
]

RUN_DISTANCES_5K = [
    {"name": "Men 5K", "meters": 5000, "climb": 30, "classes": ["M21", "M35"], "cp_count": 5},
    {"name": "Women 5K", "meters": 5000, "climb": 30, "classes": ["W21", "W35"], "cp_count": 5},
]

RUN_DISTANCES_10K = [
    {"name": "Men 10K", "meters": 10000, "climb": 50, "classes": ["M21", "M35"], "cp_count": 8},
    {"name": "Women 10K", "meters": 10000, "climb": 50, "classes": ["W21", "W35"], "cp_count": 8},
]


def create_events(db, users):
    """Create events."""
    print("Creating events...")
    main = users[:5]
    events = []

    for edef in EVENT_DEFS:
        event = Event(
            name=edef["name"],
            description=f"{edef['name']} — a {edef['sport'].value} event.",
            start_date=edef["start_date"],
            end_date=edef["end_date"],
            location=edef["location"],
            sport_kind=edef["sport"],
            privacy=Privacy.PUBLIC,
            event_format=edef["format"],
            status=edef["status"],
            organizer_id=main[edef["organizer_idx"]].id,
        )
        db.add(event)
        events.append(event)

    db.flush()
    print(f"  Created {len(events)} events.")
    return events


def create_participations(db, events, users):
    """Create event participations (organizer, secretary, judges, participants)."""
    print("Creating event participations...")
    main = users[:5]
    all_users = users
    count = 0

    # Map organizer index from EVENT_DEFS
    for i, event in enumerate(events):
        edef = EVENT_DEFS[i]
        org_idx = edef["organizer_idx"]

        # Organizer
        db.add(EventParticipation(
            user_id=main[org_idx].id,
            event_id=event.id,
            role=EventRole.ORGANIZER,
            position=EventPosition.CHIEF,
            status=ParticipationStatus.APPROVED,
            joined_at=datetime.now(timezone.utc),
        ))
        count += 1

        # Secretary — pick another main user
        sec_idx = (org_idx + 1) % 5
        db.add(EventParticipation(
            user_id=main[sec_idx].id,
            event_id=event.id,
            role=EventRole.SECRETARY,
            position=EventPosition.CHIEF,
            status=ParticipationStatus.APPROVED,
            joined_at=datetime.now(timezone.utc),
        ))
        count += 1

        # 1-2 judges from remaining main users
        remaining_main = [m for j, m in enumerate(main) if j not in (org_idx, sec_idx)]
        judges = random.sample(remaining_main, random.randint(1, 2))
        for judge in judges:
            db.add(EventParticipation(
                user_id=judge.id,
                event_id=event.id,
                role=EventRole.JUDGE,
                status=ParticipationStatus.APPROVED,
                joined_at=datetime.now(timezone.utc),
            ))
            count += 1

        # Participants: 8-15 users (mix of main and ghost, excluding team)
        team_ids = {main[org_idx].id, main[sec_idx].id} | {j.id for j in judges}
        available = [u for u in all_users if u.id not in team_ids]
        participant_count = random.randint(8, min(15, len(available)))
        participants = random.sample(available, participant_count)

        for p in participants:
            db.add(EventParticipation(
                user_id=p.id,
                event_id=event.id,
                role=EventRole.PARTICIPANT,
                status=ParticipationStatus.APPROVED,
                joined_at=datetime.now(timezone.utc),
            ))
            count += 1

    db.flush()
    print(f"  Created {count} participations.")


def create_competitions(db, events):
    """Create competitions for each event."""
    print("Creating competitions...")
    competitions = []

    for i, event in enumerate(events):
        edef = EVENT_DEFS[i]
        for cdef in edef["competitions"]:
            comp = Competition(
                event_id=event.id,
                name=cdef["name"],
                description=f"{cdef['name']} competition",
                date=event.start_date + timedelta(days=cdef["date_offset"]),
                sport_kind=edef["sport"],
                start_format=StartFormat.SEPARATED_START,
                status=cdef["status"],
            )
            db.add(comp)
            competitions.append(comp)

    db.flush()
    print(f"  Created {len(competitions)} competitions.")
    return competitions


def _get_distance_templates(event_def, comp_name):
    """Pick distance templates based on sport and competition name."""
    if event_def["sport"] == SportKind.ORIENT:
        return ORIENT_DISTANCES
    if "5K" in comp_name:
        return RUN_DISTANCES_5K
    if "10K" in comp_name:
        return RUN_DISTANCES_10K
    # Default for run (Park Run, Sprint)
    return [
        {"name": "Men Open", "meters": 5000, "climb": 20, "classes": ["M21", "M35"], "cp_count": 5},
        {"name": "Women Open", "meters": 5000, "climb": 20, "classes": ["W21", "W35"], "cp_count": 5},
    ]


def create_distances_and_cps(db, competitions):
    """Create distances and control points for each competition."""
    print("Creating distances and control points...")
    dist_count = 0
    cp_count = 0

    for comp_idx, comp in enumerate(competitions):
        # Find the event def for this competition
        edef = None
        offset = 0
        for ed in EVENT_DEFS:
            if offset + len(ed["competitions"]) > comp_idx:
                edef = ed
                break
            offset += len(ed["competitions"])

        templates = _get_distance_templates(edef, comp.name)

        for tmpl in templates:
            dist = Distance(
                competition_id=comp.id,
                name=tmpl["name"],
                distance_meters=tmpl["meters"],
                climb_meters=tmpl["climb"],
                classes=tmpl["classes"],
            )
            db.add(dist)
            db.flush()
            dist_count += 1

            # Create control points
            num_cps = tmpl["cp_count"]
            # START
            db.add(ControlPoint(
                distance_id=dist.id,
                code="S1",
                sequence=0,
                type=ControlPointType.START,
            ))
            cp_count += 1

            # CONTROLs
            for seq in range(1, num_cps - 1):
                code = str(30 + seq)
                db.add(ControlPoint(
                    distance_id=dist.id,
                    code=code,
                    sequence=seq,
                    type=ControlPointType.CONTROL,
                ))
                cp_count += 1

            # FINISH
            db.add(ControlPoint(
                distance_id=dist.id,
                code="F1",
                sequence=num_cps - 1,
                type=ControlPointType.FINISH,
            ))
            cp_count += 1

    db.flush()
    print(f"  Created {dist_count} distances, {cp_count} control points.")


def _get_class_for_user(user, available_classes):
    """Assign a class based on gender."""
    if user.gender == Gender.MALE:
        male_classes = [c for c in available_classes if c.startswith("M") or c == "OPEN"]
        return random.choice(male_classes) if male_classes else available_classes[0]
    elif user.gender == Gender.FEMALE:
        female_classes = [c for c in available_classes if c.startswith("W") or c == "OPEN"]
        return random.choice(female_classes) if female_classes else available_classes[0]
    return random.choice(available_classes)


def create_registrations(db, competitions, users):
    """Create competition registrations for participants."""
    print("Creating registrations...")
    count = 0

    for comp in competitions:
        event_id = comp.event_id

        # Get participants for this event
        participations = db.query(EventParticipation).filter(
            EventParticipation.event_id == event_id,
            EventParticipation.role == EventRole.PARTICIPANT,
            EventParticipation.status == ParticipationStatus.APPROVED,
        ).all()

        # Get distances for this competition
        distances = db.query(Distance).filter(Distance.competition_id == comp.id).all()
        if not distances:
            continue

        # All classes across distances
        all_classes = []
        for d in distances:
            if d.classes:
                all_classes.extend(d.classes)

        if not all_classes:
            continue

        # Determine registration status based on competition status
        if comp.status == CompetitionStatus.FINISHED:
            reg_status = RegistrationStatus.CONFIRMED
        elif comp.status in (CompetitionStatus.IN_PROGRESS, CompetitionStatus.REGISTRATION_OPEN):
            reg_status = RegistrationStatus.REGISTERED
        else:
            reg_status = RegistrationStatus.PENDING

        bib = 1
        for part in participations:
            user = db.query(User).filter(User.id == part.user_id).first()
            cls = _get_class_for_user(user, all_classes)

            db.add(CompetitionRegistration(
                user_id=user.id,
                competition_id=comp.id,
                class_=cls,
                bib_number=str(bib),
                status=reg_status,
            ))
            bib += 1
            count += 1

    db.flush()
    print(f"  Created {count} registrations.")


def create_results(db, competitions, users):
    """Create results with splits for FINISHED competitions."""
    print("Creating results...")
    result_count = 0
    split_count = 0

    finished_comps = [c for c in competitions if c.status == CompetitionStatus.FINISHED]

    for comp in finished_comps:
        # Get registrations
        registrations = db.query(CompetitionRegistration).filter(
            CompetitionRegistration.competition_id == comp.id,
        ).all()

        # Get distances with control points
        distances = db.query(Distance).filter(Distance.competition_id == comp.id).all()
        class_to_distance = {}
        for dist in distances:
            if dist.classes:
                for cls in dist.classes:
                    class_to_distance[cls] = dist

        # Collect results per class for position calculation
        class_results: dict[str, list[dict]] = {}

        for reg_idx, reg in enumerate(registrations):
            cls = reg.class_
            dist = class_to_distance.get(cls)
            if not dist:
                continue

            # 1-2 DSQ/DNF per competition
            is_bad = reg_idx >= len(registrations) - 2
            if is_bad:
                status = random.choice([ResultStatus.DSQ, ResultStatus.DNF])
                time_total = None
            else:
                status = ResultStatus.OK
                # Base time depends on distance: ~6-10 min/km for orienteering, ~4-6 min/km for running
                base_ms = dist.distance_meters * random.randint(5, 9)  # ms per meter -> ~5-9 min/km
                variation = random.randint(-base_ms // 10, base_ms // 5)
                time_total = base_ms + variation

            result_data = {
                "user_id": reg.user_id,
                "competition_id": comp.id,
                "distance_id": dist.id,
                "class_": cls,
                "time_total": time_total,
                "status": status,
            }

            class_results.setdefault(cls, []).append(result_data)

        # Calculate positions per class
        all_results_data = []
        for cls, results_list in class_results.items():
            ok_results = [r for r in results_list if r["status"] == ResultStatus.OK and r["time_total"]]
            ok_results.sort(key=lambda r: r["time_total"])

            leader_time = ok_results[0]["time_total"] if ok_results else None

            for pos, r in enumerate(ok_results, 1):
                r["position"] = pos
                r["time_behind_leader"] = r["time_total"] - leader_time if leader_time else 0

            for r in results_list:
                if r["status"] != ResultStatus.OK or not r["time_total"]:
                    r["position"] = None
                    r["time_behind_leader"] = None

            all_results_data.extend(results_list)

        # Assign overall positions
        ok_overall = [r for r in all_results_data if r["status"] == ResultStatus.OK and r["time_total"]]
        ok_overall.sort(key=lambda r: r["time_total"])
        for pos, r in enumerate(ok_overall, 1):
            r["position_overall"] = pos
        for r in all_results_data:
            if "position_overall" not in r:
                r["position_overall"] = None

        # Insert results and splits
        for r_data in all_results_data:
            result = Result(
                user_id=r_data["user_id"],
                competition_id=r_data["competition_id"],
                distance_id=r_data["distance_id"],
                class_=r_data["class_"],
                position=r_data["position"],
                position_overall=r_data["position_overall"],
                time_total=r_data["time_total"],
                time_behind_leader=r_data["time_behind_leader"],
                status=r_data["status"],
            )
            db.add(result)
            db.flush()
            result_count += 1

            # Create splits for OK results
            if r_data["status"] == ResultStatus.OK and r_data["time_total"]:
                dist = db.query(Distance).filter(Distance.id == r_data["distance_id"]).first()
                cps = db.query(ControlPoint).filter(
                    ControlPoint.distance_id == dist.id
                ).order_by(ControlPoint.sequence).all()

                if cps:
                    total_time = r_data["time_total"]
                    # Distribute time across control points with variation
                    num_cps = len(cps)
                    avg_split = total_time // num_cps
                    cumulative = 0

                    for cp in cps:
                        if cp.type == ControlPointType.START:
                            split_time = 0
                        elif cp.type == ControlPointType.FINISH:
                            split_time = total_time - cumulative
                        else:
                            variation_pct = random.uniform(0.6, 1.4)
                            split_time = int(avg_split * variation_pct)

                        cumulative += split_time

                        db.add(ResultSplit(
                            result_id=result.id,
                            control_point=cp.code,
                            control_point_id=cp.id,
                            sequence=cp.sequence,
                            cumulative_time=cumulative,
                            split_time=split_time,
                        ))
                        split_count += 1

                    # Adjust cumulative to match total exactly
                    # (last CP cumulative should equal time_total)

    db.flush()
    print(f"  Created {result_count} results, {split_count} splits.")


def create_total_configs(db, events):
    """Create total configs for multi-stage events with finished competitions."""
    print("Creating total configs...")

    # Autumn Cup 2025 (index 0) — fully finished multi-stage
    autumn_cup = events[0]
    config = EventTotalConfig(
        event_id=autumn_cup.id,
        name="Overall Standing",
        rules={
            "source": {},
            "score": {"type": "time"},
            "aggregation": {"method": "sum"},
            "penalties": {"dsq_handling": "exclude", "dns_handling": "exclude"},
            "sort_order": "asc",
        },
        auto_calculate=True,
    )
    db.add(config)
    db.flush()

    total_count = recalculate_total(db, config)
    print(f"  Created total config for '{autumn_cup.name}' with {total_count} total results.")

    # Spring Cup 2026 (index 4) — partially finished
    spring_cup = events[4]
    config2 = EventTotalConfig(
        event_id=spring_cup.id,
        name="Overall Standing",
        rules={
            "source": {},
            "score": {"type": "time"},
            "aggregation": {"method": "sum"},
            "penalties": {"dsq_handling": "exclude", "dns_handling": "exclude"},
            "sort_order": "asc",
        },
        auto_calculate=True,
    )
    db.add(config2)
    db.flush()

    total_count2 = recalculate_total(db, config2)
    print(f"  Created total config for '{spring_cup.name}' with {total_count2} total results.")


def print_summary(db):
    """Print a summary of all seeded data."""
    print("\n" + "=" * 50)
    print("SEED SUMMARY")
    print("=" * 50)
    tables = [
        ("Users", User),
        ("User Follows", UserFollow),
        ("Clubs", Club),
        ("Club Memberships", ClubMembership),
        ("Events", Event),
        ("Event Participations", EventParticipation),
        ("Competitions", Competition),
        ("Distances", Distance),
        ("Control Points", ControlPoint),
        ("Registrations", CompetitionRegistration),
        ("Results", Result),
        ("Result Splits", ResultSplit),
        ("Total Configs", EventTotalConfig),
        ("Total Results", EventTotalResult),
    ]
    for label, model in tables:
        count = db.query(model).count()
        print(f"  {label:.<30} {count}")
    print("=" * 50)
    print("\nLogin credentials:")
    for i, u in enumerate(MAIN_USERS, 1):
        print(f"  {u['email']:.<30} password123")
    print("\nDone!")


def main():
    db = SessionLocal()
    try:
        clear_data(db)
        users = create_users(db)
        create_follows(db, users)
        clubs = create_clubs(db, users)
        create_memberships(db, clubs, users)
        events = create_events(db, users)
        create_participations(db, events, users)
        competitions = create_competitions(db, events)
        create_distances_and_cps(db, competitions)
        create_registrations(db, competitions, users)
        create_results(db, competitions, users)
        create_total_configs(db, events)
        db.commit()
        print_summary(db)
    except Exception as e:
        db.rollback()
        print(f"\nERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
