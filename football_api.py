import time
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from config import SPORTMONKS_API_TOKEN, BASE_URL, TIMEZONE


UPCOMING_STATES = {
    "NS",
    "TBD",
    "LIVE",
    "1H",
    "HT",
    "2H",
    "ET",
    "BT",
    "P"
}

FINISHED_STATES = {
    "FT",
    "AET",
    "PEN"
}

BET365_BOOKMAKER_ID = 2

# Cache fixture details so we don't request the same fixture many times.
FIXTURE_DETAILS_CACHE = {}


def api_get(endpoint, params=None, retries=3):
    if params is None:
        params = {}

    params["api_token"] = SPORTMONKS_API_TOKEN

    url = f"{BASE_URL}/{endpoint.lstrip('/')}"

    for attempt in range(retries):
        response = requests.get(url, params=params, timeout=30)

        if response.status_code == 200:
            payload = response.json()

            if payload.get("message"):
                print("API message:", payload.get("message"))

            return payload.get("data", [])

        if response.status_code == 429:
            wait_time = 60
            print(f"Rate limit reached. Waiting {wait_time} seconds...")
            time.sleep(wait_time)
            continue

        raise Exception(f"Sportmonks API error {response.status_code}: {response.text}")

    raise Exception("Sportmonks API rate limit still active after retries.")


def normalize_name(name):
    if not name:
        return ""

    value = str(name).lower()

    replacements = {
        "ü": "u",
        "ä": "a",
        "ö": "o",
        "ß": "ss",
        "é": "e",
        "è": "e",
        "ê": "e",
        "á": "a",
        "à": "a",
        "â": "a",
        "í": "i",
        "ì": "i",
        "î": "i",
        "ó": "o",
        "ò": "o",
        "ô": "o",
        "ú": "u",
        "ù": "u",
        "û": "u",
        ".": "",
        "-": " ",
        "_": " "
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    while "  " in value:
        value = value.replace("  ", " ")

    return value.strip()


def safe_get(dictionary, keys, default=None):
    current = dictionary

    for key in keys:
        if not isinstance(current, dict):
            return default

        current = current.get(key)

        if current is None:
            return default

    return current


def parse_sportmonks_datetime(value):
    if not value:
        return None

    # Sportmonks usually returns starting_at as UTC:
    # "2026-05-06 19:00:00"
    # We parse it as UTC, then convert it to your local TIMEZONE.
    if "T" in value:
        dt = datetime.fromisoformat(value)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))

        return dt.astimezone(ZoneInfo(TIMEZONE))

    dt = datetime.fromisoformat(value)
    dt = dt.replace(tzinfo=ZoneInfo("UTC"))

    return dt.astimezone(ZoneInfo(TIMEZONE))


def get_state_short(fixture):
    state = fixture.get("state")

    if isinstance(state, dict):
        return (
            state.get("short_name")
            or state.get("code")
            or state.get("developer_name")
            or state.get("name")
            or ""
        ).upper()

    return ""


def get_participants(fixture):
    participants = fixture.get("participants", [])

    home = None
    away = None

    for participant in participants:
        meta = participant.get("meta", {})
        location = meta.get("location")

        if location == "home":
            home = participant
        elif location == "away":
            away = participant

    return home, away


def extract_score_for_participant(scores, participant_id):
    if not isinstance(scores, list):
        return None

    best_score = None

    preferred_descriptions = {
        "CURRENT",
        "FT",
        "FULLTIME",
        "FULL_TIME",
        "2ND_HALF",
        "PENALTY_SHOOTOUT"
    }

    for score_item in scores:
        if score_item.get("participant_id") != participant_id:
            continue

        score_data = score_item.get("score", {})

        if not isinstance(score_data, dict):
            continue

        goals = score_data.get("goals")

        if goals is None:
            continue

        description = str(score_item.get("description", "")).upper()

        if description in preferred_descriptions:
            return goals

        best_score = goals

    return best_score


def fixture_to_old_shape(fixture):
    home, away = get_participants(fixture)

    if not home or not away:
        return None

    league = fixture.get("league") or {}
    state_short = get_state_short(fixture)
    scores = fixture.get("scores", [])

    home_goals = extract_score_for_participant(scores, home.get("id"))
    away_goals = extract_score_for_participant(scores, away.get("id"))

    local_date = parse_sportmonks_datetime(fixture.get("starting_at"))

    if local_date:
        display_date = local_date.strftime("%Y-%m-%d %H:%M:%S")
    else:
        display_date = fixture.get("starting_at")

    country = "Unknown"

    league_country = league.get("country")
    if isinstance(league_country, dict):
        country = league_country.get("name", "Unknown")

    return {
        "fixture": {
            "id": fixture.get("id"),
            "date": display_date,
            "status": {
                "short": state_short
            }
        },
        "league": {
            "id": league.get("id"),
            "name": league.get("name", "Unknown League"),
            "country": country
        },
        "teams": {
            "home": {
                "id": home.get("id"),
                "name": home.get("name"),
                "winner": None
            },
            "away": {
                "id": away.get("id"),
                "name": away.get("name"),
                "winner": None
            }
        },
        "goals": {
            "home": home_goals,
            "away": away_goals
        },
        "_raw": fixture
    }


def teams_match(team_id, team_name, home, away):
    team_name_normalized = normalize_name(team_name)

    home_id = home.get("id")
    away_id = away.get("id")

    home_name = normalize_name(home.get("name"))
    away_name = normalize_name(away.get("name"))

    same_team_by_id = home_id == team_id or away_id == team_id

    same_team_by_name = (
        team_name_normalized in home_name
        or team_name_normalized in away_name
        or home_name in team_name_normalized
        or away_name in team_name_normalized
    )

    return same_team_by_id or same_team_by_name


def search_team(team_name):
    teams = api_get(f"teams/search/{team_name}", {
        "include": "country"
    })

    results = []

    for team in teams:
        country = team.get("country")

        if isinstance(country, dict):
            country_name = country.get("name", "Unknown")
        else:
            country_name = "Unknown"

        results.append({
            "team": {
                "id": team.get("id"),
                "name": team.get("name"),
                "country": country_name
            }
        })

    return results


def get_fixtures_by_date(date_value):
    fixtures = api_get(f"fixtures/date/{date_value}", {
        "include": "participants;league.country;state;scores"
    })

    converted = []

    for fixture in fixtures:
        old_shape = fixture_to_old_shape(fixture)

        if old_shape:
            converted.append(old_shape)

    return converted


def get_fixture_details(fixture_id):
    if fixture_id in FIXTURE_DETAILS_CACHE:
        return FIXTURE_DETAILS_CACHE[fixture_id]

    data = api_get(f"fixtures/{fixture_id}", {
        "include": (
            "participants;"
            "league.country;"
            "state;"
            "scores;"
            "lineups.player;"
            "lineups.type;"
            "lineups.position;"
            "events.type;"
            "events.player;"
            "sidelined.player;"
            "sidelined.sideline;"
            "sidelined.type"
        )
    })

    if isinstance(data, list):
        if not data:
            return None
        fixture = data[0]
    else:
        fixture = data

    FIXTURE_DETAILS_CACHE[fixture_id] = fixture
    return fixture


def get_next_match(team_id, team_name, days_ahead=3):
    now = datetime.now(ZoneInfo(TIMEZONE))
    end_date = now + timedelta(days=days_ahead)

    all_fixtures = []
    current_date = now.date()

    while current_date <= end_date.date():
        date_str = current_date.strftime("%Y-%m-%d")
        fixtures = get_fixtures_by_date(date_str)

        print(f"Fixtures found on {date_str}: {len(fixtures)}")

        all_fixtures.extend(fixtures)
        current_date += timedelta(days=1)

        time.sleep(0.5)

    matching_fixtures = []

    for match in all_fixtures:
        status = match["fixture"]["status"]["short"]
        match_date = parse_sportmonks_datetime(match["fixture"]["date"])

        if not match_date:
            continue

        if match_date < now:
            continue

        home = match["teams"]["home"]
        away = match["teams"]["away"]

        is_upcoming = status in UPCOMING_STATES or status == ""

        if not is_upcoming:
            continue

        if teams_match(team_id, team_name, home, away):
            matching_fixtures.append(match)

    if not matching_fixtures:
        print("\nNo matching upcoming fixtures found for this team.")
        print("Showing first 40 fixtures found for debugging:\n")

        for match in all_fixtures[:40]:
            print(
                match["league"]["name"],
                "-",
                match["teams"]["home"]["name"],
                "vs",
                match["teams"]["away"]["name"],
                "-",
                match["fixture"]["date"],
                "-",
                match["fixture"]["status"]["short"]
            )

        return None

    matching_fixtures.sort(key=lambda m: m["fixture"]["date"])
    return matching_fixtures[0]


def is_match_within_next_3_days(match):
    match_date = parse_sportmonks_datetime(match["fixture"]["date"])

    if not match_date:
        return False

    now = datetime.now(ZoneInfo(TIMEZONE))
    max_date = now + timedelta(days=3)

    return now <= match_date <= max_date


def get_last_matches(team_id, team_name, limit=5, days_back=120):
    now = datetime.now(ZoneInfo(TIMEZONE))
    current_date = now.date()

    finished_matches = []
    seen_fixture_ids = set()

    days_checked = 0

    while days_checked <= days_back and len(finished_matches) < limit:
        date_str = current_date.strftime("%Y-%m-%d")
        fixtures = get_fixtures_by_date(date_str)

        for match in fixtures:
            fixture_id = match["fixture"]["id"]

            if fixture_id in seen_fixture_ids:
                continue

            status = match["fixture"]["status"]["short"]

            if status not in FINISHED_STATES:
                continue

            home = match["teams"]["home"]
            away = match["teams"]["away"]

            home_goals = match["goals"]["home"]
            away_goals = match["goals"]["away"]

            if home_goals is None or away_goals is None:
                continue

            if teams_match(team_id, team_name, home, away):
                finished_matches.append(match)
                seen_fixture_ids.add(fixture_id)

                if len(finished_matches) >= limit:
                    break

        current_date -= timedelta(days=1)
        days_checked += 1

        time.sleep(0.25)

    finished_matches.sort(
        key=lambda m: m["fixture"]["date"],
        reverse=True
    )

    return finished_matches[:limit]


def get_head_to_head(home_id, away_id):
    fixtures = api_get(f"fixtures/head-to-head/{home_id}/{away_id}", {
        "include": "participants;league.country;state;scores"
    })

    converted = []

    for fixture in fixtures:
        old_shape = fixture_to_old_shape(fixture)

        if old_shape:
            converted.append(old_shape)

    return converted


def extract_player_name(player):
    if not isinstance(player, dict):
        return "Unknown Player"

    return (
        player.get("display_name")
        or player.get("common_name")
        or player.get("name")
        or player.get("fullname")
        or "Unknown Player"
    )


def extract_position(player):
    if not isinstance(player, dict):
        return "Unknown"

    position = player.get("position")

    if isinstance(position, dict):
        return position.get("name", "Unknown")

    return (
        player.get("position_name")
        or player.get("detailed_position")
        or player.get("position")
        or "Unknown"
    )


def get_lineup_player_id(lineup_item):
    return (
        lineup_item.get("player_id")
        or safe_get(lineup_item, ["player", "id"])
        or lineup_item.get("participant_id")
    )


def get_lineup_team_id(lineup_item):
    return (
        lineup_item.get("team_id")
        or lineup_item.get("participant_id")
    )


def get_lineup_type(lineup_item):
    type_data = lineup_item.get("type")

    if isinstance(type_data, dict):
        type_name = (
            type_data.get("name")
            or type_data.get("developer_name")
            or type_data.get("code")
            or ""
        ).lower()
    else:
        type_name = str(type_data or "").lower()

    if "bench" in type_name or "substitute" in type_name:
        return "bench"

    if "start" in type_name or "lineup" in type_name:
        return "starter"

    if lineup_item.get("formation_position") is not None:
        return "starter"

    return "appearance"


def get_event_player_id(event):
    return (
        event.get("player_id")
        or safe_get(event, ["player", "id"])
    )


def get_event_team_id(event):
    return (
        event.get("participant_id")
        or event.get("team_id")
    )


def get_event_type(event):
    type_data = event.get("type")

    if isinstance(type_data, dict):
        return (
            type_data.get("name")
            or type_data.get("developer_name")
            or type_data.get("code")
            or ""
        ).lower()

    return str(type_data or "").lower()


def get_sidelined_team_id(item):
    return (
        item.get("participant_id")
        or item.get("team_id")
        or safe_get(item, ["participant", "id"])
        or safe_get(item, ["team", "id"])
    )


def get_sidelined_player_id(item):
    return (
        item.get("player_id")
        or safe_get(item, ["player", "id"])
    )


def get_sidelined_reason(item):
    reason_parts = []

    type_data = item.get("type")
    sideline = item.get("sideline")

    if isinstance(type_data, dict):
        value = (
            type_data.get("name")
            or type_data.get("developer_name")
            or type_data.get("code")
        )

        if value:
            reason_parts.append(str(value))

    if isinstance(sideline, dict):
        value = (
            sideline.get("name")
            or sideline.get("category")
            or sideline.get("type")
            or sideline.get("description")
        )

        if value:
            reason_parts.append(str(value))

    if not reason_parts:
        return "Unavailable / not specified"

    return " - ".join(reason_parts)


def get_sidelined_status(item):
    type_data = item.get("type")

    if isinstance(type_data, dict):
        return (
            type_data.get("name")
            or type_data.get("developer_name")
            or type_data.get("code")
            or "Sidelined"
        )

    return "Sidelined"


def calculate_player_importance(player_id, team_id, recent_matches):
    if not player_id:
        return {
            "score": 0,
            "label": "Unknown",
            "starts": 0,
            "appearances": 0,
            "goals": 0,
            "assists": 0,
            "position": "Unknown"
        }

    starts = 0
    appearances = 0
    goals = 0
    assists = 0
    position = "Unknown"

    for match in recent_matches:
        raw = match.get("_raw")

        if not raw:
            continue

        fixture_id = raw.get("id")

        if not fixture_id:
            continue

        detailed = get_fixture_details(fixture_id)

        if not detailed:
            continue

        lineups = detailed.get("lineups", [])
        events = detailed.get("events", [])

        for lineup_item in lineups:
            lineup_player_id = get_lineup_player_id(lineup_item)
            lineup_team_id = get_lineup_team_id(lineup_item)

            if lineup_player_id != player_id:
                continue

            if lineup_team_id and team_id and lineup_team_id != team_id:
                continue

            appearances += 1

            lineup_type = get_lineup_type(lineup_item)

            if lineup_type == "starter":
                starts += 1

            player = lineup_item.get("player")
            if isinstance(player, dict):
                extracted_position = extract_position(player)

                if extracted_position != "Unknown":
                    position = extracted_position

        for event in events:
            event_player_id = get_event_player_id(event)
            event_team_id = get_event_team_id(event)

            if event_player_id != player_id:
                continue

            if event_team_id and team_id and event_team_id != team_id:
                continue

            event_type = get_event_type(event)

            if "goal" in event_type and "own" not in event_type:
                goals += 1

            if "assist" in event_type:
                assists += 1

        time.sleep(0.15)

    base_score = 0
    base_score += starts * 1.6
    base_score += max(0, appearances - starts) * 0.7
    base_score += goals * 2.0
    base_score += assists * 1.3

    position_normalized = normalize_name(position)
    position_multiplier = 1.0

    if "goalkeeper" in position_normalized:
        position_multiplier = 1.25
    elif "defender" in position_normalized or "centre back" in position_normalized:
        position_multiplier = 1.15
    elif "midfielder" in position_normalized:
        position_multiplier = 1.12
    elif (
        "forward" in position_normalized
        or "attacker" in position_normalized
        or "striker" in position_normalized
    ):
        position_multiplier = 1.18

    final_score = min(10, round(base_score * position_multiplier, 2))

    if final_score >= 7.5:
        label = "Key player"
    elif final_score >= 5:
        label = "Important player"
    elif final_score >= 2.5:
        label = "Rotation player"
    elif final_score > 0:
        label = "Squad player"
    else:
        label = "Low/unknown recent importance"

    return {
        "score": final_score,
        "label": label,
        "starts": starts,
        "appearances": appearances,
        "goals": goals,
        "assists": assists,
        "position": position
    }


def get_injuries(
    fixture_id,
    home_id=None,
    away_id=None,
    home_recent_matches=None,
    away_recent_matches=None
):
    fixture = get_fixture_details(fixture_id)

    if not fixture:
        return []

    sidelined = fixture.get("sidelined", [])

    if not sidelined:
        return []

    injuries = []

    home_recent_matches = home_recent_matches or []
    away_recent_matches = away_recent_matches or []

    for item in sidelined:
        team_id = get_sidelined_team_id(item)
        player_id = get_sidelined_player_id(item)

        player = item.get("player", {})
        player_name = extract_player_name(player)
        player_position = extract_position(player)

        if team_id == home_id:
            recent_matches = home_recent_matches
        elif team_id == away_id:
            recent_matches = away_recent_matches
        else:
            recent_matches = []

        importance = calculate_player_importance(
            player_id=player_id,
            team_id=team_id,
            recent_matches=recent_matches
        )

        if player_position != "Unknown":
            importance["position"] = player_position

        injuries.append({
            "team": {
                "id": team_id
            },
            "player": {
                "id": player_id,
                "name": player_name,
                "position": importance["position"]
            },
            "reason": get_sidelined_reason(item),
            "status": get_sidelined_status(item),
            "importance_score": importance["score"],
            "importance_label": importance["label"],
            "recent_starts": importance["starts"],
            "recent_appearances": importance["appearances"],
            "recent_goals": importance["goals"],
            "recent_assists": importance["assists"]
        })

    return injuries


def get_fixture_odds_from_include(fixture_id, bookmaker_id=BET365_BOOKMAKER_ID):
    data = api_get(f"fixtures/{fixture_id}", {
        "include": "odds.market;odds.bookmaker",
        "filters": f"bookmakers:{bookmaker_id}"
    })

    if isinstance(data, list):
        if not data:
            return []
        fixture = data[0]
    else:
        fixture = data

    odds = fixture.get("odds", [])
    return odds or []


def decimal_to_implied_probability(decimal_odd):
    try:
        odd = float(decimal_odd)

        if odd <= 1:
            return 0

        return round((1 / odd) * 100, 2)

    except (TypeError, ValueError):
        return 0


def clean_probability(value):
    if value is None:
        return None

    try:
        return float(str(value).replace("%", "").strip())
    except ValueError:
        return None


def normalize_market_name(odd):
    market = odd.get("market")

    if isinstance(market, dict):
        return (
            market.get("name")
            or market.get("developer_name")
            or market.get("code")
            or ""
        ).lower()

    return str(
        odd.get("market_description")
        or odd.get("market_name")
        or odd.get("name")
        or ""
    ).lower()


def normalize_odd_label(odd):
    return str(
        odd.get("label")
        or odd.get("name")
        or odd.get("original_label")
        or ""
    ).lower()


def get_odd_decimal_value(odd):
    value = odd.get("value") or odd.get("dp3") or odd.get("decimal")

    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def make_parsed_odd(odd):
    value = get_odd_decimal_value(odd)

    if value is None:
        return None

    api_probability = clean_probability(odd.get("probability"))

    implied = api_probability
    if implied is None:
        implied = decimal_to_implied_probability(value)

    market = odd.get("market") if isinstance(odd.get("market"), dict) else {}
    bookmaker = odd.get("bookmaker") if isinstance(odd.get("bookmaker"), dict) else {}

    return {
        "market_id": odd.get("market_id"),
        "bookmaker_id": odd.get("bookmaker_id"),
        "market": market.get("name") or normalize_market_name(odd),
        "bookmaker": bookmaker.get("name") or "bet365",
        "label": odd.get("label") or odd.get("name") or odd.get("original_label"),
        "total": odd.get("total"),
        "handicap": odd.get("handicap"),
        "value": value,
        "implied_probability": implied,
        "raw": odd
    }


def parse_bet365_odds(odds):
    parsed = {
        "home_win": None,
        "draw": None,
        "away_win": None,
        "over_1_5": None,
        "under_1_5": None,
        "over_2_5": None,
        "under_2_5": None,
        "btts_yes": None,
        "btts_no": None,
        "raw_count": len(odds or [])
    }

    for odd in odds or []:
        market_id = odd.get("market_id")
        market_name = normalize_market_name(odd)
        label = normalize_odd_label(odd)
        total = str(odd.get("total") or odd.get("handicap") or "").strip()

        parsed_odd = make_parsed_odd(odd)

        if not parsed_odd:
            continue

        if market_id == 1 or "fulltime result" in market_name or "full time result" in market_name:
            if label in ["home", "1"]:
                parsed["home_win"] = parsed_odd
            elif label in ["draw", "x"]:
                parsed["draw"] = parsed_odd
            elif label in ["away", "2"]:
                parsed["away_win"] = parsed_odd

        is_goal_total_market = (
            "over" in label
            or "under" in label
            or "over/under" in market_name
            or "total goals" in market_name
            or "goals over/under" in market_name
        )

        if is_goal_total_market:
            if "1.5" in total or "1.5" in label or "1.5" in market_name:
                if "over" in label:
                    parsed["over_1_5"] = parsed_odd
                elif "under" in label:
                    parsed["under_1_5"] = parsed_odd

            if "2.5" in total or "2.5" in label or "2.5" in market_name:
                if "over" in label:
                    parsed["over_2_5"] = parsed_odd
                elif "under" in label:
                    parsed["under_2_5"] = parsed_odd

        is_btts_market = (
            "both teams to score" in market_name
            or "btts" in market_name
        )

        if is_btts_market:
            if label in ["yes", "y"]:
                parsed["btts_yes"] = parsed_odd
            elif label in ["no", "n"]:
                parsed["btts_no"] = parsed_odd

    return parsed


def get_best_available_odds(fixture_id):
    print("Trying Bet365 odds through fixture include...")

    odds = get_fixture_odds_from_include(
        fixture_id,
        bookmaker_id=BET365_BOOKMAKER_ID
    )

    if odds:
        return odds, "Bet365 via fixture include"

    return [], "No Odds"


def debug_print_odds_markets(raw_odds, limit=30):
    if not raw_odds:
        print("No odds to debug.")
        return

    print("\nOdds debug - first markets returned:")

    for odd in raw_odds[:limit]:
        market = odd.get("market") if isinstance(odd.get("market"), dict) else {}
        bookmaker = odd.get("bookmaker") if isinstance(odd.get("bookmaker"), dict) else {}

        print(
            "market_id:",
            odd.get("market_id"),
            "| market:",
            market.get("name"),
            "| bookmaker:",
            bookmaker.get("name"),
            "| label:",
            odd.get("label"),
            "| value:",
            odd.get("value"),
            "| probability:",
            odd.get("probability"),
            "| total:",
            odd.get("total"),
            "| handicap:",
            odd.get("handicap")
        )