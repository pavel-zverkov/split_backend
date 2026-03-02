#!/usr/bin/env bash
set -euo pipefail

BASE_URL="http://localhost:8000/api"

# ─── helpers ───────────────────────────────────────────────────────────────────

log()  { printf '\n\033[1;34m>>> %s\033[0m\n' "$*"; }
ok()   { printf '  \033[0;32m✓ %s\033[0m\n' "$*"; }
fail() { printf '  \033[0;31m✗ %s\033[0m\n' "$*"; exit 1; }

# POST helper — returns full response body
post() {
  local url="$1" token="$2" body="$3"
  curl -sf -X POST "$url" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $token" \
    -d "$body"
}

# PATCH helper
patch() {
  local url="$1" token="$2" body="$3"
  curl -sf -X PATCH "$url" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $token" \
    -d "$body"
}

# POST without auth
post_noauth() {
  local url="$1" body="$2"
  curl -sf -X POST "$url" \
    -H "Content-Type: application/json" \
    -d "$body"
}

# GET helper
get() {
  local url="$1" token="${2:-}"
  if [ -n "$token" ]; then
    curl -sf "$url" -H "Authorization: Bearer $token"
  else
    curl -sf "$url"
  fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# 1. REGISTER USERS
# ═══════════════════════════════════════════════════════════════════════════════
log "Registering users"

register_user() {
  local username="$1" password="$2" first_name="$3" last_name="${4:-}"
  local body resp
  if [ -n "$last_name" ]; then
    body=$(printf '{"username":"%s","password":"%s","first_name":"%s","last_name":"%s"}' \
      "$username" "$password" "$first_name" "$last_name")
  else
    body=$(printf '{"username":"%s","password":"%s","first_name":"%s"}' \
      "$username" "$password" "$first_name")
  fi
  # Try register first, fall back to login if user exists
  resp=$(curl -s -X POST "$BASE_URL/auth/register" \
    -H "Content-Type: application/json" -d "$body")
  if echo "$resp" | jq -e '.access_token' > /dev/null 2>&1; then
    echo "$resp"
    return
  fi
  # User exists — login
  local login_body
  login_body=$(printf '{"login":"%s","password":"%s"}' "$username" "$password")
  curl -sf -X POST "$BASE_URL/auth/login" \
    -H "Content-Type: application/json" -d "$login_body"
}

RESP=$(register_user organizer1 organizer1 Alexei Petrov)
TOKEN_ORG1=$(echo "$RESP" | jq -r '.access_token')
ID_ORG1=$(echo "$RESP" | jq -r '.user.id')
ok "organizer1 (id=$ID_ORG1)"

RESP=$(register_user organizer2 organizer2 Maria Ivanova)
TOKEN_ORG2=$(echo "$RESP" | jq -r '.access_token')
ID_ORG2=$(echo "$RESP" | jq -r '.user.id')
ok "organizer2 (id=$ID_ORG2)"

RESP=$(register_user secretary1 secretary1 Dmitri Sidorov)
TOKEN_SEC=$(echo "$RESP" | jq -r '.access_token')
ID_SEC=$(echo "$RESP" | jq -r '.user.id')
ok "secretary1 (id=$ID_SEC)"

RESP=$(register_user judge1 judge1judge1 Elena Kuznetsova)
TOKEN_JUDGE=$(echo "$RESP" | jq -r '.access_token')
ID_JUDGE=$(echo "$RESP" | jq -r '.user.id')
ok "judge1 (id=$ID_JUDGE)"

RESP=$(register_user athlete1 athlete1a Ivan Volkov)
TOKEN_ATH1=$(echo "$RESP" | jq -r '.access_token')
ID_ATH1=$(echo "$RESP" | jq -r '.user.id')
ok "athlete1 (id=$ID_ATH1)"

RESP=$(register_user athlete2 athlete2a Olga Sokolova)
TOKEN_ATH2=$(echo "$RESP" | jq -r '.access_token')
ID_ATH2=$(echo "$RESP" | jq -r '.user.id')
ok "athlete2 (id=$ID_ATH2)"

RESP=$(register_user athlete3 athlete3a Petr Morozov)
TOKEN_ATH3=$(echo "$RESP" | jq -r '.access_token')
ID_ATH3=$(echo "$RESP" | jq -r '.user.id')
ok "athlete3 (id=$ID_ATH3)"

RESP=$(register_user athlete4 athlete4a Anna Lebedeva)
TOKEN_ATH4=$(echo "$RESP" | jq -r '.access_token')
ID_ATH4=$(echo "$RESP" | jq -r '.user.id')
ok "athlete4 (id=$ID_ATH4)"

RESP=$(register_user athlete5 athlete5a Sergei Novikov)
TOKEN_ATH5=$(echo "$RESP" | jq -r '.access_token')
ID_ATH5=$(echo "$RESP" | jq -r '.user.id')
ok "athlete5 (id=$ID_ATH5)"

RESP=$(register_user volunteer1 volunteer1 Nina Fedorova)
TOKEN_VOL=$(echo "$RESP" | jq -r '.access_token')
ID_VOL=$(echo "$RESP" | jq -r '.user.id')
ok "volunteer1 (id=$ID_VOL)"

# ═══════════════════════════════════════════════════════════════════════════════
# 2. CREATE EVENTS (all as draft initially)
# ═══════════════════════════════════════════════════════════════════════════════
log "Creating events (all as draft)"

create_event() {
  local token="$1" body="$2"
  post "$BASE_URL/events" "$token" "$body"
}

# Event 1: Orient Sprint Cup — single, orient, target: draft
E1=$(create_event "$TOKEN_ORG1" '{
  "name": "Orient Sprint Cup",
  "description": "Sprint orienteering competition in city park",
  "start_date": "2026-04-01",
  "end_date": "2026-04-01",
  "location": "Moscow, Sokolniki Park",
  "sport_kind": "orient",
  "event_format": "single",
  "privacy": "public",
  "status": "draft",
  "competition": {"start_format": "separated_start"}
}')
E1_ID=$(echo "$E1" | jq -r '.id')
E1_COMP_ID=$(echo "$E1" | jq -r '.competition_brief.id')
ok "Event 1: Orient Sprint Cup (id=$E1_ID, comp=$E1_COMP_ID)"

# Event 2: City Run 5K — single, run, target: planned
E2=$(create_event "$TOKEN_ORG1" '{
  "name": "City Run 5K",
  "description": "5 kilometer city run for all ages",
  "start_date": "2026-03-15",
  "end_date": "2026-03-15",
  "location": "Saint Petersburg, Palace Square",
  "sport_kind": "run",
  "event_format": "single",
  "privacy": "public",
  "status": "draft",
  "competition": {"start_format": "mass_start"}
}')
E2_ID=$(echo "$E2" | jq -r '.id')
E2_COMP_ID=$(echo "$E2" | jq -r '.competition_brief.id')
ok "Event 2: City Run 5K (id=$E2_ID, comp=$E2_COMP_ID)"

# Event 3: Bike Challenge — single, bike, target: in_progress (today)
E3=$(create_event "$TOKEN_ORG1" '{
  "name": "Bike Challenge",
  "description": "Mountain bike challenge through forest trails",
  "start_date": "2026-02-25",
  "end_date": "2026-02-25",
  "location": "Kazan, Forest Park",
  "sport_kind": "bike",
  "event_format": "single",
  "privacy": "public",
  "status": "draft",
  "competition": {"start_format": "mass_start"}
}')
E3_ID=$(echo "$E3" | jq -r '.id')
E3_COMP_ID=$(echo "$E3" | jq -r '.competition_brief.id')
ok "Event 3: Bike Challenge (id=$E3_ID, comp=$E3_COMP_ID)"

# Event 4: Ski Sprint Final — single, cx_ski, target: finished
E4=$(create_event "$TOKEN_ORG1" '{
  "name": "Ski Sprint Final",
  "description": "Cross-country ski sprint finals",
  "start_date": "2026-02-10",
  "end_date": "2026-02-10",
  "location": "Novosibirsk, Ski Stadium",
  "sport_kind": "cx_ski",
  "event_format": "single",
  "privacy": "public",
  "status": "draft",
  "competition": {"start_format": "separated_start"}
}')
E4_ID=$(echo "$E4" | jq -r '.id')
E4_COMP_ID=$(echo "$E4" | jq -r '.competition_brief.id')
ok "Event 4: Ski Sprint Final (id=$E4_ID, comp=$E4_COMP_ID)"

# Event 5: Tourism Race — single, sport_tourism, target: cancelled
E5=$(create_event "$TOKEN_ORG2" '{
  "name": "Tourism Race",
  "description": "Sport tourism race with orienteering elements",
  "start_date": "2026-05-01",
  "end_date": "2026-05-01",
  "location": "Sochi, Mountain Resort",
  "sport_kind": "sport_tourism",
  "event_format": "single",
  "privacy": "public",
  "status": "draft",
  "competition": {"start_format": "free"}
}')
E5_ID=$(echo "$E5" | jq -r '.id')
E5_COMP_ID=$(echo "$E5" | jq -r '.competition_brief.id')
ok "Event 5: Tourism Race (id=$E5_ID, comp=$E5_COMP_ID)"

# Event 6: Autumn Orient Cup — multi_stage, orient, target: planned
E6=$(create_event "$TOKEN_ORG1" '{
  "name": "Autumn Orient Cup",
  "description": "Three-day orienteering cup with sprint, middle and long distances",
  "start_date": "2026-09-20",
  "end_date": "2026-09-22",
  "location": "Ekaterinburg, Ural Forest",
  "sport_kind": "orient",
  "event_format": "multi_stage",
  "privacy": "public",
  "status": "draft"
}')
E6_ID=$(echo "$E6" | jq -r '.id')
ok "Event 6: Autumn Orient Cup (id=$E6_ID)"

# Event 7: Spring Run Series — multi_stage, run, target: in_progress
E7=$(create_event "$TOKEN_ORG1" '{
  "name": "Spring Run Series",
  "description": "Series of running competitions over a week",
  "start_date": "2026-02-20",
  "end_date": "2026-02-28",
  "location": "Moscow, Luzhniki",
  "sport_kind": "run",
  "event_format": "multi_stage",
  "privacy": "public",
  "status": "draft"
}')
E7_ID=$(echo "$E7" | jq -r '.id')
ok "Event 7: Spring Run Series (id=$E7_ID)"

# Event 8: Mountain Bike Tour — multi_stage, bike, target: finished
E8=$(create_event "$TOKEN_ORG2" '{
  "name": "Mountain Bike Tour",
  "description": "Three-day mountain bike tour",
  "start_date": "2026-01-10",
  "end_date": "2026-01-12",
  "location": "Krasnoyarsk, Stolby Reserve",
  "sport_kind": "bike",
  "event_format": "multi_stage",
  "privacy": "public",
  "status": "draft"
}')
E8_ID=$(echo "$E8" | jq -r '.id')
ok "Event 8: Mountain Bike Tour (id=$E8_ID)"

# Event 9: Ski Marathon Week — multi_stage, cx_ski, target: draft
E9=$(create_event "$TOKEN_ORG2" '{
  "name": "Ski Marathon Week",
  "description": "Multi-day cross-country ski marathon",
  "start_date": "2026-12-01",
  "end_date": "2026-12-05",
  "location": "Murmansk, Arctic Stadium",
  "sport_kind": "cx_ski",
  "event_format": "multi_stage",
  "privacy": "public",
  "status": "draft"
}')
E9_ID=$(echo "$E9" | jq -r '.id')
ok "Event 9: Ski Marathon Week (id=$E9_ID)"

# Event 10: Sport Tourism Fest — multi_stage, sport_tourism, target: cancelled
E10=$(create_event "$TOKEN_ORG2" '{
  "name": "Sport Tourism Fest",
  "description": "Multi-day sport tourism festival with various disciplines",
  "start_date": "2026-06-01",
  "end_date": "2026-06-03",
  "location": "Altai, Mountain Camp",
  "sport_kind": "sport_tourism",
  "event_format": "multi_stage",
  "privacy": "public",
  "status": "draft"
}')
E10_ID=$(echo "$E10" | jq -r '.id')
ok "Event 10: Sport Tourism Fest (id=$E10_ID)"

# ═══════════════════════════════════════════════════════════════════════════════
# 3. CREATE COMPETITIONS for multi-stage events
# ═══════════════════════════════════════════════════════════════════════════════
log "Creating competitions for multi-stage events"

create_comp() {
  local event_id="$1" token="$2" body="$3"
  post "$BASE_URL/events/$event_id/competitions" "$token" "$body"
}

# Event 6 — Autumn Orient Cup: 3 competitions
E6_C1=$(create_comp "$E6_ID" "$TOKEN_ORG1" '{
  "name": "Sprint", "date": "2026-09-20", "start_format": "separated_start", "location": "Ekaterinburg City Center"
}')
E6_C1_ID=$(echo "$E6_C1" | jq -r '.id')

E6_C2=$(create_comp "$E6_ID" "$TOKEN_ORG1" '{
  "name": "Middle Distance", "date": "2026-09-21", "start_format": "separated_start", "location": "Ural Forest North"
}')
E6_C2_ID=$(echo "$E6_C2" | jq -r '.id')

E6_C3=$(create_comp "$E6_ID" "$TOKEN_ORG1" '{
  "name": "Long Distance", "date": "2026-09-22", "start_format": "mass_start", "location": "Ural Forest South"
}')
E6_C3_ID=$(echo "$E6_C3" | jq -r '.id')
ok "Event 6: 3 competitions ($E6_C1_ID, $E6_C2_ID, $E6_C3_ID)"

# Event 7 — Spring Run Series: 3 competitions
E7_C1=$(create_comp "$E7_ID" "$TOKEN_ORG1" '{
  "name": "5K Warm-up", "date": "2026-02-20", "start_format": "mass_start", "location": "Luzhniki Stadium"
}')
E7_C1_ID=$(echo "$E7_C1" | jq -r '.id')

E7_C2=$(create_comp "$E7_ID" "$TOKEN_ORG1" '{
  "name": "10K Main Race", "date": "2026-02-24", "start_format": "mass_start", "location": "Luzhniki Embankment"
}')
E7_C2_ID=$(echo "$E7_C2" | jq -r '.id')

E7_C3=$(create_comp "$E7_ID" "$TOKEN_ORG1" '{
  "name": "Half Marathon", "date": "2026-02-28", "start_format": "separated_start", "location": "Moscow River Route"
}')
E7_C3_ID=$(echo "$E7_C3" | jq -r '.id')
ok "Event 7: 3 competitions ($E7_C1_ID, $E7_C2_ID, $E7_C3_ID)"

# Event 8 — Mountain Bike Tour: 3 competitions
E8_C1=$(create_comp "$E8_ID" "$TOKEN_ORG2" '{
  "name": "Time Trial", "date": "2026-01-10", "start_format": "separated_start", "location": "Stolby Base"
}')
E8_C1_ID=$(echo "$E8_C1" | jq -r '.id')

E8_C2=$(create_comp "$E8_ID" "$TOKEN_ORG2" '{
  "name": "Cross-Country", "date": "2026-01-11", "start_format": "mass_start", "location": "Stolby Trails"
}')
E8_C2_ID=$(echo "$E8_C2" | jq -r '.id')

E8_C3=$(create_comp "$E8_ID" "$TOKEN_ORG2" '{
  "name": "Downhill", "date": "2026-01-12", "start_format": "mass_start", "location": "Stolby Summit"
}')
E8_C3_ID=$(echo "$E8_C3" | jq -r '.id')
ok "Event 8: 3 competitions ($E8_C1_ID, $E8_C2_ID, $E8_C3_ID)"

# Event 9 — Ski Marathon Week: 2 competitions (stays draft)
E9_C1=$(create_comp "$E9_ID" "$TOKEN_ORG2" '{
  "name": "Classic 30K", "date": "2026-12-01", "start_format": "mass_start", "location": "Arctic Stadium"
}')
E9_C1_ID=$(echo "$E9_C1" | jq -r '.id')

E9_C2=$(create_comp "$E9_ID" "$TOKEN_ORG2" '{
  "name": "Freestyle 50K", "date": "2026-12-05", "start_format": "separated_start", "location": "Arctic Trail"
}')
E9_C2_ID=$(echo "$E9_C2" | jq -r '.id')
ok "Event 9: 2 competitions ($E9_C1_ID, $E9_C2_ID)"

# Event 10 — Sport Tourism Fest: 2 competitions
E10_C1=$(create_comp "$E10_ID" "$TOKEN_ORG2" '{
  "name": "Navigation Challenge", "date": "2026-06-01", "start_format": "mass_start", "location": "Altai Valley"
}')
E10_C1_ID=$(echo "$E10_C1" | jq -r '.id')

E10_C2=$(create_comp "$E10_ID" "$TOKEN_ORG2" '{
  "name": "Survival Race", "date": "2026-06-03", "start_format": "free", "location": "Altai Summit"
}')
E10_C2_ID=$(echo "$E10_C2" | jq -r '.id')
ok "Event 10: 2 competitions ($E10_C1_ID, $E10_C2_ID)"

# ═══════════════════════════════════════════════════════════════════════════════
# 4. CREATE DISTANCES with classes and control points
# ═══════════════════════════════════════════════════════════════════════════════
log "Creating distances"

create_distance() {
  local comp_id="$1" token="$2" body="$3"
  post "$BASE_URL/competitions/$comp_id/distances" "$token" "$body"
}

# Single events — one distance each

# Event 1 comp (orient sprint)
E1_D1=$(create_distance "$E1_COMP_ID" "$TOKEN_ORG1" '{
  "name": "Sprint Course",
  "distance_meters": 3500,
  "climb_meters": 50,
  "classes": ["M21", "W21", "M35"],
  "control_points": [
    {"code": "S1", "type": "start"},
    {"code": "31", "type": "control"},
    {"code": "32", "type": "control"},
    {"code": "33", "type": "control"},
    {"code": "34", "type": "control"},
    {"code": "35", "type": "control"},
    {"code": "F1", "type": "finish"}
  ]
}')
E1_D1_ID=$(echo "$E1_D1" | jq -r '.id')
ok "E1 distance: Sprint Course ($E1_D1_ID)"

# Event 2 comp (run 5K)
E2_D1=$(create_distance "$E2_COMP_ID" "$TOKEN_ORG1" '{
  "name": "5K Route",
  "distance_meters": 5000,
  "climb_meters": 20,
  "classes": ["Open", "Senior"],
  "control_points": [
    {"code": "S", "type": "start"},
    {"code": "1K", "type": "control"},
    {"code": "2K", "type": "control"},
    {"code": "3K", "type": "control"},
    {"code": "4K", "type": "control"},
    {"code": "F", "type": "finish"}
  ]
}')
E2_D1_ID=$(echo "$E2_D1" | jq -r '.id')
ok "E2 distance: 5K Route ($E2_D1_ID)"

# Event 3 comp (bike)
E3_D1=$(create_distance "$E3_COMP_ID" "$TOKEN_ORG1" '{
  "name": "Forest Loop",
  "distance_meters": 25000,
  "climb_meters": 400,
  "classes": ["Elite", "Amateur"],
  "control_points": [
    {"code": "S", "type": "start"},
    {"code": "CP1", "type": "control"},
    {"code": "CP2", "type": "control"},
    {"code": "CP3", "type": "control"},
    {"code": "F", "type": "finish"}
  ]
}')
E3_D1_ID=$(echo "$E3_D1" | jq -r '.id')
ok "E3 distance: Forest Loop ($E3_D1_ID)"

# Event 4 comp (ski sprint)
E4_D1=$(create_distance "$E4_COMP_ID" "$TOKEN_ORG1" '{
  "name": "Sprint Track",
  "distance_meters": 1500,
  "climb_meters": 30,
  "classes": ["M21", "W21"],
  "control_points": [
    {"code": "S", "type": "start"},
    {"code": "500m", "type": "control"},
    {"code": "1000m", "type": "control"},
    {"code": "F", "type": "finish"}
  ]
}')
E4_D1_ID=$(echo "$E4_D1" | jq -r '.id')
ok "E4 distance: Sprint Track ($E4_D1_ID)"

# Event 5 comp (tourism)
E5_D1=$(create_distance "$E5_COMP_ID" "$TOKEN_ORG2" '{
  "name": "Tourism Course",
  "distance_meters": 8000,
  "climb_meters": 200,
  "classes": ["Open"],
  "control_points": [
    {"code": "S", "type": "start"},
    {"code": "T1", "type": "control"},
    {"code": "T2", "type": "control"},
    {"code": "F", "type": "finish"}
  ]
}')
E5_D1_ID=$(echo "$E5_D1" | jq -r '.id')
ok "E5 distance: Tourism Course ($E5_D1_ID)"

# Event 6 — multi-stage orient (3 comps)
E6_D1=$(create_distance "$E6_C1_ID" "$TOKEN_ORG1" '{
  "name": "City Sprint",
  "distance_meters": 3000,
  "climb_meters": 40,
  "classes": ["M21", "W21"],
  "control_points": [
    {"code": "S", "type": "start"}, {"code": "41", "type": "control"}, {"code": "42", "type": "control"},
    {"code": "43", "type": "control"}, {"code": "44", "type": "control"}, {"code": "F", "type": "finish"}
  ]
}')
E6_D1_ID=$(echo "$E6_D1" | jq -r '.id')

E6_D2=$(create_distance "$E6_C2_ID" "$TOKEN_ORG1" '{
  "name": "Forest Middle",
  "distance_meters": 6000,
  "climb_meters": 120,
  "classes": ["M21", "W21"],
  "control_points": [
    {"code": "S", "type": "start"}, {"code": "51", "type": "control"}, {"code": "52", "type": "control"},
    {"code": "53", "type": "control"}, {"code": "54", "type": "control"}, {"code": "55", "type": "control"},
    {"code": "56", "type": "control"}, {"code": "F", "type": "finish"}
  ]
}')
E6_D2_ID=$(echo "$E6_D2" | jq -r '.id')

E6_D3=$(create_distance "$E6_C3_ID" "$TOKEN_ORG1" '{
  "name": "Long Classic",
  "distance_meters": 12000,
  "climb_meters": 250,
  "classes": ["M21", "W21"],
  "control_points": [
    {"code": "S", "type": "start"}, {"code": "61", "type": "control"}, {"code": "62", "type": "control"},
    {"code": "63", "type": "control"}, {"code": "64", "type": "control"}, {"code": "65", "type": "control"},
    {"code": "66", "type": "control"}, {"code": "67", "type": "control"}, {"code": "68", "type": "control"},
    {"code": "F", "type": "finish"}
  ]
}')
E6_D3_ID=$(echo "$E6_D3" | jq -r '.id')
ok "E6 distances: 3 created"

# Event 7 — multi-stage run (3 comps)
E7_D1=$(create_distance "$E7_C1_ID" "$TOKEN_ORG1" '{
  "name": "5K Warm-up Route",
  "distance_meters": 5000,
  "classes": ["Open", "Senior"],
  "control_points": [
    {"code": "S", "type": "start"}, {"code": "1K", "type": "control"}, {"code": "2.5K", "type": "control"},
    {"code": "4K", "type": "control"}, {"code": "F", "type": "finish"}
  ]
}')
E7_D1_ID=$(echo "$E7_D1" | jq -r '.id')

E7_D2=$(create_distance "$E7_C2_ID" "$TOKEN_ORG1" '{
  "name": "10K Main Route",
  "distance_meters": 10000,
  "classes": ["Open", "Senior"],
  "control_points": [
    {"code": "S", "type": "start"}, {"code": "2K", "type": "control"}, {"code": "5K", "type": "control"},
    {"code": "8K", "type": "control"}, {"code": "F", "type": "finish"}
  ]
}')
E7_D2_ID=$(echo "$E7_D2" | jq -r '.id')

E7_D3=$(create_distance "$E7_C3_ID" "$TOKEN_ORG1" '{
  "name": "Half Marathon Route",
  "distance_meters": 21097,
  "classes": ["Open", "Senior"],
  "control_points": [
    {"code": "S", "type": "start"}, {"code": "5K", "type": "control"}, {"code": "10K", "type": "control"},
    {"code": "15K", "type": "control"}, {"code": "20K", "type": "control"}, {"code": "F", "type": "finish"}
  ]
}')
E7_D3_ID=$(echo "$E7_D3" | jq -r '.id')
ok "E7 distances: 3 created"

# Event 8 — multi-stage bike (3 comps)
E8_D1=$(create_distance "$E8_C1_ID" "$TOKEN_ORG2" '{
  "name": "TT Course",
  "distance_meters": 15000,
  "climb_meters": 200,
  "classes": ["Elite", "Amateur"],
  "control_points": [
    {"code": "S", "type": "start"}, {"code": "CP1", "type": "control"}, {"code": "CP2", "type": "control"},
    {"code": "F", "type": "finish"}
  ]
}')
E8_D1_ID=$(echo "$E8_D1" | jq -r '.id')

E8_D2=$(create_distance "$E8_C2_ID" "$TOKEN_ORG2" '{
  "name": "XC Course",
  "distance_meters": 30000,
  "climb_meters": 600,
  "classes": ["Elite", "Amateur"],
  "control_points": [
    {"code": "S", "type": "start"}, {"code": "CP1", "type": "control"}, {"code": "CP2", "type": "control"},
    {"code": "CP3", "type": "control"}, {"code": "F", "type": "finish"}
  ]
}')
E8_D2_ID=$(echo "$E8_D2" | jq -r '.id')

E8_D3=$(create_distance "$E8_C3_ID" "$TOKEN_ORG2" '{
  "name": "DH Course",
  "distance_meters": 5000,
  "climb_meters": 800,
  "classes": ["Elite", "Amateur"],
  "control_points": [
    {"code": "S", "type": "start"}, {"code": "CP1", "type": "control"}, {"code": "F", "type": "finish"}
  ]
}')
E8_D3_ID=$(echo "$E8_D3" | jq -r '.id')
ok "E8 distances: 3 created"

# ═══════════════════════════════════════════════════════════════════════════════
# 5. ADD TEAM MEMBERS to events
# ═══════════════════════════════════════════════════════════════════════════════
log "Adding team members"

add_team() {
  local event_id="$1" token="$2" body="$3"
  post "$BASE_URL/events/$event_id/team" "$token" "$body" > /dev/null
}

# Add secretary, judge, volunteer to events 2,3,4,6,7,8 (ones that will go beyond draft)
for EID in $E2_ID $E3_ID $E4_ID $E6_ID $E7_ID $E8_ID; do
  # Determine which organizer token to use
  TOKEN="$TOKEN_ORG1"
  if [ "$EID" = "$E8_ID" ]; then TOKEN="$TOKEN_ORG2"; fi

  add_team "$EID" "$TOKEN" "{\"user_id\": $ID_SEC, \"role\": \"secretary\"}"
  add_team "$EID" "$TOKEN" "{\"user_id\": $ID_JUDGE, \"role\": \"judge\"}"
  add_team "$EID" "$TOKEN" "{\"user_id\": $ID_VOL, \"role\": \"volunteer\"}"
done

# Add team to event 10 (will be cancelled but needs planned first)
add_team "$E10_ID" "$TOKEN_ORG2" "{\"user_id\": $ID_SEC, \"role\": \"secretary\"}"
add_team "$E10_ID" "$TOKEN_ORG2" "{\"user_id\": $ID_JUDGE, \"role\": \"judge\"}"
ok "Team members added to events"

# ═══════════════════════════════════════════════════════════════════════════════
# 6. TRANSITION EVENTS TO PLANNED
# ═══════════════════════════════════════════════════════════════════════════════
log "Transitioning events to planned"

# Single events: draft → planned (auto-syncs competition to registration_open)
# Events 2,3,4 (org1) and 5,10 (org2)
patch "$BASE_URL/events/$E2_ID" "$TOKEN_ORG1" '{"status": "planned"}' > /dev/null
ok "Event 2 → planned"
patch "$BASE_URL/events/$E3_ID" "$TOKEN_ORG1" '{"status": "planned"}' > /dev/null
ok "Event 3 → planned"
patch "$BASE_URL/events/$E4_ID" "$TOKEN_ORG1" '{"status": "planned"}' > /dev/null
ok "Event 4 → planned"

# Multi-stage events: draft → planned
patch "$BASE_URL/events/$E6_ID" "$TOKEN_ORG1" '{"status": "planned"}' > /dev/null
ok "Event 6 → planned"
patch "$BASE_URL/events/$E7_ID" "$TOKEN_ORG1" '{"status": "planned"}' > /dev/null
ok "Event 7 → planned"
patch "$BASE_URL/events/$E8_ID" "$TOKEN_ORG2" '{"status": "planned"}' > /dev/null
ok "Event 8 → planned"
patch "$BASE_URL/events/$E10_ID" "$TOKEN_ORG2" '{"status": "planned"}' > /dev/null
ok "Event 10 → planned"

# Single-event competitions need manual transition to registration_open
# (sync_single_event_competition_status only flushes, doesn't commit)
patch "$BASE_URL/events/$E2_ID/competitions/$E2_COMP_ID" "$TOKEN_ORG1" '{"status": "registration_open"}' > /dev/null
patch "$BASE_URL/events/$E3_ID/competitions/$E3_COMP_ID" "$TOKEN_ORG1" '{"status": "registration_open"}' > /dev/null
patch "$BASE_URL/events/$E4_ID/competitions/$E4_COMP_ID" "$TOKEN_ORG1" '{"status": "registration_open"}' > /dev/null
ok "Single-event competitions → registration_open"

# ═══════════════════════════════════════════════════════════════════════════════
# 7. JOIN ATHLETES as participants (public events → auto-approved)
# ═══════════════════════════════════════════════════════════════════════════════
log "Athletes joining events"

join_event() {
  local event_id="$1" token="$2"
  post "$BASE_URL/events/$event_id/join" "$token" '{"role": "participant"}' > /dev/null
}

# Athletes join events 2,3,4,6,7,8
for EID in $E2_ID $E3_ID $E4_ID $E6_ID $E7_ID $E8_ID; do
  for TATH in "$TOKEN_ATH1" "$TOKEN_ATH2" "$TOKEN_ATH3" "$TOKEN_ATH4" "$TOKEN_ATH5"; do
    join_event "$EID" "$TATH"
  done
done
ok "5 athletes joined events 2,3,4,6,7,8"

# ═══════════════════════════════════════════════════════════════════════════════
# 8. OPEN REGISTRATION on multi-stage competitions
# ═══════════════════════════════════════════════════════════════════════════════
log "Opening registration on multi-stage competitions"

# Multi-stage competitions are in PLANNED state; transition to registration_open
for CID in $E6_C1_ID $E6_C2_ID $E6_C3_ID $E7_C1_ID $E7_C2_ID $E7_C3_ID $E8_C1_ID $E8_C2_ID $E8_C3_ID; do
  # Determine token
  TOKEN="$TOKEN_ORG1"
  if [ "$CID" = "$E8_C1_ID" ] || [ "$CID" = "$E8_C2_ID" ] || [ "$CID" = "$E8_C3_ID" ]; then
    TOKEN="$TOKEN_ORG2"
    EID_FOR="$E8_ID"
  elif [ "$CID" = "$E6_C1_ID" ] || [ "$CID" = "$E6_C2_ID" ] || [ "$CID" = "$E6_C3_ID" ]; then
    EID_FOR="$E6_ID"
  else
    EID_FOR="$E7_ID"
  fi
  patch "$BASE_URL/events/$EID_FOR/competitions/$CID" "$TOKEN" '{"status": "registration_open"}' > /dev/null
done
ok "All multi-stage competitions → registration_open"

# ═══════════════════════════════════════════════════════════════════════════════
# 9. REGISTER ATHLETES for competitions
# ═══════════════════════════════════════════════════════════════════════════════
log "Registering athletes for competitions"

register_athlete() {
  local comp_id="$1" token="$2" class="$3"
  post "$BASE_URL/competitions/$comp_id/register" "$token" "{\"class\": \"$class\"}"
}

# Single-event competitions (registration already open via event → planned auto-sync)
# E2 (run 5K) — classes: Open, Senior
for TATH in "$TOKEN_ATH1" "$TOKEN_ATH2" "$TOKEN_ATH3"; do
  register_athlete "$E2_COMP_ID" "$TATH" "Open" > /dev/null
done
for TATH in "$TOKEN_ATH4" "$TOKEN_ATH5"; do
  register_athlete "$E2_COMP_ID" "$TATH" "Senior" > /dev/null
done
ok "E2: 5 athletes registered"

# E3 (bike) — classes: Elite, Amateur
for TATH in "$TOKEN_ATH1" "$TOKEN_ATH2"; do
  register_athlete "$E3_COMP_ID" "$TATH" "Elite" > /dev/null
done
for TATH in "$TOKEN_ATH3" "$TOKEN_ATH4" "$TOKEN_ATH5"; do
  register_athlete "$E3_COMP_ID" "$TATH" "Amateur" > /dev/null
done
ok "E3: 5 athletes registered"

# E4 (ski sprint) — classes: M21, W21
for TATH in "$TOKEN_ATH1" "$TOKEN_ATH3" "$TOKEN_ATH5"; do
  register_athlete "$E4_COMP_ID" "$TATH" "M21" > /dev/null
done
for TATH in "$TOKEN_ATH2" "$TOKEN_ATH4"; do
  register_athlete "$E4_COMP_ID" "$TATH" "W21" > /dev/null
done
ok "E4: 5 athletes registered"

# Multi-stage competitions
# E6 (orient) — all 3 comps, classes M21/W21
for CID in $E6_C1_ID $E6_C2_ID $E6_C3_ID; do
  for TATH in "$TOKEN_ATH1" "$TOKEN_ATH3" "$TOKEN_ATH5"; do
    register_athlete "$CID" "$TATH" "M21" > /dev/null
  done
  for TATH in "$TOKEN_ATH2" "$TOKEN_ATH4"; do
    register_athlete "$CID" "$TATH" "W21" > /dev/null
  done
done
ok "E6: 5 athletes registered for all 3 comps"

# E7 (run) — all 3 comps, classes Open/Senior
for CID in $E7_C1_ID $E7_C2_ID $E7_C3_ID; do
  for TATH in "$TOKEN_ATH1" "$TOKEN_ATH2" "$TOKEN_ATH3"; do
    register_athlete "$CID" "$TATH" "Open" > /dev/null
  done
  for TATH in "$TOKEN_ATH4" "$TOKEN_ATH5"; do
    register_athlete "$CID" "$TATH" "Senior" > /dev/null
  done
done
ok "E7: 5 athletes registered for all 3 comps"

# E8 (bike) — all 3 comps, classes Elite/Amateur
for CID in $E8_C1_ID $E8_C2_ID $E8_C3_ID; do
  for TATH in "$TOKEN_ATH1" "$TOKEN_ATH2"; do
    register_athlete "$CID" "$TATH" "Elite" > /dev/null
  done
  for TATH in "$TOKEN_ATH3" "$TOKEN_ATH4" "$TOKEN_ATH5"; do
    register_athlete "$CID" "$TATH" "Amateur" > /dev/null
  done
done
ok "E8: 5 athletes registered for all 3 comps"

# ═══════════════════════════════════════════════════════════════════════════════
# 10. SET BIB NUMBERS & START TIMES (batch update → confirmed)
# ═══════════════════════════════════════════════════════════════════════════════
log "Setting bib numbers and start times"

# Helper: fetch registrations for a competition and build batch update payload
build_batch_payload() {
  local comp_id="$1" token="$2" start_format="$3"
  local regs bib_start=100 payload="["
  regs=$(get "$BASE_URL/competitions/$comp_id/registrations?limit=100" "$token")

  local first=true
  local counter=1
  echo "$regs" | jq -c '.registrations[]' | while read -r reg; do
    local reg_id
    reg_id=$(echo "$reg" | jq -r '.id')
    local bib=$((bib_start + counter))

    if [ "$start_format" = "separated_start" ]; then
      # Generate start times 2 minutes apart
      local minutes=$((counter * 2))
      local hour=$((10 + minutes / 60))
      local min=$((minutes % 60))
      printf '{"registration_id": %s, "bib_number": "%s", "start_time": "2026-01-01T%02d:%02d:00"}' \
        "$reg_id" "$bib" "$hour" "$min"
    else
      printf '{"registration_id": %s, "bib_number": "%s"}' "$reg_id" "$bib"
    fi
    counter=$((counter + 1))
  done
}

# Simpler approach: get registrations, then batch update with jq
batch_confirm() {
  local comp_id="$1" token="$2" start_format="$3" base_bib="$4" date_str="$5"
  local regs
  regs=$(get "$BASE_URL/competitions/$comp_id/registrations?limit=100" "$token")

  local items="[]"
  local counter=0
  for reg_id in $(echo "$regs" | jq -r '.registrations[].id'); do
    counter=$((counter + 1))
    local bib="${base_bib}$(printf '%02d' $counter)"

    if [ "$start_format" = "separated_start" ]; then
      local minutes=$((counter * 2))
      local hour=$((10 + minutes / 60))
      local min=$((minutes % 60))
      local st
      st=$(printf '%sT%02d:%02d:00' "$date_str" "$hour" "$min")
      items=$(echo "$items" | jq --arg rid "$reg_id" --arg bib "$bib" --arg st "$st" \
        '. + [{"registration_id": ($rid|tonumber), "bib_number": $bib, "start_time": $st}]')
    else
      items=$(echo "$items" | jq --arg rid "$reg_id" --arg bib "$bib" \
        '. + [{"registration_id": ($rid|tonumber), "bib_number": $bib}]')
    fi
  done

  local body
  body=$(jq -n --argjson regs "$items" '{"registrations": $regs, "set_status": "confirmed"}')
  post "$BASE_URL/competitions/$comp_id/registrations/batch" "$token" "$body" > /dev/null
}

# Single event competitions
batch_confirm "$E2_COMP_ID" "$TOKEN_ORG1" "mass_start" "2" "2026-03-15"
ok "E2 comp: bibs set, confirmed"

batch_confirm "$E3_COMP_ID" "$TOKEN_ORG1" "mass_start" "3" "2026-02-25"
ok "E3 comp: bibs set, confirmed"

batch_confirm "$E4_COMP_ID" "$TOKEN_ORG1" "separated_start" "4" "2026-02-10"
ok "E4 comp: bibs + start times set, confirmed"

# Multi-stage event competitions
# E7 — past comps (C1 date=2026-02-20, C2 date=2026-02-24)
batch_confirm "$E7_C1_ID" "$TOKEN_ORG1" "mass_start" "71" "2026-02-20"
batch_confirm "$E7_C2_ID" "$TOKEN_ORG1" "mass_start" "72" "2026-02-24"
batch_confirm "$E7_C3_ID" "$TOKEN_ORG1" "separated_start" "73" "2026-02-28"
ok "E7 comps: bibs set, confirmed"

# E8 — all past
batch_confirm "$E8_C1_ID" "$TOKEN_ORG2" "separated_start" "81" "2026-01-10"
batch_confirm "$E8_C2_ID" "$TOKEN_ORG2" "mass_start" "82" "2026-01-11"
batch_confirm "$E8_C3_ID" "$TOKEN_ORG2" "mass_start" "83" "2026-01-12"
ok "E8 comps: bibs set, confirmed"

# E6 — future, still set bibs for completeness
batch_confirm "$E6_C1_ID" "$TOKEN_ORG1" "separated_start" "61" "2026-09-20"
batch_confirm "$E6_C2_ID" "$TOKEN_ORG1" "separated_start" "62" "2026-09-21"
batch_confirm "$E6_C3_ID" "$TOKEN_ORG1" "mass_start" "63" "2026-09-22"
ok "E6 comps: bibs set, confirmed"

# ═══════════════════════════════════════════════════════════════════════════════
# 11. TRANSITION COMPETITIONS TO IN_PROGRESS (where date allows)
# ═══════════════════════════════════════════════════════════════════════════════
log "Transitioning competitions to in_progress"

# Single-event competitions: manually transition (auto-sync doesn't commit)
# E3 comp — today (2026-02-25), mass_start, bibs set
patch "$BASE_URL/events/$E3_ID/competitions/$E3_COMP_ID" "$TOKEN_ORG1" '{"status": "registration_closed"}' > /dev/null
patch "$BASE_URL/events/$E3_ID/competitions/$E3_COMP_ID" "$TOKEN_ORG1" '{"status": "in_progress"}' > /dev/null
ok "E3 comp → in_progress"

# E4 comp — past (2026-02-10), separated_start, bibs+times set
patch "$BASE_URL/events/$E4_ID/competitions/$E4_COMP_ID" "$TOKEN_ORG1" '{"status": "registration_closed"}' > /dev/null
patch "$BASE_URL/events/$E4_ID/competitions/$E4_COMP_ID" "$TOKEN_ORG1" '{"status": "in_progress"}' > /dev/null
ok "E4 comp → in_progress"

# E7 C1 (2026-02-20 — past, mass_start)
patch "$BASE_URL/events/$E7_ID/competitions/$E7_C1_ID" "$TOKEN_ORG1" '{"status": "registration_closed"}' > /dev/null
patch "$BASE_URL/events/$E7_ID/competitions/$E7_C1_ID" "$TOKEN_ORG1" '{"status": "in_progress"}' > /dev/null
ok "E7 C1 → in_progress"

# E7 C2 (2026-02-24 — past, mass_start)
patch "$BASE_URL/events/$E7_ID/competitions/$E7_C2_ID" "$TOKEN_ORG1" '{"status": "registration_closed"}' > /dev/null
patch "$BASE_URL/events/$E7_ID/competitions/$E7_C2_ID" "$TOKEN_ORG1" '{"status": "in_progress"}' > /dev/null
ok "E7 C2 → in_progress"

# E8 all 3 comps — all past
for CID in $E8_C1_ID $E8_C2_ID $E8_C3_ID; do
  patch "$BASE_URL/events/$E8_ID/competitions/$CID" "$TOKEN_ORG2" '{"status": "registration_closed"}' > /dev/null
  patch "$BASE_URL/events/$E8_ID/competitions/$CID" "$TOKEN_ORG2" '{"status": "in_progress"}' > /dev/null
done
ok "E8 all comps → in_progress"

# ═══════════════════════════════════════════════════════════════════════════════
# 12. TRANSITION EVENTS TO IN_PROGRESS
# ═══════════════════════════════════════════════════════════════════════════════
log "Transitioning events to in_progress"

# E3 — today (2026-02-25), single format: auto-syncs competition
patch "$BASE_URL/events/$E3_ID" "$TOKEN_ORG1" '{"status": "in_progress"}' > /dev/null
ok "Event 3 → in_progress"

# E7 — start_date 2026-02-20 (past), multi_stage
patch "$BASE_URL/events/$E7_ID" "$TOKEN_ORG1" '{"status": "in_progress"}' > /dev/null
ok "Event 7 → in_progress"

# E4 — start_date 2026-02-10 (past), single format
patch "$BASE_URL/events/$E4_ID" "$TOKEN_ORG1" '{"status": "in_progress"}' > /dev/null
ok "Event 4 → in_progress"

# E8 — start_date 2026-01-10 (past), multi_stage
patch "$BASE_URL/events/$E8_ID" "$TOKEN_ORG2" '{"status": "in_progress"}' > /dev/null
ok "Event 8 → in_progress"

# ═══════════════════════════════════════════════════════════════════════════════
# 13. CREATE RESULTS with splits (for competitions that will finish)
# ═══════════════════════════════════════════════════════════════════════════════
log "Creating results with splits"

create_result() {
  local comp_id="$1" token="$2" body="$3"
  post "$BASE_URL/competitions/$comp_id/results" "$token" "$body" > /dev/null
}

# E4 (ski sprint — CPs: S, 500m, 1000m, F)
# M21 athletes: ATH1, ATH3, ATH5
create_result "$E4_COMP_ID" "$TOKEN_ORG1" "{
  \"user_id\": $ID_ATH1, \"class\": \"M21\", \"time_total\": 185000, \"status\": \"ok\",
  \"splits\": [
    {\"control_point\": \"S\", \"cumulative_time\": 0},
    {\"control_point\": \"500m\", \"cumulative_time\": 62000},
    {\"control_point\": \"1000m\", \"cumulative_time\": 128000},
    {\"control_point\": \"F\", \"cumulative_time\": 185000}
  ]
}"
create_result "$E4_COMP_ID" "$TOKEN_ORG1" "{
  \"user_id\": $ID_ATH3, \"class\": \"M21\", \"time_total\": 192000, \"status\": \"ok\",
  \"splits\": [
    {\"control_point\": \"S\", \"cumulative_time\": 0},
    {\"control_point\": \"500m\", \"cumulative_time\": 65000},
    {\"control_point\": \"1000m\", \"cumulative_time\": 134000},
    {\"control_point\": \"F\", \"cumulative_time\": 192000}
  ]
}"
create_result "$E4_COMP_ID" "$TOKEN_ORG1" "{
  \"user_id\": $ID_ATH5, \"class\": \"M21\", \"time_total\": 198000, \"status\": \"ok\",
  \"splits\": [
    {\"control_point\": \"S\", \"cumulative_time\": 0},
    {\"control_point\": \"500m\", \"cumulative_time\": 68000},
    {\"control_point\": \"1000m\", \"cumulative_time\": 140000},
    {\"control_point\": \"F\", \"cumulative_time\": 198000}
  ]
}"
# W21 athletes: ATH2, ATH4
create_result "$E4_COMP_ID" "$TOKEN_ORG1" "{
  \"user_id\": $ID_ATH2, \"class\": \"W21\", \"time_total\": 205000, \"status\": \"ok\",
  \"splits\": [
    {\"control_point\": \"S\", \"cumulative_time\": 0},
    {\"control_point\": \"500m\", \"cumulative_time\": 70000},
    {\"control_point\": \"1000m\", \"cumulative_time\": 145000},
    {\"control_point\": \"F\", \"cumulative_time\": 205000}
  ]
}"
create_result "$E4_COMP_ID" "$TOKEN_ORG1" "{
  \"user_id\": $ID_ATH4, \"class\": \"W21\", \"time_total\": 210000, \"status\": \"ok\",
  \"splits\": [
    {\"control_point\": \"S\", \"cumulative_time\": 0},
    {\"control_point\": \"500m\", \"cumulative_time\": 72000},
    {\"control_point\": \"1000m\", \"cumulative_time\": 148000},
    {\"control_point\": \"F\", \"cumulative_time\": 210000}
  ]
}"
ok "E4: 5 results created"

# E8 C1 (Time Trial — CPs: S, CP1, CP2, F)
create_result "$E8_C1_ID" "$TOKEN_ORG2" "{
  \"user_id\": $ID_ATH1, \"class\": \"Elite\", \"time_total\": 1520000, \"status\": \"ok\",
  \"splits\": [
    {\"control_point\": \"S\", \"cumulative_time\": 0},
    {\"control_point\": \"CP1\", \"cumulative_time\": 780000},
    {\"control_point\": \"CP2\", \"cumulative_time\": 1350000},
    {\"control_point\": \"F\", \"cumulative_time\": 1520000}
  ]
}"
create_result "$E8_C1_ID" "$TOKEN_ORG2" "{
  \"user_id\": $ID_ATH2, \"class\": \"Elite\", \"time_total\": 1580000, \"status\": \"ok\",
  \"splits\": [
    {\"control_point\": \"S\", \"cumulative_time\": 0},
    {\"control_point\": \"CP1\", \"cumulative_time\": 810000},
    {\"control_point\": \"CP2\", \"cumulative_time\": 1400000},
    {\"control_point\": \"F\", \"cumulative_time\": 1580000}
  ]
}"
create_result "$E8_C1_ID" "$TOKEN_ORG2" "{
  \"user_id\": $ID_ATH3, \"class\": \"Amateur\", \"time_total\": 1850000, \"status\": \"ok\",
  \"splits\": [
    {\"control_point\": \"S\", \"cumulative_time\": 0},
    {\"control_point\": \"CP1\", \"cumulative_time\": 950000},
    {\"control_point\": \"CP2\", \"cumulative_time\": 1650000},
    {\"control_point\": \"F\", \"cumulative_time\": 1850000}
  ]
}"
create_result "$E8_C1_ID" "$TOKEN_ORG2" "{
  \"user_id\": $ID_ATH4, \"class\": \"Amateur\", \"time_total\": 1920000, \"status\": \"ok\",
  \"splits\": [
    {\"control_point\": \"S\", \"cumulative_time\": 0},
    {\"control_point\": \"CP1\", \"cumulative_time\": 980000},
    {\"control_point\": \"CP2\", \"cumulative_time\": 1700000},
    {\"control_point\": \"F\", \"cumulative_time\": 1920000}
  ]
}"
create_result "$E8_C1_ID" "$TOKEN_ORG2" "{
  \"user_id\": $ID_ATH5, \"class\": \"Amateur\", \"time_total\": 1980000, \"status\": \"ok\",
  \"splits\": [
    {\"control_point\": \"S\", \"cumulative_time\": 0},
    {\"control_point\": \"CP1\", \"cumulative_time\": 1020000},
    {\"control_point\": \"CP2\", \"cumulative_time\": 1750000},
    {\"control_point\": \"F\", \"cumulative_time\": 1980000}
  ]
}"
ok "E8 C1: 5 results"

# E8 C2 (Cross-Country — CPs: S, CP1, CP2, CP3, F)
create_result "$E8_C2_ID" "$TOKEN_ORG2" "{
  \"user_id\": $ID_ATH1, \"class\": \"Elite\", \"time_total\": 3600000, \"status\": \"ok\",
  \"splits\": [
    {\"control_point\": \"S\", \"cumulative_time\": 0},
    {\"control_point\": \"CP1\", \"cumulative_time\": 1200000},
    {\"control_point\": \"CP2\", \"cumulative_time\": 2400000},
    {\"control_point\": \"CP3\", \"cumulative_time\": 3300000},
    {\"control_point\": \"F\", \"cumulative_time\": 3600000}
  ]
}"
create_result "$E8_C2_ID" "$TOKEN_ORG2" "{
  \"user_id\": $ID_ATH2, \"class\": \"Elite\", \"time_total\": 3720000, \"status\": \"ok\",
  \"splits\": [
    {\"control_point\": \"S\", \"cumulative_time\": 0},
    {\"control_point\": \"CP1\", \"cumulative_time\": 1250000},
    {\"control_point\": \"CP2\", \"cumulative_time\": 2500000},
    {\"control_point\": \"CP3\", \"cumulative_time\": 3420000},
    {\"control_point\": \"F\", \"cumulative_time\": 3720000}
  ]
}"
create_result "$E8_C2_ID" "$TOKEN_ORG2" "{
  \"user_id\": $ID_ATH3, \"class\": \"Amateur\", \"time_total\": 4200000, \"status\": \"ok\",
  \"splits\": [
    {\"control_point\": \"S\", \"cumulative_time\": 0},
    {\"control_point\": \"CP1\", \"cumulative_time\": 1400000},
    {\"control_point\": \"CP2\", \"cumulative_time\": 2800000},
    {\"control_point\": \"CP3\", \"cumulative_time\": 3850000},
    {\"control_point\": \"F\", \"cumulative_time\": 4200000}
  ]
}"
create_result "$E8_C2_ID" "$TOKEN_ORG2" "{
  \"user_id\": $ID_ATH4, \"class\": \"Amateur\", \"time_total\": 4350000, \"status\": \"ok\",
  \"splits\": [
    {\"control_point\": \"S\", \"cumulative_time\": 0},
    {\"control_point\": \"CP1\", \"cumulative_time\": 1450000},
    {\"control_point\": \"CP2\", \"cumulative_time\": 2900000},
    {\"control_point\": \"CP3\", \"cumulative_time\": 3980000},
    {\"control_point\": \"F\", \"cumulative_time\": 4350000}
  ]
}"
create_result "$E8_C2_ID" "$TOKEN_ORG2" "{
  \"user_id\": $ID_ATH5, \"class\": \"Amateur\", \"time_total\": 4500000, \"status\": \"dnf\",
  \"splits\": [
    {\"control_point\": \"S\", \"cumulative_time\": 0},
    {\"control_point\": \"CP1\", \"cumulative_time\": 1500000},
    {\"control_point\": \"CP2\", \"cumulative_time\": 3100000},
    {\"control_point\": \"CP3\", \"cumulative_time\": 4100000},
    {\"control_point\": \"F\", \"cumulative_time\": 4500000}
  ]
}"
ok "E8 C2: 5 results (1 DNF)"

# E8 C3 (Downhill — CPs: S, CP1, F)
create_result "$E8_C3_ID" "$TOKEN_ORG2" "{
  \"user_id\": $ID_ATH1, \"class\": \"Elite\", \"time_total\": 420000, \"status\": \"ok\",
  \"splits\": [
    {\"control_point\": \"S\", \"cumulative_time\": 0},
    {\"control_point\": \"CP1\", \"cumulative_time\": 210000},
    {\"control_point\": \"F\", \"cumulative_time\": 420000}
  ]
}"
create_result "$E8_C3_ID" "$TOKEN_ORG2" "{
  \"user_id\": $ID_ATH2, \"class\": \"Elite\", \"time_total\": 435000, \"status\": \"ok\",
  \"splits\": [
    {\"control_point\": \"S\", \"cumulative_time\": 0},
    {\"control_point\": \"CP1\", \"cumulative_time\": 220000},
    {\"control_point\": \"F\", \"cumulative_time\": 435000}
  ]
}"
create_result "$E8_C3_ID" "$TOKEN_ORG2" "{
  \"user_id\": $ID_ATH3, \"class\": \"Amateur\", \"time_total\": 510000, \"status\": \"ok\",
  \"splits\": [
    {\"control_point\": \"S\", \"cumulative_time\": 0},
    {\"control_point\": \"CP1\", \"cumulative_time\": 260000},
    {\"control_point\": \"F\", \"cumulative_time\": 510000}
  ]
}"
create_result "$E8_C3_ID" "$TOKEN_ORG2" "{
  \"user_id\": $ID_ATH4, \"class\": \"Amateur\", \"time_total\": 540000, \"status\": \"ok\",
  \"splits\": [
    {\"control_point\": \"S\", \"cumulative_time\": 0},
    {\"control_point\": \"CP1\", \"cumulative_time\": 275000},
    {\"control_point\": \"F\", \"cumulative_time\": 540000}
  ]
}"
create_result "$E8_C3_ID" "$TOKEN_ORG2" "{
  \"user_id\": $ID_ATH5, \"class\": \"Amateur\", \"time_total\": 560000, \"status\": \"dsq\",
  \"splits\": [
    {\"control_point\": \"S\", \"cumulative_time\": 0},
    {\"control_point\": \"CP1\", \"cumulative_time\": 280000},
    {\"control_point\": \"F\", \"cumulative_time\": 560000}
  ]
}"
ok "E8 C3: 5 results (1 DSQ)"

# E7 C1 (5K Warm-up — CPs: S, 1K, 2.5K, 4K, F)
create_result "$E7_C1_ID" "$TOKEN_ORG1" "{
  \"user_id\": $ID_ATH1, \"class\": \"Open\", \"time_total\": 1200000, \"status\": \"ok\",
  \"splits\": [
    {\"control_point\": \"S\", \"cumulative_time\": 0},
    {\"control_point\": \"1K\", \"cumulative_time\": 240000},
    {\"control_point\": \"2.5K\", \"cumulative_time\": 600000},
    {\"control_point\": \"4K\", \"cumulative_time\": 960000},
    {\"control_point\": \"F\", \"cumulative_time\": 1200000}
  ]
}"
create_result "$E7_C1_ID" "$TOKEN_ORG1" "{
  \"user_id\": $ID_ATH2, \"class\": \"Open\", \"time_total\": 1250000, \"status\": \"ok\",
  \"splits\": [
    {\"control_point\": \"S\", \"cumulative_time\": 0},
    {\"control_point\": \"1K\", \"cumulative_time\": 250000},
    {\"control_point\": \"2.5K\", \"cumulative_time\": 625000},
    {\"control_point\": \"4K\", \"cumulative_time\": 1000000},
    {\"control_point\": \"F\", \"cumulative_time\": 1250000}
  ]
}"
create_result "$E7_C1_ID" "$TOKEN_ORG1" "{
  \"user_id\": $ID_ATH3, \"class\": \"Open\", \"time_total\": 1300000, \"status\": \"ok\",
  \"splits\": [
    {\"control_point\": \"S\", \"cumulative_time\": 0},
    {\"control_point\": \"1K\", \"cumulative_time\": 260000},
    {\"control_point\": \"2.5K\", \"cumulative_time\": 650000},
    {\"control_point\": \"4K\", \"cumulative_time\": 1040000},
    {\"control_point\": \"F\", \"cumulative_time\": 1300000}
  ]
}"
create_result "$E7_C1_ID" "$TOKEN_ORG1" "{
  \"user_id\": $ID_ATH4, \"class\": \"Senior\", \"time_total\": 1350000, \"status\": \"ok\",
  \"splits\": [
    {\"control_point\": \"S\", \"cumulative_time\": 0},
    {\"control_point\": \"1K\", \"cumulative_time\": 270000},
    {\"control_point\": \"2.5K\", \"cumulative_time\": 675000},
    {\"control_point\": \"4K\", \"cumulative_time\": 1080000},
    {\"control_point\": \"F\", \"cumulative_time\": 1350000}
  ]
}"
create_result "$E7_C1_ID" "$TOKEN_ORG1" "{
  \"user_id\": $ID_ATH5, \"class\": \"Senior\", \"time_total\": 1400000, \"status\": \"ok\",
  \"splits\": [
    {\"control_point\": \"S\", \"cumulative_time\": 0},
    {\"control_point\": \"1K\", \"cumulative_time\": 280000},
    {\"control_point\": \"2.5K\", \"cumulative_time\": 700000},
    {\"control_point\": \"4K\", \"cumulative_time\": 1120000},
    {\"control_point\": \"F\", \"cumulative_time\": 1400000}
  ]
}"
ok "E7 C1: 5 results"

# E7 C2 (10K — CPs: S, 2K, 5K, 8K, F) — all times in seconds
create_result "$E7_C2_ID" "$TOKEN_ORG1" "{
  \"user_id\": $ID_ATH1, \"class\": \"Open\", \"time_total\": 2400, \"status\": \"ok\",
  \"splits\": [
    {\"control_point\": \"S\", \"cumulative_time\": 0},
    {\"control_point\": \"2K\", \"cumulative_time\": 480},
    {\"control_point\": \"5K\", \"cumulative_time\": 1200},
    {\"control_point\": \"8K\", \"cumulative_time\": 1920},
    {\"control_point\": \"F\", \"cumulative_time\": 2400}
  ]
}"
create_result "$E7_C2_ID" "$TOKEN_ORG1" "{
  \"user_id\": $ID_ATH2, \"class\": \"Open\", \"time_total\": 2500, \"status\": \"ok\",
  \"splits\": [
    {\"control_point\": \"S\", \"cumulative_time\": 0},
    {\"control_point\": \"2K\", \"cumulative_time\": 500},
    {\"control_point\": \"5K\", \"cumulative_time\": 1250},
    {\"control_point\": \"8K\", \"cumulative_time\": 2000},
    {\"control_point\": \"F\", \"cumulative_time\": 2500}
  ]
}"
create_result "$E7_C2_ID" "$TOKEN_ORG1" "{
  \"user_id\": $ID_ATH3, \"class\": \"Open\", \"time_total\": 2600, \"status\": \"ok\",
  \"splits\": [
    {\"control_point\": \"S\", \"cumulative_time\": 0},
    {\"control_point\": \"2K\", \"cumulative_time\": 520},
    {\"control_point\": \"5K\", \"cumulative_time\": 1300},
    {\"control_point\": \"8K\", \"cumulative_time\": 2080},
    {\"control_point\": \"F\", \"cumulative_time\": 2600}
  ]
}"
create_result "$E7_C2_ID" "$TOKEN_ORG1" "{
  \"user_id\": $ID_ATH4, \"class\": \"Senior\", \"time_total\": 2700, \"status\": \"ok\",
  \"splits\": [
    {\"control_point\": \"S\", \"cumulative_time\": 0},
    {\"control_point\": \"2K\", \"cumulative_time\": 540},
    {\"control_point\": \"5K\", \"cumulative_time\": 1350},
    {\"control_point\": \"8K\", \"cumulative_time\": 2160},
    {\"control_point\": \"F\", \"cumulative_time\": 2700}
  ]
}"
create_result "$E7_C2_ID" "$TOKEN_ORG1" "{
  \"user_id\": $ID_ATH5, \"class\": \"Senior\", \"time_total\": 2800, \"status\": \"ok\",
  \"splits\": [
    {\"control_point\": \"S\", \"cumulative_time\": 0},
    {\"control_point\": \"2K\", \"cumulative_time\": 560},
    {\"control_point\": \"5K\", \"cumulative_time\": 1400},
    {\"control_point\": \"8K\", \"cumulative_time\": 2240},
    {\"control_point\": \"F\", \"cumulative_time\": 2800}
  ]
}"
ok "E7 C2: 5 results"

# ═══════════════════════════════════════════════════════════════════════════════
# 14. TRANSITION COMPETITIONS TO FINISHED (past date + all results in)
# ═══════════════════════════════════════════════════════════════════════════════
log "Transitioning competitions to finished"

# E4 comp — manually finish (auto-sync doesn't commit)
patch "$BASE_URL/events/$E4_ID/competitions/$E4_COMP_ID" "$TOKEN_ORG1" '{"status": "finished"}' > /dev/null
ok "E4 comp → finished"

# E8 all 3 comps (all dates in January — past)
patch "$BASE_URL/events/$E8_ID/competitions/$E8_C1_ID" "$TOKEN_ORG2" '{"status": "finished"}' > /dev/null
patch "$BASE_URL/events/$E8_ID/competitions/$E8_C2_ID" "$TOKEN_ORG2" '{"status": "finished"}' > /dev/null
patch "$BASE_URL/events/$E8_ID/competitions/$E8_C3_ID" "$TOKEN_ORG2" '{"status": "finished"}' > /dev/null
ok "E8 all comps → finished"

# E7 C1 (date 2026-02-20 — past) and C2 (date 2026-02-24 — past)
patch "$BASE_URL/events/$E7_ID/competitions/$E7_C1_ID" "$TOKEN_ORG1" '{"status": "finished"}' > /dev/null
ok "E7 C1 → finished"
patch "$BASE_URL/events/$E7_ID/competitions/$E7_C2_ID" "$TOKEN_ORG1" '{"status": "finished"}' > /dev/null
ok "E7 C2 → finished"

# ═══════════════════════════════════════════════════════════════════════════════
# 15. TRANSITION EVENTS TO FINISHED
# ═══════════════════════════════════════════════════════════════════════════════
log "Transitioning events to finished"

# E4 — single format, comp already finished
patch "$BASE_URL/events/$E4_ID" "$TOKEN_ORG1" '{"status": "finished"}' > /dev/null
ok "Event 4 → finished"

# E8 — multi_stage, all comps finished
patch "$BASE_URL/events/$E8_ID" "$TOKEN_ORG2" '{"status": "finished"}' > /dev/null
ok "Event 8 → finished"

# ═══════════════════════════════════════════════════════════════════════════════
# 16. CANCEL events 5 and 10
# ═══════════════════════════════════════════════════════════════════════════════
log "Cancelling events"

# E5 is still draft — can cancel from draft
patch "$BASE_URL/events/$E5_ID" "$TOKEN_ORG2" '{"status": "cancelled"}' > /dev/null
ok "Event 5 → cancelled"

# E10 is planned — can cancel from planned
patch "$BASE_URL/events/$E10_ID" "$TOKEN_ORG2" '{"status": "cancelled"}' > /dev/null
ok "Event 10 → cancelled"

# ═══════════════════════════════════════════════════════════════════════════════
# VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════════
log "Verification"

echo ""
echo "Events summary:"
get "$BASE_URL/events?limit=20" | jq '[.events[] | {id, name, status, sport_kind, event_format}]'

echo ""
echo "Feed check:"
get "$BASE_URL/feed?limit=20" | jq '.total'

log "Seed data complete!"
echo ""
echo "Test accounts (username / password):"
echo "  organizer1 / organizer1"
echo "  organizer2 / organizer2"
echo "  secretary1 / secretary1"
echo "  judge1    / judge1judge1"
echo "  athlete1  / athlete1a"
echo "  athlete2  / athlete2a"
echo "  athlete3  / athlete3a"
echo "  athlete4  / athlete4a"
echo "  athlete5  / athlete5a"
echo "  volunteer1 / volunteer1"
