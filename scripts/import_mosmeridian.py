"""
Import MosMeridian Весенний сезон 2026 results into the Split Backend API.

Usage (from project root):
    poetry run python -m scripts.import_mosmeridian

What it does:
  1. Fetches 02.htm (2 Apr) and 03.htm (7 Apr) from mosmeridian.website.yandexcloud.net
  2. Parses results:
       - 3 distances with athletes per competition (D1/D2/D3 from WinOrient HTML)
       - "Выбор" distance created with no CPs (athletes not in WinOrient results)
       - Classes derived from gender (from Russian name heuristic) + birth year
  3. Logs in as organizer.
  4. Creates one Event + two Competitions (one per date).
  5. For each competition: creates 4 Distances (1/2/3/Выбор).
  6. For each athlete: searches DB by name first; creates account only if not found.
     Skips "аренда ММ" and "резерв" placeholder entries.
  7. Creates result with cumulative split times for athletes who finished.

Environment: API must be running at http://localhost:8000.
"""

import json as _json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

sys.path.insert(0, '.')

from app.parsers.mosmeridian import AthleteData, ClassData, CompetitionData, fetch_and_parse
from app.parsers.omephi import transliterate

API = 'http://localhost:8000'
ORGANIZER_LOGIN = 'user1@test.com'
ORGANIZER_PASSWORD = 'password123'

EVENT_NAME = 'Весенний сезон МС Меридиан 2026'
EVENT_LOCATION = 'Кузьминки, Москва'
COMPETITION_YEAR = 2026

# Competitions to import: (date, location, splits_url)
COMPETITIONS = [
    ('2026-04-02', 'Кузьминки (восток)', 'https://mosmeridian.website.yandexcloud.net/02.htm'),
    ('2026-04-07', 'Кузьминки (запад)',  'https://mosmeridian.website.yandexcloud.net/03.htm'),
]

# Distance name mapping from WinOrient course number → human-readable name
DISTANCE_NAMES = {'1': 'Длинная', '2': 'Средняя', '3': 'Короткая'}
# "Выбор" distance exists in every competition but has no WinOrient results
VYBOR_DISTANCE = 'Выбор'


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


# ── Auth ──────────────────────────────────────────────────────────────────────

def login() -> str:
    resp = post('/api/auth/login', {'login': ORGANIZER_LOGIN, 'password': ORGANIZER_PASSWORD})
    print(f'  Logged in as {ORGANIZER_LOGIN}')
    return resp['access_token']


# ── Event helpers ─────────────────────────────────────────────────────────────

def get_or_create_event(token: str) -> int:
    dates = [d for d, _, __ in COMPETITIONS]
    start_date, end_date = dates[0], dates[-1]
    try:
        event = post('/api/events', {
            'name': EVENT_NAME,
            'start_date': start_date,
            'end_date': end_date,
            'location': EVENT_LOCATION,
            'sport_kind': 'orient',
            'event_format': 'multi_stage',
            'privacy': 'public',
            'status': 'planned',
        }, token)
        return event['id']
    except RuntimeError as e:
        if '409' not in str(e):
            raise
        resp = get('/api/events?limit=100', token)
        all_events = resp if isinstance(resp, list) else resp.get('events', resp.get('items', []))
        existing = next((ev for ev in all_events if ev.get('name') == EVENT_NAME), None)
        if not existing:
            raise RuntimeError(f'Event conflict but not found: {EVENT_NAME}') from e
        return existing['id']


# ── User helpers ──────────────────────────────────────────────────────────────

def _make_username(athlete: AthleteData) -> str:
    last = re.sub(r'[^a-z0-9]', '', transliterate(athlete.last_name).lower())
    first_init = re.sub(r'[^a-z0-9]', '', transliterate(athlete.first_name).lower())[:2]
    bib = re.sub(r'[^a-z0-9]', '', athlete.bib_number.lower()) if athlete.bib_number else 'x'
    return f'{last}_{first_init}_{bib}'[:50]


def _search_user_by_name(last_name: str, first_name: str, token: str) -> int:
    """
    Search for an existing user by first and last name.
    Returns user_id or -1 if not found.
    """
    query = f'{last_name} {first_name}'.strip()
    if not query:
        return -1
    try:
        resp = get(f'/api/users?q={urllib.parse.quote(query)}&limit=10', token)
        users = resp.get('users', [])
        for u in users:
            u_last = (u.get('last_name') or '').strip().upper()
            u_first = (u.get('first_name') or '').strip()
            if u_last == last_name.strip().upper() and u_first.lower().startswith(first_name[:1].lower()):
                return u['id']
    except RuntimeError:
        pass
    return -1


def get_or_create_user(athlete: AthleteData, token: str, cache: dict) -> int:
    """
    Find or create a user for the athlete.
    Cache is keyed by bib_number to avoid redundant lookups within one competition.
    Returns user_id or -1 on failure.
    """
    cache_key = f'{athlete.last_name}_{athlete.first_name}_{athlete.bib_number}'
    if cache_key in cache:
        return cache[cache_key]

    # 1. Search DB by name first
    uid = _search_user_by_name(athlete.last_name, athlete.first_name, token)
    if uid != -1:
        print(f'    Found existing user for {athlete.full_name} (id={uid})')
        cache[cache_key] = uid
        return uid

    # 2. Try to register new account
    username = _make_username(athlete)
    password = f'orient{athlete.bib_number or "000"}!'

    for attempt_username in [username, f'{username}_{athlete.bib_number}'[:50]]:
        try:
            resp = post('/api/auth/register', {
                'username': attempt_username,
                'password': password,
                'first_name': athlete.first_name or athlete.last_name,
                'last_name': athlete.last_name if athlete.first_name else None,
            })
            uid = resp['user']['id']
            cache[cache_key] = uid
            return uid
        except RuntimeError as e:
            err = str(e)
            if 'already' in err.lower() or '422' in err:
                continue
            print(f'    ⚠ Cannot create user for {athlete.full_name}: {e}')
            return -1

    # Both usernames taken — try lookup by transliterated username
    try:
        resp = get(f'/api/users?q={urllib.parse.quote(username)}&limit=10', token)
        for u in resp.get('users', []):
            if u.get('username_display') == username:
                uid = u['id']
                cache[cache_key] = uid
                return uid
    except RuntimeError:
        pass

    print(f'    ⚠ Cannot resolve user for {athlete.full_name} ({username})')
    return -1


# ── Distance creation ─────────────────────────────────────────────────────────

def _suffixed_class(age_gender_class: str, course_num: str) -> str:
    """
    Make a class name unique per distance by appending the course number.
    e.g. 'М21' + '2' → 'М21-2'
    This avoids class collisions across distances (same age class can run any distance).
    """
    return f'{age_gender_class}-{course_num}'


def create_distances(competition_id: int, classes: list[ClassData], token: str) -> dict[str, int]:
    """
    Create one Distance per ClassData (D1/D2/D3) plus the empty "Выбор" distance.
    Class names are suffixed with course number to be globally unique within the competition
    (e.g. М21-1, М21-2, М21-3 for M21 athletes choosing different distances).
    Returns class_data.name (e.g. 'D1') → distance_id mapping.
    """
    class_to_dist: dict[str, int] = {}

    for cls in classes:
        course_num = cls.name.lstrip('D')  # '1', '2', '3'
        dist_name = DISTANCE_NAMES.get(course_num, cls.name)

        # Suffix each class to make it unique within this competition
        unique_classes = sorted({_suffixed_class(a.competition_class, course_num) for a in cls.athletes})

        body = {
            'name': dist_name,
            'distance_meters': cls.distance_meters,
            'classes': unique_classes,
            'control_points': [{'code': cp} for cp in cls.control_points],
        }
        resp = post(f'/api/competitions/{competition_id}/distances', body, token)
        dist_id = resp['id']
        class_to_dist[cls.name] = dist_id
        print(f'  Distance {dist_name} (id={dist_id}): {len(cls.control_points)} CPs, '
              f'{len(unique_classes)} classes, {len(cls.athletes)} athletes')

    # Create empty "Выбор" distance — no fixed CPs, classes defined ad-hoc
    resp = post(f'/api/competitions/{competition_id}/distances', {
        'name': VYBOR_DISTANCE,
        'distance_meters': 1500,
        'classes': [],
        'control_points': [],
    }, token)
    class_to_dist[VYBOR_DISTANCE] = resp['id']
    print(f'  Distance {VYBOR_DISTANCE} (id={resp["id"]}): empty — athletes added manually')

    return class_to_dist


# ── Result import ─────────────────────────────────────────────────────────────

def import_athletes(
    competition_id: int,
    event_id: int,
    comp_data: CompetitionData,
    token: str,
) -> tuple[int, int]:
    user_cache: dict[str, int] = {}
    imported = skipped = 0

    for cls in comp_data.classes:
        course_num = cls.name.lstrip('D')
        print(f'  Distance D{course_num} ({len(cls.athletes)} athletes)...')

        for athlete in cls.athletes:
            uid = get_or_create_user(athlete, token, user_cache)
            if uid == -1:
                skipped += 1
                continue

            # Unique class name for this distance
            suffixed_class = _suffixed_class(athlete.competition_class, course_num)

            # Event participant
            try:
                post(f'/api/events/{event_id}/participants', {'user_id': uid, 'role': 'participant'}, token)
            except RuntimeError:
                pass  # already a participant

            # Competition registration with suffixed class
            try:
                post(f'/api/competitions/{competition_id}/registrations', {
                    'user_id': uid,
                    'class': suffixed_class,
                    'bib_number': athlete.bib_number,
                }, token)
            except RuntimeError as e:
                if 'already registered' not in str(e).lower():
                    print(f'    ⚠ Registration failed for {athlete.full_name}: {e}')
                    skipped += 1
                    continue

            # Result payload
            result_body: dict = {
                'user_id': uid,
                'class': athlete.competition_class,
                'status': athlete.status,
            }
            if athlete.time_ms is not None:
                result_body['time_total'] = athlete.time_ms

            # Include splits only when complete and validated
            if athlete.splits and athlete.status == 'ok' and athlete.time_ms is not None:
                actual_cps = [s.control_point for s in athlete.splits]
                if actual_cps == cls.control_points:
                    result_body['splits'] = (
                        [{'control_point': 'start', 'cumulative_time': 0}]
                        + [{'control_point': s.control_point, 'cumulative_time': s.cumulative_time_ms}
                           for s in athlete.splits]
                        + [{'control_point': 'finish', 'cumulative_time': athlete.time_ms}]
                    )

            try:
                post(f'/api/competitions/{competition_id}/results', result_body, token)
                imported += 1
            except RuntimeError as e:
                print(f'    ⚠ Result failed for {athlete.full_name}: {e}')
                skipped += 1

    return imported, skipped


# ── Main ──────────────────────────────────────────────────────────────────────

def run() -> None:
    # 1. Fetch and parse both competitions
    print('Fetching and parsing results...')
    parsed: list[tuple[str, CompetitionData]] = []  # (location, CompetitionData)
    for date, location, url in COMPETITIONS:
        print(f'  {date} ({location}): {url}')
        comp_data = fetch_and_parse(url, date=date, location=location, competition_year=COMPETITION_YEAR)
        total = sum(len(c.athletes) for c in comp_data.classes)
        print(f'    → {len(comp_data.classes)} distances, {total} athletes')
        parsed.append((location, comp_data))

    # 2. Login
    print('\nLogging in...')
    token = login()

    # 3. Create or find event
    print(f'\nCreating event: {EVENT_NAME}')
    event_id = get_or_create_event(token)
    print(f'  Event id={event_id}')

    # 4. One competition per date
    for location, comp_data in parsed:
        date = comp_data.date
        comp_name = f'МС Меридиан {date}'
        print(f'\n=== Competition: {comp_name} ===')

        comp = post(f'/api/events/{event_id}/competitions', {
            'name': comp_name,
            'date': date,
            'location': location,
            'sport_kind': 'orient',
            'start_format': 'free',
            'start_time': f'{date}T17:00:00',
        }, token)
        competition_id = comp['id']
        print(f'  Competition id={competition_id}')

        # Advance status to finished
        for status in ('registration_open', 'registration_closed', 'in_progress', 'finished'):
            try:
                patch(f'/api/events/{event_id}/competitions/{competition_id}', {'status': status}, token)
            except RuntimeError as e:
                print(f'  Status {status!r} skipped: {e}')
                break

        # Create distances
        print('  Creating distances...')
        create_distances(competition_id, comp_data.classes, token)

        # Import athletes
        print('  Importing athletes...')
        imp, skip = import_athletes(competition_id, event_id, comp_data, token)
        print(f'  → imported={imp}, skipped={skip}')

    print('\nAll done.')
    print(f'Event: {API}/api/events/{event_id}')


if __name__ == '__main__':
    run()
