"""
Parser for orgeo.ru live result JSON (SPA at https://orgeo.ru/live/#/{event}/{sub}).

The live page calls two endpoints (discovered from inline JS in /live/):

  GET https://orgeo.ru/online/top/?id={event_id}&s={sub_id}&api=json
      → event metadata: subs (stages), dists (group filter chips), etc.

  GET https://orgeo.ru/online/finish/{event_id}?s={sub_id}&d={group}&dist_names=[]&api=json
      → array `finish` of athlete rows for the given group.

Each athlete row carries:
  name      "Фамилия Имя"
  team      club / region string
  year      birth year (string)
  number    bib (string)
  start     start time HH:MM:SS (clock)
  finish    elapsed time HH:MM:SS
  otm       status code: '0'=ok, '1'=DSQ, '7'=DNF, '8'=DNS
  otm_name  human label ('', 'не старт', 'непр.отмет.', ...)
  place     1-based finishing place (int)
  spl       splits string of alternating leg_time|cp_code pairs,
            last pair has cp_code='FIN'.
            e.g. '00:02:16|77|00:01:14|74|...|00:00:16|FIN|'
"""
import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Optional


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class SplitEntry:
    control_point: str       # CP code, e.g. "77"
    cumulative_time_ms: int


@dataclass
class AthleteData:
    position: Optional[int]
    last_name: str
    first_name: str
    club: str
    bib_number: str
    birth_year: Optional[int]
    time_ms: Optional[int]
    status: str                                  # 'ok' | 'dnf' | 'dns' | 'dsq'
    competition_class: str                       # group name, e.g. 'Ж-12'
    start_clock_time: Optional[str] = None       # 'HH:MM:SS' from orgeo, in event timezone
    splits: list[SplitEntry] = field(default_factory=list)

    @property
    def full_name(self) -> str:
        return f'{self.last_name} {self.first_name}'.strip()


@dataclass
class ClassData:
    name: str                                       # group name (== orgeo `dist`)
    distance_meters: Optional[int]
    control_points: list[str] = field(default_factory=list)
    athletes: list[AthleteData] = field(default_factory=list)


@dataclass
class CompetitionData:
    title: str                                      # sub stage name, e.g. 'Кросс – классика'
    event_name: str                                 # parent event name
    date: str                                       # ISO date 'YYYY-MM-DD' for this stage
    location: str
    sub_id: int
    event_start_date: str = ''                      # earliest stage date in the parent event
    event_end_date: str = ''                        # latest stage date in the parent event
    start_time: str = '11:00:00'                    # HH:MM:SS — start of this stage
    classes: list[ClassData] = field(default_factory=list)


# ── Helpers ───────────────────────────────────────────────────────────────────

_OTM_TO_STATUS = {
    '0': 'ok',
    '1': 'dsq',
    '7': 'dnf',
    '8': 'dns',
}

# Fallback mapping by Russian label when otm code is missing/unknown
_OTM_NAME_TO_STATUS = {
    'не старт':    'dns',
    'непр.отмет.': 'dsq',
    'дсв':         'dsq',
    'снят':        'dnf',
}


def _time_to_ms(s: str) -> Optional[int]:
    """Parse HH:MM:SS → milliseconds. Returns None if format mismatches."""
    if not s:
        return None
    m = re.match(r'^(\d{1,2}):(\d{2}):(\d{2})$', s.strip())
    if not m:
        return None
    h, mi, sec = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return (h * 3600 + mi * 60 + sec) * 1000


def _split_name(full: str) -> tuple[str, str]:
    """orgeo convention is 'Фамилия Имя'."""
    parts = (full or '').strip().split(None, 1)
    last = parts[0] if parts else ''
    first = parts[1] if len(parts) > 1 else ''
    return last, first


def _parse_spl(spl: str) -> list[tuple[str, int]]:
    """
    Split the 'spl' string into [(cp_code, leg_ms), ...].
    Last entry has cp_code='FIN' — kept by the caller.
    """
    if not spl:
        return []
    tokens = [t for t in spl.split('|') if t != '']
    out: list[tuple[str, int]] = []
    for i in range(0, len(tokens) - 1, 2):
        leg_str = tokens[i]
        cp_code = tokens[i + 1]
        leg_ms = _time_to_ms(leg_str)
        if leg_ms is None:
            continue
        out.append((cp_code, leg_ms))
    return out


def _decode_status(otm: Optional[str], otm_name: Optional[str], has_finish_time: bool) -> str:
    if otm in _OTM_TO_STATUS:
        return _OTM_TO_STATUS[otm]
    if otm_name:
        key = otm_name.strip().lower()
        if key in _OTM_NAME_TO_STATUS:
            return _OTM_NAME_TO_STATUS[key]
    return 'ok' if has_finish_time else 'dns'


# ── Athlete row ───────────────────────────────────────────────────────────────

def _parse_athlete_row(row: dict, group_name: str) -> Optional[AthleteData]:
    name = (row.get('name') or '').strip()
    if not name:
        return None

    last_name, first_name = _split_name(name)
    bib = (row.get('number') or '').strip()
    club = (row.get('team') or '').strip()

    year_str = (row.get('year') or '').strip()
    birth_year = int(year_str) if year_str.isdigit() else None

    finish_ms = _time_to_ms(row.get('finish') or '')

    status = _decode_status(
        otm=str(row.get('otm')) if row.get('otm') is not None else None,
        otm_name=row.get('otm_name'),
        has_finish_time=finish_ms is not None,
    )

    # Splits: leg pairs → cumulative
    splits: list[SplitEntry] = []
    if status == 'ok' and finish_ms is not None:
        cumulative = 0
        for cp_code, leg_ms in _parse_spl(row.get('spl') or ''):
            cumulative += leg_ms
            if cp_code == 'FIN':
                continue  # finish synthesised by caller
            splits.append(SplitEntry(control_point=cp_code, cumulative_time_ms=cumulative))

    place = row.get('place')
    position = int(place) if isinstance(place, int) or (isinstance(place, str) and place.isdigit()) else None

    start_str = (row.get('start') or '').strip()
    if re.match(r'^\d{1,2}:\d{2}:\d{2}$', start_str) and start_str != '00:00:00':
        start_clock = start_str
    else:
        start_clock = None  # orgeo uses 00:00:00 as a "didn't actually run" placeholder

    return AthleteData(
        position=position,
        last_name=last_name,
        first_name=first_name,
        club=club,
        bib_number=bib,
        birth_year=birth_year,
        time_ms=finish_ms if status == 'ok' else None,
        status=status,
        competition_class=group_name,
        start_clock_time=start_clock,
        splits=splits,
    )


def _reference_cps(athletes: list[AthleteData]) -> list[str]:
    """
    Most common CP sequence across finishers — used as the canonical course
    for the group. Athletes whose own splits don't match this stay finishless
    in the import step.
    """
    from collections import Counter
    seqs = [tuple(s.control_point for s in a.splits) for a in athletes if a.status == 'ok' and a.splits]
    if not seqs:
        return []
    most_common, _ = Counter(seqs).most_common(1)[0]
    return list(most_common)


# ── Public API ────────────────────────────────────────────────────────────────

def parse_group_finish(finish_payload: dict) -> ClassData:
    """
    Build a ClassData for a single group from one /online/finish/... response.
    """
    group_name = finish_payload.get('dist') or ''
    raw_athletes = finish_payload.get('finish') or []

    athletes: list[AthleteData] = []
    for row in raw_athletes:
        a = _parse_athlete_row(row, group_name)
        if a is not None:
            athletes.append(a)

    return ClassData(
        name=group_name,
        distance_meters=None,
        control_points=_reference_cps(athletes),
        athletes=athletes,
    )


@dataclass
class TopMeta:
    event_name: str
    sub_name: str
    sub_date: str             # ISO date for the requested stage
    sub_start_time: str       # HH:MM:SS for the requested stage
    event_start_date: str     # earliest sub date across the whole event
    event_end_date: str       # latest sub date across the whole event
    groups: list[str]


def parse_top_meta(top_payload: dict, sub_id: int) -> TopMeta:
    """
    Pull metadata from /online/top/...

    `top.subs` has one entry per stage; we pick the requested sub for stage info
    and derive event_start_date/event_end_date from min/max of all subs.
    """
    subs = top_payload.get('subs') or []
    sub = next((s for s in subs if str(s.get('sub_id')) == str(sub_id)), None)
    if sub is None and subs:
        sub = subs[0]

    def _split_dt(dt: str) -> tuple[str, str]:
        if not dt:
            return '', ''
        parts = dt.split(' ', 1)
        return parts[0], (parts[1] if len(parts) > 1 else '')

    sub_date, sub_time = _split_dt((sub.get('datetime') if sub else '') or '')
    all_dates = [_split_dt(s.get('datetime') or '')[0] for s in subs]
    all_dates = [d for d in all_dates if d]
    event_start = min(all_dates) if all_dates else sub_date
    event_end = max(all_dates) if all_dates else sub_date

    return TopMeta(
        event_name=(sub.get('event_name') if sub else '') or '',
        sub_name=(sub.get('name') if sub else '') or '',
        sub_date=sub_date,
        sub_start_time=sub_time or '11:00:00',
        event_start_date=event_start,
        event_end_date=event_end,
        groups=list(top_payload.get('dists') or []),
    )


# ── Fetchers ──────────────────────────────────────────────────────────────────

_UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36'
_BASE = 'https://orgeo.ru'


def _http_get_json(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': _UA,
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Referer': f'{_BASE}/live/',
            'X-Requested-With': 'XMLHttpRequest',
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def fetch_top(event_id: int, sub_id: int) -> dict:
    qs = urllib.parse.urlencode({'id': event_id, 's': sub_id, 'api': 'json', '_': 0})
    return _http_get_json(f'{_BASE}/online/top/?{qs}')


def fetch_finish(event_id: int, sub_id: int, group: str) -> dict:
    qs = urllib.parse.urlencode({
        's': sub_id,
        'd': group,
        'dist_names': '[]',
        'api': 'json',
        '_': 0,
    })
    return _http_get_json(f'{_BASE}/online/finish/{event_id}?{qs}')


def fetch_competition(event_id: int, sub_id: int, location: str = '') -> CompetitionData:
    """
    Full pipeline: hit /online/top/ + /online/finish/ for every group and
    return a ready-to-import CompetitionData.
    """
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
        payload = fetch_finish(event_id, sub_id, group)
        comp.classes.append(parse_group_finish(payload))
    return comp
