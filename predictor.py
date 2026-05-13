def calculate_team_form_score(matches, team_id):
    if not matches:
        return 0

    score = 0

    for match in matches:
        teams = match["teams"]
        goals = match["goals"]

        home_id = teams["home"]["id"]
        away_id = teams["away"]["id"]

        home_goals = goals["home"]
        away_goals = goals["away"]

        if home_goals is None or away_goals is None:
            continue

        if team_id == home_id:
            team_goals = home_goals
            opponent_goals = away_goals
        elif team_id == away_id:
            team_goals = away_goals
            opponent_goals = home_goals
        else:
            continue

        if team_goals > opponent_goals:
            score += 3
        elif team_goals == opponent_goals:
            score += 1

        score += team_goals * 0.35
        score -= opponent_goals * 0.25

        if team_goals >= 2:
            score += 0.4

        if opponent_goals == 0:
            score += 0.5

    return round(score, 2)


def calculate_goal_stats(matches, team_id):
    if not matches:
        return empty_goal_stats()

    goals_for = 0
    goals_against = 0
    total_goals_sum = 0
    over_1_5_count = 0
    over_2_5_count = 0
    btts_count = 0
    valid_matches = 0

    for match in matches:
        teams = match["teams"]
        goals = match["goals"]

        home_id = teams["home"]["id"]
        away_id = teams["away"]["id"]

        home_goals = goals["home"]
        away_goals = goals["away"]

        if home_goals is None or away_goals is None:
            continue

        if team_id == home_id:
            team_goals = home_goals
            opponent_goals = away_goals
        elif team_id == away_id:
            team_goals = away_goals
            opponent_goals = home_goals
        else:
            continue

        match_total = team_goals + opponent_goals

        goals_for += team_goals
        goals_against += opponent_goals
        total_goals_sum += match_total
        valid_matches += 1

        if match_total >= 2:
            over_1_5_count += 1

        if match_total >= 3:
            over_2_5_count += 1

        if team_goals >= 1 and opponent_goals >= 1:
            btts_count += 1

    if valid_matches == 0:
        return empty_goal_stats()

    return {
        "matches": valid_matches,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "avg_goals_for": round(goals_for / valid_matches, 2),
        "avg_goals_against": round(goals_against / valid_matches, 2),
        "avg_total_goals": round(total_goals_sum / valid_matches, 2),
        "over_1_5_count": over_1_5_count,
        "over_2_5_count": over_2_5_count,
        "btts_count": btts_count,
        "over_1_5_rate": round((over_1_5_count / valid_matches) * 100, 1),
        "over_2_5_rate": round((over_2_5_count / valid_matches) * 100, 1),
        "btts_rate": round((btts_count / valid_matches) * 100, 1),
    }


def empty_goal_stats():
    return {
        "matches": 0,
        "goals_for": 0,
        "goals_against": 0,
        "avg_goals_for": 0,
        "avg_goals_against": 0,
        "avg_total_goals": 0,
        "over_1_5_count": 0,
        "over_2_5_count": 0,
        "btts_count": 0,
        "over_1_5_rate": 0,
        "over_2_5_rate": 0,
        "btts_rate": 0,
    }


def calculate_goal_prediction(home_matches, away_matches, home_id, away_id):
    home_stats = calculate_goal_stats(home_matches, home_id)
    away_stats = calculate_goal_stats(away_matches, away_id)

    if home_stats["matches"] == 0 or away_stats["matches"] == 0:
        return {
            "home_stats": home_stats,
            "away_stats": away_stats,
            "expected_home_goals": 0,
            "expected_away_goals": 0,
            "expected_total_goals": 0,
            "over_1_5_pick": "No bet / not enough data",
            "over_1_5_confidence": 0,
            "over_2_5_pick": "No bet / not enough data",
            "over_2_5_confidence": 0,
            "btts_pick": "No bet / not enough data",
            "btts_confidence": 0,
            "correct_score_idea": "Not enough data",
        }

    expected_home_goals = (
        home_stats["avg_goals_for"] * 0.60
        + away_stats["avg_goals_against"] * 0.40
    )

    expected_away_goals = (
        away_stats["avg_goals_for"] * 0.60
        + home_stats["avg_goals_against"] * 0.40
    )

    expected_home_goals += 0.15

    expected_home_goals = round(expected_home_goals, 2)
    expected_away_goals = round(expected_away_goals, 2)
    expected_total_goals = round(expected_home_goals + expected_away_goals, 2)

    combined_over_1_5_rate = (
        home_stats["over_1_5_rate"] + away_stats["over_1_5_rate"]
    ) / 2

    combined_over_2_5_rate = (
        home_stats["over_2_5_rate"] + away_stats["over_2_5_rate"]
    ) / 2

    combined_btts_rate = (
        home_stats["btts_rate"] + away_stats["btts_rate"]
    ) / 2

    if expected_total_goals >= 1.75 and combined_over_1_5_rate >= 60:
        over_1_5_pick = "Over 1.5 goals"
        over_1_5_confidence = min(85, 55 + (expected_total_goals - 1.5) * 15)
    elif expected_total_goals < 1.6 and combined_over_1_5_rate < 55:
        over_1_5_pick = "Under 1.5 goals"
        over_1_5_confidence = min(75, 55 + (1.6 - expected_total_goals) * 15)
    else:
        over_1_5_pick = "Over 1.5 is possible but not strong"
        over_1_5_confidence = 52

    if expected_total_goals >= 2.75 and combined_over_2_5_rate >= 55:
        over_2_5_pick = "Over 2.5 goals"
        over_2_5_confidence = min(82, 52 + (expected_total_goals - 2.5) * 13)
    elif expected_total_goals < 2.35 and combined_over_2_5_rate < 50:
        over_2_5_pick = "Under 2.5 goals"
        over_2_5_confidence = min(80, 52 + (2.5 - expected_total_goals) * 12)
    else:
        over_2_5_pick = "Over/Under 2.5 is risky"
        over_2_5_confidence = 50

    if (
        expected_home_goals >= 0.9
        and expected_away_goals >= 0.9
        and combined_btts_rate >= 50
    ):
        btts_pick = "BTTS Yes"
        btts_confidence = min(80, 52 + combined_btts_rate * 0.25)
    elif expected_home_goals < 0.8 or expected_away_goals < 0.8:
        btts_pick = "BTTS No"
        btts_confidence = 60
    else:
        btts_pick = "BTTS is risky"
        btts_confidence = 50

    correct_home_goals = round(expected_home_goals)
    correct_away_goals = round(expected_away_goals)
    correct_score_idea = f"{correct_home_goals}-{correct_away_goals}"

    return {
        "home_stats": home_stats,
        "away_stats": away_stats,
        "expected_home_goals": expected_home_goals,
        "expected_away_goals": expected_away_goals,
        "expected_total_goals": expected_total_goals,
        "over_1_5_pick": over_1_5_pick,
        "over_1_5_confidence": round(over_1_5_confidence, 1),
        "over_2_5_pick": over_2_5_pick,
        "over_2_5_confidence": round(over_2_5_confidence, 1),
        "btts_pick": btts_pick,
        "btts_confidence": round(btts_confidence, 1),
        "correct_score_idea": correct_score_idea,
    }


def calculate_h2h_score(h2h_matches, home_id, away_id):
    home_score = 0
    away_score = 0

    for match in h2h_matches[:5]:
        goals = match.get("goals", {})
        teams = match.get("teams", {})

        hg = goals.get("home")
        ag = goals.get("away")

        if hg is None or ag is None:
            continue

        match_home_id = teams.get("home", {}).get("id")
        match_away_id = teams.get("away", {}).get("id")

        if match_home_id == home_id:
            home_goals = hg
            away_goals = ag
        elif match_away_id == home_id:
            home_goals = ag
            away_goals = hg
        else:
            continue

        if home_goals > away_goals:
            home_score += 0.5
        elif home_goals < away_goals:
            away_score += 0.5
        else:
            home_score += 0.15
            away_score += 0.15

    return round(home_score, 2), round(away_score, 2)


def confidence_from_difference(difference, data_quality):
    base = 52 + abs(difference) * 7
    base *= data_quality

    return max(45, min(82, round(base, 1)))


def implied_probability(decimal_odd):
    if not decimal_odd:
        return 0

    try:
        odd = float(decimal_odd)

        if odd <= 1:
            return 0

        return round((1 / odd) * 100, 2)

    except (TypeError, ValueError):
        return 0


def calculate_value_edge(model_probability, decimal_odd):
    bookmaker_probability = implied_probability(decimal_odd)

    if bookmaker_probability == 0:
        return 0

    return round(model_probability - bookmaker_probability, 2)


def add_value_pick(value_picks, market, selection, model_probability, odd_data, reason):
    if not odd_data:
        return

    decimal_odd = odd_data.get("value")
    bookmaker_probability = implied_probability(decimal_odd)
    edge = calculate_value_edge(model_probability, decimal_odd)

    value_picks.append({
        "market": market,
        "selection": selection,
        "odd": decimal_odd,
        "bookmaker_probability": bookmaker_probability,
        "model_probability": round(model_probability, 2),
        "edge": edge,
        "reason": reason,
    })


def calculate_odds_value_picks(
    home_team,
    away_team,
    prediction,
    confidence,
    goal_prediction,
    bet365_odds,
):
    if not bet365_odds:
        return {
            "available": False,
            "best_pick": None,
            "value_picks": [],
            "message": "No Bet365 odds available.",
        }

    value_picks = []

    home = home_team["name"]
    away = away_team["name"]

    if prediction == f"{home} win":
        add_value_pick(
            value_picks,
            "1X2",
            f"{home} win",
            confidence,
            bet365_odds.get("home_win"),
            "Model match-winner prediction agrees with this selection.",
        )

    elif prediction == f"{away} win":
        add_value_pick(
            value_picks,
            "1X2",
            f"{away} win",
            confidence,
            bet365_odds.get("away_win"),
            "Model match-winner prediction agrees with this selection.",
        )

    else:
        add_value_pick(
            value_picks,
            "1X2",
            "Draw",
            confidence,
            bet365_odds.get("draw"),
            "Model sees the match as close.",
        )

    over_1_5_pick = goal_prediction.get("over_1_5_pick", "")
    over_1_5_confidence = goal_prediction.get("over_1_5_confidence", 0)

    if over_1_5_pick == "Over 1.5 goals":
        add_value_pick(
            value_picks,
            "Goals 1.5",
            "Over 1.5",
            over_1_5_confidence,
            bet365_odds.get("over_1_5"),
            "Goal model expects enough total goals for Over 1.5.",
        )
    elif over_1_5_pick == "Under 1.5 goals":
        add_value_pick(
            value_picks,
            "Goals 1.5",
            "Under 1.5",
            over_1_5_confidence,
            bet365_odds.get("under_1_5"),
            "Goal model expects a low-scoring match.",
        )

    over_2_5_pick = goal_prediction.get("over_2_5_pick", "")
    over_2_5_confidence = goal_prediction.get("over_2_5_confidence", 0)

    if over_2_5_pick == "Over 2.5 goals":
        add_value_pick(
            value_picks,
            "Goals 2.5",
            "Over 2.5",
            over_2_5_confidence,
            bet365_odds.get("over_2_5"),
            "Goal model expects the total to clear 2.5.",
        )
    elif over_2_5_pick == "Under 2.5 goals":
        add_value_pick(
            value_picks,
            "Goals 2.5",
            "Under 2.5",
            over_2_5_confidence,
            bet365_odds.get("under_2_5"),
            "Goal model expects the total to stay below 2.5.",
        )

    btts_pick = goal_prediction.get("btts_pick", "")
    btts_confidence = goal_prediction.get("btts_confidence", 0)

    if btts_pick == "BTTS Yes":
        add_value_pick(
            value_picks,
            "BTTS",
            "Yes",
            btts_confidence,
            bet365_odds.get("btts_yes"),
            "Both teams project close to or above 1 expected goal.",
        )
    elif btts_pick == "BTTS No":
        add_value_pick(
            value_picks,
            "BTTS",
            "No",
            btts_confidence,
            bet365_odds.get("btts_no"),
            "At least one team projects below a strong scoring threshold.",
        )

    value_picks.sort(key=lambda item: item["edge"], reverse=True)

    positive_value_picks = [
        pick for pick in value_picks
        if pick["edge"] > 0
    ]

    best_pick = positive_value_picks[0] if positive_value_picks else (
        value_picks[0] if value_picks else None
    )

    return {
        "available": True,
        "best_pick": best_pick,
        "value_picks": value_picks,
        "message": "Bet365 odds compared against model probability.",
    }


def analyze_match(
    home_team,
    away_team,
    home_matches,
    away_matches,
    h2h_matches,
    injuries,
    bet365_odds=None,
):
    home_id = home_team["id"]
    away_id = away_team["id"]

    reasons = []

    home_score = calculate_team_form_score(home_matches, home_id)
    away_score = calculate_team_form_score(away_matches, away_id)

    goal_prediction = calculate_goal_prediction(
        home_matches,
        away_matches,
        home_id,
        away_id,
    )

    home_h2h_score, away_h2h_score = calculate_h2h_score(
        h2h_matches,
        home_id,
        away_id,
    )

    home_score += home_h2h_score
    away_score += away_h2h_score

    has_form_data = len(home_matches) > 0 or len(away_matches) > 0

    if len(home_matches) == 0:
        reasons.append(f"No recent completed matches found for {home_team['name']}.")

    if len(away_matches) == 0:
        reasons.append(f"No recent completed matches found for {away_team['name']}.")

    if has_form_data:
        home_score += 1.0
        reasons.append("Home advantage added to the home team's rating.")

    if home_h2h_score > away_h2h_score:
        reasons.append(f"{home_team['name']} has the better recent head-to-head trend.")
    elif away_h2h_score > home_h2h_score:
        reasons.append(f"{away_team['name']} has the better recent head-to-head trend.")

    home_injuries = 0
    away_injuries = 0

    home_injury_impact = 0
    away_injury_impact = 0

    home_key_absences = []
    away_key_absences = []

    for injury in injuries:
        team_id = injury.get("team", {}).get("id")
        importance_score = injury.get("importance_score", 0)

        impact = importance_score * 0.18

        player_name = injury.get("player", {}).get("name", "Unknown Player")
        player_position = injury.get("player", {}).get("position", "Unknown")
        importance_label = injury.get("importance_label", "Unknown")
        reason = injury.get("reason", "Unavailable")

        absence_text = (
            f"{player_name} ({player_position}) - "
            f"{importance_label}, importance {importance_score}/10, reason: {reason}"
        )

        if team_id == home_id:
            home_injuries += 1
            home_injury_impact += impact

            if importance_score >= 5:
                home_key_absences.append(absence_text)

        elif team_id == away_id:
            away_injuries += 1
            away_injury_impact += impact

            if importance_score >= 5:
                away_key_absences.append(absence_text)

    if has_form_data:
        home_score -= home_injury_impact
        away_score -= away_injury_impact
    else:
        home_score -= home_injury_impact * 0.35
        away_score -= away_injury_impact * 0.35

        if injuries:
            reasons.append(
                "Injury impact was reduced because recent form data is missing."
            )

    if home_injury_impact > away_injury_impact:
        reasons.append(
            f"{home_team['name']} has the higher injury impact "
            f"({round(home_injury_impact, 2)} rating penalty)."
        )
    elif away_injury_impact > home_injury_impact:
        reasons.append(
            f"{away_team['name']} has the higher injury impact "
            f"({round(away_injury_impact, 2)} rating penalty)."
        )

    if home_key_absences:
        reasons.append(
            f"Key absences for {home_team['name']}: "
            + "; ".join(home_key_absences[:3])
        )

    if away_key_absences:
        reasons.append(
            f"Key absences for {away_team['name']}: "
            + "; ".join(away_key_absences[:3])
        )

    if goal_prediction["expected_total_goals"] > 0:
        reasons.append(
            f"Goal model expects around {goal_prediction['expected_total_goals']} total goals."
        )

        reasons.append(
            f"Main goals pick: {goal_prediction['over_2_5_pick']} "
            f"({goal_prediction['over_2_5_confidence']}% confidence)."
        )

    if home_score > away_score:
        reasons.append(f"{home_team['name']} has the stronger calculated rating.")
    elif away_score > home_score:
        reasons.append(f"{away_team['name']} has the stronger calculated rating.")
    else:
        reasons.append("Both teams have very similar calculated ratings.")

    if len(home_matches) < 5 or len(away_matches) < 5:
        reasons.append(
            "Prediction confidence reduced because fewer than 5 recent completed matches were found."
        )

    difference = home_score - away_score

    available_match_count = len(home_matches) + len(away_matches)
    data_quality = min(1.0, available_match_count / 10)

    if available_match_count == 0:
        data_quality = 0.55
    elif available_match_count < 6:
        data_quality = 0.75

    if difference >= 1.0:
        prediction = f"{home_team['name']} win"
        confidence = confidence_from_difference(difference, data_quality)
    elif difference <= -1.0:
        prediction = f"{away_team['name']} win"
        confidence = confidence_from_difference(difference, data_quality)
    else:
        prediction = "Draw or very close match"
        confidence = max(45, min(58, 50 + abs(difference) * 3))

    odds_analysis = calculate_odds_value_picks(
        home_team=home_team,
        away_team=away_team,
        prediction=prediction,
        confidence=confidence,
        goal_prediction=goal_prediction,
        bet365_odds=bet365_odds or {},
    )

    return {
        "prediction": prediction,
        "confidence": round(confidence, 1),
        "home_score": round(home_score, 2),
        "away_score": round(away_score, 2),
        "home_matches_count": len(home_matches),
        "away_matches_count": len(away_matches),
        "home_injuries": home_injuries,
        "away_injuries": away_injuries,
        "home_injury_impact": round(home_injury_impact, 2),
        "away_injury_impact": round(away_injury_impact, 2),
        "home_key_absences": home_key_absences,
        "away_key_absences": away_key_absences,
        "goal_prediction": goal_prediction,
        "odds_analysis": odds_analysis,
        "injuries": injuries,
        "reasons": reasons,
    }