"""
Import an orgeo.ru live competition into the Split Backend API.

Usage (from project root):
    poetry run python -m scripts.import_orgeo 51922 2
    poetry run python -m scripts.import_orgeo 51922 2 --cached   # read /tmp/orgeo/*.json

What it does:
  1. Fetches /online/top/ + /online/finish/?d=<group> for every group of the requested
     event/sub (or reads them from /tmp/orgeo/ when --cached is passed).
  2. Logs in as the organizer account.
  3. Creates (or finds) one Event for orgeo event_id, one Competition for sub_id.
  4. Creates one Distance per group (group name → distance name, with that group as the
     single class). Control points come from the most common CP sequence among finishers.
  5. For each athlete: looks up by name; registers an account if no match.
  6. Registers the athlete in the competition and posts the result (with cumulative
     splits for ok finishers whose own CP sequence matches the group reference).

Environment: API must be running at http://localhost:8000.
"""

from __future__ import annotations

import json as _json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

sys.path.insert(0, '.')

from app.parsers.orgeo import (
    AthleteData, ClassData, CompetitionData, TopMeta,
    fetch_top, fetch_finish, parse_top_meta, parse_group_finish,
)
from app.parsers.omephi import transliterate

API = 'http://localhost:8000'
ORGANIZER_LOGIN = 'user1@test.com'
ORGANIZER_PASSWORD = 'password123'

DEFAULT_LOCATION = 'Москва, Битцевский лес'
CACHE_DIR = Path('/tmp/orgeo')


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


def get(path, token=None):  return _request('GET',   path, token)
def post(path, body, token=None):  return _request('POST',  path, token, body)
def patch(path, body, token=None): return _request('PATCH', path, token, body)


# ── Auth ──────────────────────────────────────────────────────────────────────

def login() -> str:
    resp = post('/api/auth/login', {'login': ORGANIZER_LOGIN, 'password': ORGANIZER_PASSWORD})
    print(f'  Logged in as {ORGANIZER_LOGIN}')
    return resp['access_token']


# ── Event / competition helpers ───────────────────────────────────────────────

def get_or_create_event(name: str, start_date: str, end_date: str, location: str, token: str) -> int:
    try:
        ev = post('/api/events', {
            'name': name,
            'start_date': start_date,
            'end_date': end_date,
            'location': location,
            'sport_kind': 'orient',
            'event_format': 'multi_stage',
            'privacy': 'public',
            'status': 'planned',
        }, token)
        return ev['id']
    except RuntimeError as e:
        if '409' not in str(e):
            raise
        resp = get('/api/events?limit=100', token)
        all_events = resp if isinstance(resp, list) else resp.get('events', resp.get('items', []))
        existing = next((ev for ev in all_events if ev.get('name') == name), None)
        if not existing:
            raise RuntimeError(f'Event conflict but not found: {name}') from e
        # Widen date range if this stage extends beyond the recorded span
        cur_start = (existing.get('start_date') or '')[:10]
        cur_end   = (existing.get('end_date')   or '')[:10]
        new_start = min(cur_start, start_date) if cur_start else start_date
        new_end   = max(cur_end,   end_date)   if cur_end   else end_date
        if (cur_start, cur_end) != (new_start, new_end):
            try:
                patch(f'/api/events/{existing["id"]}', {
                    'start_date': new_start,
                    'end_date': new_end,
                }, token)
                print(f'  Event dates widened: {cur_start}…{cur_end} → {new_start}…{new_end}')
            except RuntimeError as pe:
                print(f'  (could not widen event dates: {pe})')
        return existing['id']


def get_or_create_competition(event_id: int, name: str, date: str, start_time: str, location: str, token: str) -> int:
    body = {
        'name': name,
        'date': date,
        'location': location,
        'sport_kind': 'orient',
        'start_format': 'separated_start',
        'start_time': f'{date}T{start_time}',
    }
    try:
        return post(f'/api/events/{event_id}/competitions', body, token)['id']
    except RuntimeError as e:
        if '409' not in str(e):
            raise
        resp = get(f'/api/events/{event_id}/competitions', token)
        comps = resp if isinstance(resp, list) else resp.get('competitions', resp.get('items', []))
        existing = next((c for c in comps if c.get('name') == name), None)
        if not existing:
            raise RuntimeError(f'Competition conflict but not found: {name}') from e
        return existing['id']


# ── Users ─────────────────────────────────────────────────────────────────────

def _make_username(athlete: AthleteData) -> str:
    last = re.sub(r'[^a-z0-9]', '', transliterate(athlete.last_name).lower())
    first_init = re.sub(r'[^a-z0-9]', '', transliterate(athlete.first_name).lower())[:2]
    bib = re.sub(r'[^a-z0-9]', '', athlete.bib_number.lower()) if athlete.bib_number else 'x'
    return f'{last}_{first_init}_{bib}'[:50]


def _search_user_by_name(last_name: str, first_name: str, token: str) -> int:
    query = f'{last_name} {first_name}'.strip()
    if not query:
        return -1
    try:
        resp = get(f'/api/users?q={urllib.parse.quote(query)}&limit=10', token)
        for u in resp.get('users', []):
            u_last  = (u.get('last_name')  or '').strip().upper()
            u_first = (u.get('first_name') or '').strip()
            if u_last == last_name.strip().upper() and u_first.lower().startswith(first_name[:1].lower()):
                return u['id']
    except RuntimeError:
        pass
    return -1


def get_or_create_user(athlete: AthleteData, token: str, cache: dict) -> int:
    key = f'{athlete.last_name}_{athlete.first_name}_{athlete.bib_number}'
    if key in cache:
        return cache[key]

    uid = _search_user_by_name(athlete.last_name, athlete.first_name, token)
    if uid != -1:
        cache[key] = uid
        return uid

    username = _make_username(athlete)
    password = f'orient{athlete.bib_number or "000"}!'
    for attempt in (username, f'{username}_{athlete.bib_number}'[:50]):
        try:
            resp = post('/api/auth/register', {
                'username': attempt,
                'password': password,
                'first_name': athlete.first_name or athlete.last_name,
                'last_name': athlete.last_name if athlete.first_name else None,
            })
            uid = resp['user']['id']
            cache[key] = uid
            return uid
        except RuntimeError as e:
            err = str(e).lower()
            if 'already' in err or '422' in err:
                continue
            print(f'    ⚠ Cannot create user for {athlete.full_name}: {e}')
            return -1

    print(f'    ⚠ Cannot resolve user for {athlete.full_name} ({username})')
    return -1


# ── Distances ─────────────────────────────────────────────────────────────────

def _group_classes_by_cps(classes: list[ClassData]) -> list[list[ClassData]]:
    """
    Group ClassData entries that share the same control-point sequence
    (= same physical course). Returns groups in input order; within each
    group the original order is preserved.
    """
    buckets: dict[tuple, list[ClassData]] = {}
    order: list[tuple] = []
    for cls in classes:
        key = tuple(cls.control_points)
        if not key:
            # Empty CP list (no finishers found) — keep as singleton bucket on cls.name
            key = ('__nocp__', cls.name)
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(cls)
    return [buckets[k] for k in order]


def create_distance_for_group(competition_id: int, bucket: list[ClassData], token: str) -> int:
    """
    Create one Distance for a bucket of ClassData entries sharing the same course.
    The Distance is named with all class names joined ('/'), and its `classes`
    field carries every group name (so per-athlete registrations can pick one).
    """
    ref = bucket[0]
    class_names = [c.name for c in bucket]
    dist_name = ' / '.join(class_names)

    body = {
        'name': dist_name,
        'distance_meters': ref.distance_meters,
        'classes': class_names,
        'control_points': [{'code': cp} for cp in ref.control_points],
    }
    resp = post(f'/api/competitions/{competition_id}/distances', body, token)
    print(f'  Distance {dist_name!r} (id={resp["id"]}): {len(ref.control_points)} CPs, '
          f'classes={class_names}, athletes={sum(len(c.athletes) for c in bucket)}')
    return resp['id']


# ── Result import ─────────────────────────────────────────────────────────────

def import_athletes(competition_id: int, event_id: int, comp: CompetitionData, token: str) -> tuple[int, int]:
    user_cache: dict[str, int] = {}
    results_posted: set[int] = set()      # uids that already have a result in this competition
    imported = skipped = 0

    for cls in comp.classes:
        print(f'  → {cls.name} ({len(cls.athletes)} athletes)')
        for athlete in cls.athletes:
            uid = get_or_create_user(athlete, token, user_cache)
            if uid == -1:
                skipped += 1
                continue

            # Event participant (idempotent)
            try:
                post(f'/api/events/{event_id}/participants', {'user_id': uid, 'role': 'participant'}, token)
            except RuntimeError:
                pass

            # Competition registration
            reg_body: dict = {
                'user_id': uid,
                'class': athlete.competition_class,
                'bib_number': athlete.bib_number,
            }
            if athlete.start_clock_time:
                reg_body['start_time'] = f'{comp.date}T{athlete.start_clock_time}'
            try:
                post(f'/api/competitions/{competition_id}/registrations', reg_body, token)
            except RuntimeError as e:
                if 'already registered' not in str(e).lower():
                    print(f'    ⚠ Registration failed for {athlete.full_name}: {e}')
                    skipped += 1
                    continue

            # Result — skip for athletes orgeo lists as "registered but didn't run"
            # (no real start time, no finish time). The registration alone captures them.
            if athlete.status == 'dns' and athlete.start_clock_time is None:
                continue

            result_body: dict = {
                'user_id': uid,
                'class': athlete.competition_class,
                'status': athlete.status,
            }
            if athlete.time_ms is not None:
                result_body['time_total'] = athlete.time_ms

            if (
                athlete.splits
                and athlete.status == 'ok'
                and athlete.time_ms is not None
                and [s.control_point for s in athlete.splits] == cls.control_points
            ):
                result_body['splits'] = (
                    [{'control_point': 'start',  'cumulative_time': 0}]
                    + [{'control_point': s.control_point, 'cumulative_time': s.cumulative_time_ms}
                       for s in athlete.splits]
                    + [{'control_point': 'finish', 'cumulative_time': athlete.time_ms}]
                )

            if uid in results_posted:
                # Same athlete appeared in another group (open-category dupes); keep the first result.
                continue

            try:
                post(f'/api/competitions/{competition_id}/results', result_body, token)
                imported += 1
                results_posted.add(uid)
            except RuntimeError as e:
                print(f'    ⚠ Result failed for {athlete.full_name}: {e}')
                skipped += 1

    return imported, skipped


# ── Data loading ──────────────────────────────────────────────────────────────

def _safe_group_filename(group: str) -> str:
    return group.replace('/', '_').replace(' ', '_')


def load_competition(event_id: int, sub_id: int, location: str, cached: bool) -> CompetitionData:
    if cached:
        top_path = CACHE_DIR / 'top.json'
        if not top_path.exists():
            raise SystemExit(f'--cached set but {top_path} missing — run /tmp/orgeo_probe.sh first')
        top = _json.loads(top_path.read_text())
    else:
        top = fetch_top(event_id, sub_id)

    meta = parse_top_meta(top, sub_id)
    comp = CompetitionData(
        title=meta.sub_name,
        event_name=meta.event_name,
        date=meta.sub_date,
        location=location,
        sub_id=sub_id,
        event_start_date=meta.event_start_date,
        event_end_date=meta.event_end_date,
        start_time=meta.sub_start_time,
    )

    for group in meta.groups:
        if cached:
            f = CACHE_DIR / 'finish' / f'finish_{_safe_group_filename(group)}.json'
            if not f.exists():
                print(f'  (cache miss for group {group} — skipping)')
                continue
            payload = _json.loads(f.read_text())
        else:
            payload = fetch_finish(event_id, sub_id, group)
        comp.classes.append(parse_group_finish(payload))

    return comp


# ── Main ──────────────────────────────────────────────────────────────────────

def run(event_id: int, sub_id: int, cached: bool, location: str) -> None:
    print(f'Loading orgeo event={event_id} sub={sub_id} (cached={cached})')
    comp = load_competition(event_id, sub_id, location, cached)

    if not comp.classes:
        raise SystemExit('No groups parsed — abort.')

    total_athletes = sum(len(c.athletes) for c in comp.classes)
    print(f'  Event: {comp.event_name}')
    print(f'  Stage: {comp.title} ({comp.date})')
    print(f'  Groups: {len(comp.classes)}  athletes: {total_athletes}')

    print('\nLogging in...')
    token = login()

    event_name = comp.event_name or f'orgeo-{event_id}'
    ev_start = comp.event_start_date or comp.date
    ev_end   = comp.event_end_date or comp.date
    print(f'\nCreating event: {event_name}  ({ev_start} → {ev_end})')
    event_id_be = get_or_create_event(event_name, ev_start, ev_end, comp.location, token)
    print(f'  Event id={event_id_be}')

    comp_name = f'{comp.title} {comp.date}'.strip()
    print(f'\n=== Competition: {comp_name} ===')
    competition_id = get_or_create_competition(
        event_id_be, comp_name, comp.date, comp.start_time, comp.location, token,
    )
    print(f'  Competition id={competition_id}')

    for status in ('registration_open', 'registration_closed', 'in_progress', 'finished'):
        try:
            patch(f'/api/events/{event_id_be}/competitions/{competition_id}', {'status': status}, token)
        except RuntimeError as e:
            print(f'  Status {status!r} skipped: {e}')
            break

    print('  Creating distances...')
    for bucket in _group_classes_by_cps(comp.classes):
        create_distance_for_group(competition_id, bucket, token)

    print('  Importing athletes...')
    imp, skip = import_athletes(competition_id, event_id_be, comp, token)
    print(f'  → imported={imp}, skipped={skip}')

    print('\nDone.')
    print(f'  Event:        {API}/api/events/{event_id_be}')
    print(f'  Competition:  {API}/api/competitions/{competition_id}')


if __name__ == '__main__':
    args = sys.argv[1:]
    cached = '--cached' in args
    args = [a for a in args if a != '--cached']

    if len(args) < 2:
        print('Usage: poetry run python -m scripts.import_orgeo <event_id> <sub_id> [--cached]')
        sys.exit(1)

    event_id_arg = int(args[0])
    sub_id_arg = int(args[1])
    run(event_id_arg, sub_id_arg, cached=cached, location=DEFAULT_LOCATION)
