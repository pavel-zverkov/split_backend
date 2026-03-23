"""
Import an o-mephi.net competition into the Split Backend API.

Usage (from project root):
    poetry run python -m scripts.import_omephi

What it does:
  1. Parses the splits HTML page (contains all results + split times).
  2. Logs in as organizer1 (user1@test.com / password123).
  3. Creates an Event + Competition.
  4. Groups classes by identical CP-sequence → creates one Distance per group.
  5. For every athlete: creates a user account, adds a competition registration,
     then creates a result with cumulative split times.

Environment: API must be running at http://localhost:8000.
"""

import re
import sys
import time
import urllib.request
import urllib.error
import json as _json
from dataclasses import dataclass, field
from typing import Optional

sys.path.insert(0, '.')

from app.parsers.omephi import CompetitionData, ClassData, AthleteData, parse_splits_html, transliterate

API = 'http://localhost:8000'
SPLITS_URL = 'https://o-mephi.net/cup/prot/8marta2026_spl.htm'

ORGANIZER_LOGIN = 'organizer1'
ORGANIZER_PASSWORD = 'organizer1'

# Competition details parsed from the event page
EVENT_NAME = 'ХI Традиционные соревнования, посвящённые Международному Женскому Дню 8 марта'
COMP_DATE = '2026-03-08'
COMP_LOCATION = 'Борисово-Городня'
COMP_START_TIME = '2026-03-08T10:00:00'


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _request(method: str, path: str, token: Optional[str] = None, body=None) -> dict:
    url = API + path
    data = _json.dumps(body).encode() if body is not None else None
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return _json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        body_bytes = e.read()
        try:
            detail = _json.loads(body_bytes).get('detail', body_bytes.decode())
        except Exception:
            detail = body_bytes.decode()
        raise RuntimeError(f'HTTP {e.code} {method} {path}: {detail}') from e


def get(path, token=None):
    return _request('GET', path, token)

def post(path, body, token=None):
    return _request('POST', path, token, body)

def patch(path, body, token=None):
    return _request('PATCH', path, token, body)


# ── Login ─────────────────────────────────────────────────────────────────────

def login() -> str:
    resp = post('/api/auth/login', {'login': ORGANIZER_LOGIN, 'password': ORGANIZER_PASSWORD})
    token = resp['access_token']
    print(f'  Logged in as {ORGANIZER_LOGIN}')
    return token


# ── User creation ─────────────────────────────────────────────────────────────

def _make_username(athlete: AthleteData) -> str:
    """Generate a unique username from transliterated name + bib."""
    last = re.sub(r'[^a-z0-9]', '', transliterate(athlete.last_name).lower())
    first_init = re.sub(r'[^a-z0-9]', '', transliterate(athlete.first_name).lower())[:2]
    return f'{last}_{first_init}_{athlete.bib_number}'[:50]


_user_cache: dict[str, int] = {}  # bib_number → user_id


def get_or_create_user(athlete: AthleteData, token: str) -> int:
    if athlete.bib_number in _user_cache:
        return _user_cache[athlete.bib_number]

    username = _make_username(athlete)
    password = f'orient{athlete.bib_number}!'

    # Try to register
    try:
        resp = post('/api/auth/register', {
            'username': username,
            'password': password,
            'first_name': athlete.first_name or athlete.last_name,
            'last_name': athlete.last_name if athlete.first_name else None,
        })
        user_id = resp['user']['id']
        _user_cache[athlete.bib_number] = user_id
        return user_id
    except RuntimeError as e:
        if '422' in str(e) or 'already' in str(e).lower() or 'username' in str(e).lower():
            # Username collision: append more bib digits
            username2 = f'{username}_{athlete.bib_number}'[:50]
            try:
                resp = post('/api/auth/register', {
                    'username': username2,
                    'password': password,
                    'first_name': athlete.first_name or athlete.last_name,
                    'last_name': athlete.last_name if athlete.first_name else None,
                })
                user_id = resp['user']['id']
                _user_cache[athlete.bib_number] = user_id
                return user_id
            except RuntimeError as e2:
                print(f'    ⚠ Could not create user for {athlete.full_name} ({athlete.bib_number}): {e2}')
                return -1
        print(f'    ⚠ Could not create user for {athlete.full_name}: {e}')
        return -1


# ── Distance creation ─────────────────────────────────────────────────────────

def create_distances(competition_id: int, classes: list[ClassData], token: str) -> dict[str, int]:
    """
    Group classes by CP sequence, create one Distance per group.
    Returns a map of class_name → distance_id.
    """
    # Group by tuple of ordered CPs
    groups: dict[tuple, list[ClassData]] = {}
    for cls in classes:
        key = tuple(cls.control_points)
        groups.setdefault(key, []).append(cls)

    class_to_distance: dict[str, int] = {}

    for i, (cp_key, group_classes) in enumerate(groups.items(), start=1):
        class_names = [c.name for c in group_classes]
        dist_m = next((c.distance_meters for c in group_classes if c.distance_meters), None)

        body = {
            'name': f'D{i}',
            'distance_meters': dist_m,
            'classes': class_names,
            'control_points': [{'code': cp} for cp in cp_key],
        }
        resp = post(f'/api/competitions/{competition_id}/distances', body, token)
        dist_id = resp['id']
        for cn in class_names:
            class_to_distance[cn] = dist_id
        print(f'  Distance D{i} (id={dist_id}): {", ".join(class_names)} | {len(cp_key)} CPs')

    return class_to_distance


# ── Main import ───────────────────────────────────────────────────────────────

def run():
    # 1. Fetch and parse splits page
    print('Fetching splits page...')
    with urllib.request.urlopen(SPLITS_URL) as resp:
        html_bytes = resp.read()
    comp_data = parse_splits_html(html_bytes)

    total_athletes = sum(len(c.athletes) for c in comp_data.classes)
    print(f'  Parsed {len(comp_data.classes)} classes, {total_athletes} athletes')

    # 2. Login
    print('Logging in...')
    token = login()

    # 3. Create Event
    print('Creating event...')
    event = post('/api/events', {
        'name': EVENT_NAME,
        'start_date': COMP_DATE,
        'end_date': COMP_DATE,
        'location': COMP_LOCATION,
        'sport_kind': 'orient',
        'event_format': 'multi_stage',
        'privacy': 'public',
        'status': 'planned',
    }, token)
    event_id = event['id']
    print(f'  Event id={event_id}: {EVENT_NAME}')

    # 4. Create Competition
    print('Creating competition...')
    comp = post(f'/api/events/{event_id}/competitions', {
        'name': EVENT_NAME,
        'date': COMP_DATE,
        'location': COMP_LOCATION,
        'sport_kind': 'orient',
        'start_format': 'mass_start',
        'start_time': COMP_START_TIME,
    }, token)
    competition_id = comp['id']
    print(f'  Competition id={competition_id}')

    # 5. Walk status to finished: planned → reg_open → reg_closed → in_progress → finished
    for new_status in ('registration_open', 'registration_closed', 'in_progress', 'finished'):
        patch(f'/api/events/{event_id}/competitions/{competition_id}', {'status': new_status}, token)
    print(f'  Competition status → finished')

    # 6. Create distances (grouped by CP sequence)
    print('Creating distances...')
    class_to_distance = create_distances(competition_id, comp_data.classes, token)

    # 7. Add event participant (organizer already counted), then per-athlete
    print('Importing athletes...')
    imported = 0
    skipped = 0

    for cls in comp_data.classes:
        if not cls.athletes:
            continue
        print(f'  Class {cls.name} ({len(cls.athletes)} athletes)...')

        for athlete in cls.athletes:
            # Create user
            user_id = get_or_create_user(athlete, token)
            if user_id == -1:
                skipped += 1
                continue

            # Add participant to event
            try:
                post(f'/api/events/{event_id}/participants', {
                    'user_id': user_id,
                    'role': 'participant',
                }, token)
            except RuntimeError:
                pass  # already a participant

            # Register for competition (with bib number)
            try:
                post(f'/api/competitions/{competition_id}/registrations', {
                    'user_id': user_id,
                    'class': athlete.competition_class,
                    'bib_number': athlete.bib_number,
                }, token)
            except RuntimeError as e:
                if 'already registered' not in str(e).lower():
                    print(f'    ⚠ Registration failed for {athlete.full_name}: {e}')
                    skipped += 1
                    continue

            # Build result payload
            result_body: dict = {
                'user_id': user_id,
                'class': athlete.competition_class,
                'status': athlete.status,
            }
            if athlete.time_ms is not None:
                result_body['time_total'] = athlete.time_ms

            # Include splits for finished athletes whose splits are complete.
            # The distance adds start (cum=0) and finish (cum=total) automatically,
            # so we wrap our intermediate CPs with those two endpoints.
            if athlete.splits and athlete.status == 'ok' and athlete.time_ms is not None:
                expected_cps = cls.control_points
                actual_cps = [s.control_point for s in athlete.splits]
                if actual_cps == expected_cps:
                    result_body['splits'] = (
                        [{'control_point': 'start', 'cumulative_time': 0}]
                        + [{'control_point': s.control_point, 'cumulative_time': s.cumulative_time_ms}
                           for s in athlete.splits]
                        + [{'control_point': 'finish', 'cumulative_time': athlete.time_ms}]
                    )

            # Create result
            try:
                post(f'/api/competitions/{competition_id}/results', result_body, token)
                imported += 1
            except RuntimeError as e:
                print(f'    ⚠ Result failed for {athlete.full_name}: {e}')
                skipped += 1

    print(f'\nDone. Imported: {imported}, Skipped: {skipped}')
    print(f'Event: {API}/api/events/{event_id}')
    print(f'Competition: {API}/api/competitions/{competition_id}')


if __name__ == '__main__':
    run()
