"""
Parser for Gelendjik camp results PDFs (Протокол А/В/С1/С2).

Each PDF contains pages per gender group. Layout:
  - Header area (y≈78-100): CP index labels and codes arranged horizontally
  - Athlete rows: one line per athlete with pos, name, year, bib, club, total_time, splits...
    Protocol С2 wraps name/year/club across 2-3 lines close to the data row.
  - Status "сн" (снялся) = DNS — no times follow.

Splits in the PDF are individual leg times; this parser converts them to cumulative ms.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pdfplumber


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class SplitEntry:
    control_point: str      # intermediate CP code, e.g. "32"
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
    status: str             # 'ok' | 'dns'
    competition_class: str  # e.g. "М21", "Ж16"
    splits: list[SplitEntry] = field(default_factory=list)

    @property
    def full_name(self) -> str:
        return f'{self.last_name} {self.first_name}'.strip()


@dataclass
class ClassData:
    name: str                           # derived age class, e.g. "М21"
    distance_meters: Optional[int]
    control_points: list[str] = field(default_factory=list)   # intermediate CPs only
    athletes: list[AthleteData] = field(default_factory=list)


@dataclass
class CompetitionData:
    title: str
    date: str       # ISO, e.g. "2026-03-29"
    location: str
    protocol: str   # 'А', 'В', 'С1', 'С2'
    classes: list[ClassData] = field(default_factory=list)


# ── Age-class derivation ──────────────────────────────────────────────────────

_AGE_THRESHOLDS = [65, 55, 45, 35, 21, 20, 18, 16, 14, 12, 10]


def _age_class(birth_year: int, gender_char: str, competition_year: int) -> str:
    """Derive Russian orienteering age class from birth year and gender."""
    age = competition_year - birth_year
    prefix = 'М' if gender_char == 'м' else 'Ж'
    for t in _AGE_THRESHOLDS:
        if age >= t:
            return f'{prefix}{t:02d}'
    return f'{prefix}10'


# ── Helpers ───────────────────────────────────────────────────────────────────

_TIME_RE = re.compile(r'^\d{1,2}:\d{2}:\d{2}$')
_YEAR_RE = re.compile(r'^(19[4-9]\d|20[012]\d)$')
_CP_IDX_RE = re.compile(r'^\d+\)$')
_DATE_RE = re.compile(r'(\d{2})\.(\d{2})\.(\d{4})|(\d{2})\.(\d{2})')


def _is_time(s: str) -> bool:
    return bool(_TIME_RE.match(s))


def _is_year(s: str) -> bool:
    return bool(_YEAR_RE.match(s))


def _time_to_ms(s: str) -> int:
    h, m, sec = map(int, s.split(':'))
    return (h * 3600 + m * 60 + sec) * 1000


def _extract_date_from_filename(filename: str) -> Optional[str]:
    """Extract ISO date from filename like 'Протокол А 29.03.pdf'."""
    m = re.search(r'(\d{1,2})\.(\d{2})(?:\.(\d{4}))?', filename)
    if not m:
        return None
    day, month = int(m.group(1)), int(m.group(2))
    year = int(m.group(3)) if m.group(3) else 2026
    return f'{year}-{month:02d}-{day:02d}'


def _extract_protocol_from_filename(filename: str) -> str:
    """Extract protocol letter from filename like 'Протокол А 29.03.pdf'."""
    m = re.search(r'Протокол\s+([А-ЯA-Z][12]?)', filename)
    return m.group(1) if m else ''


# ── Word-row grouping ─────────────────────────────────────────────────────────

def _group_by_y(words: list, tolerance: float = 2.0) -> list[tuple[float, list]]:
    """Group words into rows by y-coordinate within tolerance. Returns sorted list."""
    rows: dict[int, list] = {}
    for w in words:
        key = round(w['top'] / tolerance) * int(tolerance)
        rows.setdefault(key, []).append(w)
    return sorted(rows.items())


# ── CP extraction ─────────────────────────────────────────────────────────────

def _extract_cps(words: list) -> list[str]:
    """
    Extract ordered intermediate CP codes from the page header area.

    Layout: index labels (e.g. "0)", "1)") and CP names (e.g. "32.КП", "D.СТАРТ")
    appear as separate words at nearly the same x-position, ~6px apart vertically.
    We pair them by x-proximity, skip start/finish, return intermediate codes.
    """
    # Collect index words and name words separately
    idx_words = [w for w in words if _CP_IDX_RE.match(w['text'])]
    if not idx_words:
        return []

    # Build a map: index → cp_name by finding closest word below each index word
    idx_map: dict[int, str] = {}
    for iw in idx_words:
        idx = int(iw['text'].rstrip(')'))
        # Find word at same x (±5px) with slightly higher y (3-15px below)
        candidates = [
            w for w in words
            if not _CP_IDX_RE.match(w['text'])
            and abs(w['x0'] - iw['x0']) < 8
            and 2 < (w['top'] - iw['top']) < 16
        ]
        if candidates:
            name = candidates[0]['text']
            idx_map[idx] = name

    # Convert to ordered list, skipping start (idx=0) and finish (last)
    if not idx_map:
        return []

    max_idx = max(idx_map)
    cps = []
    for i in range(1, max_idx):   # skip 0=start and max=finish
        name = idx_map.get(i, '')
        if '.КП' in name:
            cps.append(name.split('.')[0])
        elif name:
            cps.append(name)
    return cps


# ── Athlete parsing ───────────────────────────────────────────────────────────

def _parse_athlete_words(
    nearby_words: list,
    anchor_y: float,
    gender_char: str,
    competition_year: int,
    cp_count: int,
) -> Optional[AthleteData]:
    """
    Parse one athlete from words collected around an anchor data row.

    Anchor row always contains: pos (x<40), [bib,] total_time, splits.
    Name, year, club may be on the anchor row or on adjacent rows (C2 format).
    """
    # Separate anchor-row words from adjacent-row words
    anchor = [w for w in nearby_words if abs(w['top'] - anchor_y) < 2]
    adjacent = [w for w in nearby_words if abs(w['top'] - anchor_y) >= 2]

    anchor_sorted = sorted(anchor, key=lambda w: w['x0'])

    # --- Times from anchor row ---
    time_words = [w for w in anchor_sorted if _is_time(w['text'])]
    if not time_words:
        return None  # no time data on this row → not an athlete row

    total_time_str = time_words[0]['text']
    # All leg times; last one is finish leg — excluded from intermediate CP splits
    all_leg_strs = [w['text'] for w in time_words[1:]]
    # Keep only intermediate-CP legs (drop the last leg = start→finish or last-CP→finish)
    split_time_strs = all_leg_strs[:-1] if cp_count > 0 and len(all_leg_strs) > cp_count else all_leg_strs
    time_x_threshold = time_words[0]['x0']

    # Detect status from anchor row (look for "сн" before time column)
    pre_time_anchor = [w for w in anchor_sorted if w['x0'] < time_x_threshold]
    has_dns = any(w['text'] == 'сн' for w in pre_time_anchor)

    # --- Position ---
    pos_words = [w for w in pre_time_anchor if w['x0'] < 40 and w['text'].isdigit()]
    if not pos_words:
        return None
    pos = int(pos_words[0]['text'])

    # --- Collect all non-time, non-pos, pre-time-column words (anchor + adjacent) ---
    info_words = sorted(
        [w for w in nearby_words
         if w['x0'] < time_x_threshold
         and not (w['x0'] < 40 and w['text'].isdigit() and abs(w['top'] - anchor_y) < 2)
         and not _is_time(w['text'])
         and w['text'] not in ('П.П', '№', 'ДЕЛЕГАЦИЯ', 'РЕЗУЛЬТАТ', 'сн')],
        key=lambda w: w['x0']
    )

    # --- Year ---
    year_words = [w for w in info_words if _is_year(w['text'])]
    birth_year = int(year_words[0]['text']) if year_words else None

    # --- Bib: integer that is NOT year, NOT pos, preferably between name and club x-range ---
    bib_words = [
        w for w in info_words
        if w['text'].isdigit() and not _is_year(w['text'])
    ]
    bib = bib_words[0]['text'] if bib_words else ''
    bib_x = bib_words[0]['x0'] if bib_words else time_x_threshold

    # --- Name and club: split by bib x-position ---
    # Exclude identified year and bib tokens; include everything else (integers may appear in club names)
    excluded_ids = {id(w) for w in year_words[:1]} | ({id(bib_words[0])} if bib_words else set())
    remaining = [w for w in info_words if id(w) not in excluded_ids]
    name_words = sorted(
        [w for w in remaining if w['x0'] < bib_x + 5],
        key=lambda w: (w['top'], w['x0'])
    )
    club_words = sorted(
        [w for w in remaining if w['x0'] > bib_x + 5],
        key=lambda w: (w['top'], w['x0'])
    )

    name_str = ' '.join(w['text'] for w in name_words).strip()
    club_str = ' '.join(w['text'] for w in club_words).strip()

    # Split name into last/first (Russian convention: "Фамилия Имя")
    name_parts = name_str.split(None, 1)
    last_name = name_parts[0] if name_parts else ''
    first_name = name_parts[1] if len(name_parts) > 1 else ''

    # --- Time and splits ---
    if has_dns or not time_words:
        status = 'dns'
        time_ms = None
        splits = []
    else:
        status = 'ok'
        time_ms = _time_to_ms(total_time_str)
        # Convert individual leg times → cumulative times
        cumulative = 0
        splits = []
        for i, t_str in enumerate(split_time_strs):
            leg_ms = _time_to_ms(t_str)
            cumulative += leg_ms
            splits.append(SplitEntry(
                control_point=str(i + 1),   # placeholder; replaced after CP list is known
                cumulative_time_ms=cumulative,
            ))

    # --- Age class ---
    comp_class = (
        _age_class(birth_year, gender_char, competition_year)
        if birth_year else (('М' if gender_char == 'м' else 'Ж') + '21')
    )

    return AthleteData(
        position=pos,
        last_name=last_name,
        first_name=first_name,
        club=club_str,
        bib_number=bib,
        birth_year=birth_year,
        time_ms=time_ms,
        status=status,
        competition_class=comp_class,
        splits=splits,
    )


def _assign_cp_codes(athlete: AthleteData, cp_list: list[str]) -> None:
    """Replace placeholder CP codes with actual CP codes from the course."""
    for i, split in enumerate(athlete.splits):
        if i < len(cp_list):
            split.control_point = cp_list[i]


# ── Page parser ───────────────────────────────────────────────────────────────

def _parse_page(page, competition_year: int, fallback_cps: Optional[list[str]] = None, fallback_gender: str = 'м') -> tuple[str, list[str], list[AthleteData]]:
    """
    Parse one PDF page.

    Returns:
        gender_char: 'м' or 'ж'
        cp_list: ordered intermediate CP codes
        athletes: parsed athletes on this page
    """
    words = page.extract_words(x_tolerance=3, y_tolerance=3)
    sorted_rows = _group_by_y(words, tolerance=2.0)

    # --- Detect gender from group header (fall back to previous page's gender on overflow pages) ---
    # The header row looks like "Геленджик 2026 - С1 31 марта м. 1 - 100"
    # We check for "ж." or "м." as standalone word tokens (not substrings) to avoid
    # false matches with "марта" on the same line.
    gender_char = None
    for _, row_words in sorted_rows:
        tokens = {w['text'].lower() for w in row_words}
        if 'ж.' in tokens:
            gender_char = 'ж'
            break
        if 'м.' in tokens:
            gender_char = 'м'
            break
    if gender_char is None:
        gender_char = fallback_gender

    # --- Extract CPs (use fallback if this is a continuation page without a CP header) ---
    cp_list = _extract_cps(words) or (fallback_cps or [])

    # --- Find athlete anchor rows ---
    # Anchor row: leftmost word at x<40 is a small integer AND row has time tokens
    anchor_rows: list[float] = []
    for y_key, row_words in sorted_rows:
        left_words = [w for w in row_words if w['x0'] < 40]
        if not left_words:
            continue
        left = min(left_words, key=lambda w: w['x0'])
        if not left['text'].isdigit():
            continue
        if any(_is_time(w['text']) for w in row_words):
            anchor_rows.append(left['top'])

    # Also find DNS-only rows (pos + name/bib + "сн", no time)
    # These are rows with a left integer, "сн", but no time token
    dns_rows: list[float] = []
    for y_key, row_words in sorted_rows:
        left_words = [w for w in row_words if w['x0'] < 40]
        if not left_words:
            continue
        left = min(left_words, key=lambda w: w['x0'])
        if not left['text'].isdigit():
            continue
        texts = [w['text'] for w in row_words]
        if 'сн' in texts and not any(_is_time(t) for t in texts):
            dns_rows.append(left['top'])

    # --- Parse athletes ---
    all_y = [w['top'] for w in words]
    min_y = min(all_y) if all_y else 0
    max_y = max(all_y) if all_y else 0
    Y_WINDOW = 10.0  # px around anchor row to collect wrapping words

    athletes: list[AthleteData] = []

    for anchor_y in anchor_rows:
        nearby = [
            w for w in words
            if abs(w['top'] - anchor_y) <= Y_WINDOW
        ]
        athlete = _parse_athlete_words(nearby, anchor_y, gender_char, competition_year, len(cp_list))
        if athlete:
            _assign_cp_codes(athlete, cp_list)
            athletes.append(athlete)

    # Parse DNS athletes
    for anchor_y in dns_rows:
        nearby = [
            w for w in words
            if abs(w['top'] - anchor_y) <= Y_WINDOW
        ]
        anchor = [w for w in nearby if abs(w['top'] - anchor_y) < 2]
        anchor_sorted = sorted(anchor, key=lambda w: w['x0'])

        pos_words = [w for w in anchor_sorted if w['x0'] < 40 and w['text'].isdigit()]
        if not pos_words:
            continue
        pos = int(pos_words[0]['text'])

        # Collect info words (no time column threshold known, use page width)
        info_words = sorted(
            [w for w in nearby
             if not (w['x0'] < 40 and w['text'].isdigit() and abs(w['top'] - anchor_y) < 2)
             and w['text'] not in ('П.П', '№', 'ДЕЛЕГАЦИЯ', 'РЕЗУЛЬТАТ', 'сн')],
            key=lambda w: w['x0']
        )

        year_words = [w for w in info_words if _is_year(w['text'])]
        birth_year = int(year_words[0]['text']) if year_words else None

        bib_words = [w for w in info_words if w['text'].isdigit() and not _is_year(w['text'])]
        bib = bib_words[0]['text'] if bib_words else ''
        bib_x = bib_words[0]['x0'] if bib_words else 1000

        name_words_list = sorted(
            [w for w in info_words if not w['text'].isdigit() and w['x0'] < bib_x + 5],
            key=lambda w: (w['top'], w['x0'])
        )
        club_words_list = sorted(
            [w for w in info_words if not w['text'].isdigit() and w['x0'] > bib_x + 5],
            key=lambda w: (w['top'], w['x0'])
        )

        name_str = ' '.join(w['text'] for w in name_words_list).strip()
        club_str = ' '.join(w['text'] for w in club_words_list).strip()
        name_parts = name_str.split(None, 1)
        last_name = name_parts[0] if name_parts else ''
        first_name = name_parts[1] if len(name_parts) > 1 else ''

        comp_class = (
            _age_class(birth_year, gender_char, competition_year)
            if birth_year else (('М' if gender_char == 'м' else 'Ж') + '21')
        )

        athletes.append(AthleteData(
            position=pos,
            last_name=last_name,
            first_name=first_name,
            club=club_str,
            bib_number=bib,
            birth_year=birth_year,
            time_ms=None,
            status='dns',
            competition_class=comp_class,
            splits=[],
        ))

    athletes.sort(key=lambda a: a.position or 9999)
    return gender_char, cp_list, athletes


# ── Public API ────────────────────────────────────────────────────────────────

def parse_protocol_pdf(path: 'str | Path', competition_year: int = 2026) -> CompetitionData:
    """
    Parse a Gelendjik results PDF (Протокол А/В/С1/С2).

    Returns a CompetitionData with one ClassData per age class found.
    All CP codes are taken from the first page (same course for all genders).
    """
    path = Path(path)
    filename = path.name

    date = _extract_date_from_filename(filename) or ''
    protocol = _extract_protocol_from_filename(filename)

    # Title from filename, e.g. "Геленджик 2026 - А 29 марта"
    date_part = re.search(r'\d{2}\.\d{2}', filename)
    date_label = date_part.group(0) if date_part else ''
    title = f'Геленджик {competition_year} - {protocol} {date_label}'

    comp = CompetitionData(title=title, date=date, location='Геленджик', protocol=protocol)

    shared_cps: list[str] = []
    last_gender = 'м'

    # group athletes by age class → one ClassData per class
    class_map: dict[str, ClassData] = {}

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            gender_char, cp_list, athletes = _parse_page(
                page, competition_year,
                fallback_cps=shared_cps or None,
                fallback_gender=last_gender,
            )
            if cp_list:
                shared_cps = cp_list
            last_gender = gender_char

            for athlete in athletes:
                cls_name = athlete.competition_class
                if cls_name not in class_map:
                    class_map[cls_name] = ClassData(
                        name=cls_name,
                        distance_meters=None,
                        control_points=shared_cps,
                    )
                class_map[cls_name].athletes.append(athlete)

    # Assign shared CPs to all classes (in case first page had none)
    for cls in class_map.values():
        if not cls.control_points:
            cls.control_points = shared_cps

    comp.classes = list(class_map.values())
    return comp
