"""
Import Gelendjik camp results (Протокол А/В/С1/С2 PDFs) into the Split Backend API.

Usage (from project root):
    poetry run python -m scripts.import_gelendjik [directory]

    directory defaults to ../data/archive

Structure produced:
  1 Event  — "Сборы Геленджик 2026"
  N Competitions — one per day found in the file names (e.g. 29.03, 30.03)
  4 Distances per competition — А, В, С1, С2 (each has its own CP sequence)
  Age classes — М10…М65, Ж10…Ж65 derived from birth year; assigned to their distance

Environment: API must be running at http://localhost:8000.
"""

import json as _json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

sys.path.insert(0, '.')

from app.parsers.gelendjik import (
    AthleteData, ClassData, CompetitionData, parse_protocol_pdf
)
from app.parsers.omephi import transliterate

API = 'http://localhost:8000'
ORGANIZER_LOGIN = 'user1@test.com'
ORGANIZER_PASSWORD = 'password123'

DEFAULT_DATA_DIR = Path(__file__).parent.parent.parent / 'data' / 'archive'

EVENT_NAME = 'Сборы Геленджик 2026'
EVENT_START = '2026-03-29'
EVENT_END   = '2026-03-30'

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


def get(path, token=None): return _request('GET', path, token)
def post(path, body, token=None): return _request('POST', path, token, body)
def patch(path, body, token=None): return _request('PATCH', path, token, body)


# ── Auth ──────────────────────────────────────────────────────────────────────

def login() -> str:
    resp = post('/api/auth/login', {'login': ORGANIZER_LOGIN, 'password': ORGANIZER_PASSWORD})
    print(f'  Logged in as {ORGANIZER_LOGIN}')
    return resp['access_token']


# ── Event helpers ─────────────────────────────────────────────────────────────

def get_or_create_event(name: str, start_date: str, end_date: str, token: str) -> int:
    try:
        event = post('/api/events', {
            'name': name,
            'start_date': start_date,
            'end_date': end_date,
            'location': 'Геленджик',
            'sport_kind': 'orient',
            'event_format': 'multi_stage',
            'privacy': 'public',
            'status': 'planned',
        }, token)
        return event['id']
    except RuntimeError as e:
        if '409' not in str(e):
            raise
        events_resp = get('/api/events?limit=100', token)
        all_events = (
            events_resp if isinstance(events_resp, list)
            else events_resp.get('events', events_resp.get('items', []))
        )
        existing = next((ev for ev in all_events if ev.get('name') == name), None)
        if not existing:
            raise RuntimeError(f'Event exists but could not be found: {name}') from e
        return existing['id']


# ── User creation ─────────────────────────────────────────────────────────────

def _make_username(athlete: AthleteData) -> str:
    last = re.sub(r'[^a-z0-9]', '', transliterate(athlete.last_name).lower())
    first_init = re.sub(r'[^a-z0-9]', '', transliterate(athlete.first_name).lower())[:2]
    return f'{last}_{first_init}_{athlete.bib_number}'[:50]


def _lookup_user_by_username(username: str, token: str) -> int:
    """Search for an existing user by exact username. Returns user_id or -1."""
    try:
        resp = get(f'/api/users?q={username}', token)
        for u in resp.get('users', []):
            if u.get('username_display') == username:
                return u['id']
    except RuntimeError:
        pass
    return -1


def get_or_create_user(athlete: AthleteData, token: str, cache: dict) -> int:
    """cache is a per-protocol dict keyed by bib_number."""
    if athlete.bib_number in cache:
        return cache[athlete.bib_number]

    username = _make_username(athlete)
    password = f'orient{athlete.bib_number}!'
    candidates = [username, f'{username}x{athlete.bib_number}']

    for attempt, uname in enumerate(candidates):
        try:
            resp = post('/api/auth/register', {
                'username': uname,
                'password': password,
                'first_name': athlete.first_name or athlete.last_name,
                'last_name': athlete.last_name if athlete.first_name else None,
            })
            uid = resp['user']['id']
            cache[athlete.bib_number] = uid
            return uid
        except RuntimeError as e:
            if 'already' in str(e).lower() or '422' in str(e):
                continue
            print(f'    ⚠ Cannot create user for {athlete.full_name}: {e}')
            return -1

    # Both usernames taken — find the existing account by the primary username
    uid = _lookup_user_by_username(username, token)
    if uid != -1:
        cache[athlete.bib_number] = uid
        return uid

    print(f'    ⚠ Cannot resolve user for {athlete.full_name} ({username})')
    return -1


# ── Distance creation ─────────────────────────────────────────────────────────

def _proto_class(class_name: str, protocol: str) -> str:
    """Append protocol letter to class name to make it unique: 'М21' + 'А' → 'М21А'."""
    return f'{class_name}{protocol}'


def _proto_bib(bib: str, protocol: str) -> str:
    """Prefix bib with protocol letter to avoid collisions: '1' + 'А' → 'А1'."""
    return f'{protocol}{bib}'


def create_distance(
    competition_id: int,
    protocol: str,
    classes: list[ClassData],
    token: str,
) -> int:
    """Create one distance for a protocol (А/В/С1/С2). Returns distance_id."""
    cp_list = classes[0].control_points if classes else []
    # Class names are suffixed with protocol to be unique within the competition
    class_names = [_proto_class(c.name, protocol) for c in classes]

    body = {
        'name': protocol,
        'distance_meters': None,
        'classes': class_names,
        'control_points': [{'code': cp} for cp in cp_list],
    }
    resp = post(f'/api/competitions/{competition_id}/distances', body, token)
    dist_id = resp['id']
    print(f'  Distance {protocol} (id={dist_id}): {len(cp_list)} CPs, classes: {", ".join(class_names)}')
    return dist_id


# ── Result import ─────────────────────────────────────────────────────────────

def import_athletes(
    competition_id: int,
    event_id: int,
    comp_data: CompetitionData,
    token: str,
) -> tuple[int, int]:
    """Import all athletes from a parsed protocol. Returns (imported, skipped)."""
    # Per-protocol user cache — bibs are NOT unique across different protocols
    user_cache: dict[str, int] = {}
    protocol = comp_data.protocol

    imported = skipped = 0
    for cls in comp_data.classes:
        comp_class = _proto_class(cls.name, protocol)   # e.g. "М21А"

        for athlete in cls.athletes:
            uid = get_or_create_user(athlete, token, user_cache)
            if uid == -1:
                skipped += 1
                continue

            # Event participant
            try:
                post(f'/api/events/{event_id}/participants', {'user_id': uid, 'role': 'participant'}, token)
            except RuntimeError:
                pass

            # Competition registration — bib prefixed to avoid cross-protocol collisions
            proto_bib = _proto_bib(athlete.bib_number, protocol)
            try:
                post(f'/api/competitions/{competition_id}/registrations', {
                    'user_id': uid,
                    'class': comp_class,
                    'bib_number': proto_bib,
                }, token)
            except RuntimeError as e:
                if 'already registered' not in str(e).lower():
                    print(f'    ⚠ Registration failed for {athlete.full_name}: {e}')
                    skipped += 1
                    continue

            # Result
            result_body: dict = {
                'user_id': uid,
                'class': comp_class,
                'status': athlete.status,
            }
            if athlete.time_ms is not None:
                result_body['time_total'] = athlete.time_ms

            if athlete.splits and athlete.status == 'ok' and athlete.time_ms is not None:
                if [s.control_point for s in athlete.splits] == cls.control_points:
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

def run(data_dirs: list[Path]) -> None:
    # Collect all protocol PDFs from all dirs
    all_files: list[Path] = []
    for d in data_dirs:
        all_files.extend(sorted(d.glob('Протокол *.pdf')))

    if not all_files:
        print('No protocol PDFs found')
        return

    print(f'Found {len(all_files)} protocol files')

    # Parse all PDFs; group by date
    by_date: dict[str, dict[str, CompetitionData]] = {}  # date → {protocol → CompetitionData}
    for pdf_path in all_files:
        print(f'Parsing {pdf_path.name}...')
        comp_data = parse_protocol_pdf(pdf_path)
        total = sum(len(c.athletes) for c in comp_data.classes)
        print(f'  → protocol={comp_data.protocol}, {len(comp_data.classes)} classes, {total} athletes, {len(comp_data.classes[0].control_points) if comp_data.classes else 0} CPs')
        by_date.setdefault(comp_data.date, {})[comp_data.protocol] = comp_data

    # Login
    print('\nLogging in...')
    token = login()

    # Create single event spanning all dates
    dates = sorted(by_date.keys())
    print(f'\nCreating event: {EVENT_NAME}')
    event_id = get_or_create_event(EVENT_NAME, dates[0], dates[-1], token)
    print(f'  Event id={event_id}')

    # One competition per day
    for date in dates:
        protocols = by_date[date]
        comp_name = f'Геленджик {date}'
        print(f'\n=== Competition: {comp_name} ===')

        comp = post(f'/api/events/{event_id}/competitions', {
            'name': comp_name,
            'date': date,
            'location': 'Геленджик',
            'sport_kind': 'orient',
            'start_format': 'mass_start',
            'start_time': f'{date}T10:00:00',
        }, token)
        competition_id = comp['id']
        print(f'  Competition id={competition_id}')

        # Advance status as far as possible
        for status in ('registration_open', 'registration_closed', 'in_progress', 'finished'):
            try:
                patch(f'/api/events/{event_id}/competitions/{competition_id}', {'status': status}, token)
            except RuntimeError as e:
                print(f'  Status {status!r} skipped: {e}')
                break

        # Create one distance per protocol (А → В → С1 → С2)
        for protocol in ('А', 'В', 'С1', 'С2'):
            comp_data = protocols.get(protocol)
            if not comp_data:
                continue

            create_distance(competition_id, protocol, comp_data.classes, token)

        # Import athletes (per protocol, with separate bib caches)
        total_imported = total_skipped = 0
        for protocol in ('А', 'В', 'С1', 'С2'):
            comp_data = protocols.get(protocol)
            if not comp_data:
                continue
            print(f'  Importing protocol {protocol}...')
            imp, skip = import_athletes(competition_id, event_id, comp_data, token)
            total_imported += imp
            total_skipped += skip
            print(f'    → imported={imp}, skipped={skip}')

        print(f'  Total: imported={total_imported}, skipped={total_skipped}')

    print('\nAll done.')


if __name__ == '__main__':
    if len(sys.argv) > 1:
        dirs = [Path(p) for p in sys.argv[1:]]
    else:
        dirs = [DEFAULT_DATA_DIR]
    run(dirs)
