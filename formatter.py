from colorama import Fore, Style


def format_injury_list(team_name, injuries, team_id):
    team_injuries = [
        injury for injury in injuries
        if injury.get("team", {}).get("id") == team_id
    ]

    if not team_injuries:
        return f"{Fore.GREEN}[+]{Style.RESET_ALL} {Fore.CYAN}{team_name}{Style.RESET_ALL}: no sidelined players"

    lines = [
        f"{Fore.RED}[-]{Style.RESET_ALL} {Fore.CYAN}{team_name}{Style.RESET_ALL}: {Fore.YELLOW}{len(team_injuries)} sidelined{Style.RESET_ALL}"
    ]

    sorted_injuries = sorted(
        team_injuries,
        key=lambda item: item.get("importance_score", 0),
        reverse=True
    )

    for injury in sorted_injuries[:8]:
        player = injury.get("player", {})
        name = player.get("name", "Unknown Player")
        position = player.get("position", "Unknown")
        reason = injury.get("reason", "Unavailable")
        importance_score = injury.get("importance_score", 0)
        importance_label = injury.get("importance_label", "Unknown")
        starts = injury.get("recent_starts", 0)
        appearances = injury.get("recent_appearances", 0)
        goals = injury.get("recent_goals", 0)
        assists = injury.get("recent_assists", 0)

        lines.append(
            f"    {Fore.MAGENTA}[*]{Style.RESET_ALL} {Fore.LIGHTCYAN_EX}{name}{Style.RESET_ALL} "
            f"{Fore.WHITE}({position}){Style.RESET_ALL} | "
            f"{Fore.YELLOW}{importance_label}{Style.RESET_ALL} {importance_score}/10 | "
            f"{Fore.LIGHTWHITE_EX}{starts} Starts {appearances} Appearances {goals} Goals {assists} Assists{Style.RESET_ALL} | {reason}"
        )

    return "\n".join(lines)


def format_goal_stats(team_name, stats):
    return (
        f"  {Fore.GREEN}[+]{Style.RESET_ALL} {Fore.LIGHTCYAN_EX}{team_name}{Style.RESET_ALL}: "
        f"{Fore.YELLOW}{stats['avg_goals_for']:.2f}↑{Style.RESET_ALL} "
        f"{Fore.RED}{stats['avg_goals_against']:.2f}↓{Style.RESET_ALL} | "
        f"O1.5: {Fore.LIGHTGREEN_EX}{stats['over_1_5_rate']}%{Style.RESET_ALL} | "
        f"O2.5: {Fore.LIGHTGREEN_EX}{stats['over_2_5_rate']}%{Style.RESET_ALL} | "
        f"BTTS: {Fore.LIGHTBLUE_EX}{stats['btts_rate']}%{Style.RESET_ALL}"
    )


def format_odds_analysis(analysis):
    odds_analysis = analysis.get("odds_analysis", {})

    if not odds_analysis or not odds_analysis.get("available"):
        return f"{Fore.YELLOW}[-]{Style.RESET_ALL} Bet365 odds: not available"

    best_pick = odds_analysis.get("best_pick")
    value_picks = odds_analysis.get("value_picks", [])

    if not best_pick and not value_picks:
        return f"{Fore.YELLOW}[-]{Style.RESET_ALL} Bet365 odds: available, but no usable markets parsed."

    lines = [f"{Fore.LIGHTGREEN_EX}[*] Bet365 Value Analysis:{Style.RESET_ALL}"]

    if best_pick:
        edge_label = f"{Fore.GREEN}VALUE" if best_pick["edge"] > 0 else f"{Fore.RED}NO VALUE"
        edge_label += Style.RESET_ALL

        lines.append(
            f"  {Fore.GREEN}[+]{Style.RESET_ALL} {best_pick['selection']} "
            f"{Fore.LIGHTWHITE_EX}@ {best_pick['odd']}{Style.RESET_ALL} | "
            f"{best_pick['market']} | "
            f"Model: {Fore.CYAN}{best_pick['model_probability']}%{Style.RESET_ALL} vs "
            f"Implied: {Fore.CYAN}{best_pick['bookmaker_probability']}%{Style.RESET_ALL} | "
            f"Edge: {edge_label}"
        )

    lines.append(f"{Fore.LIGHTBLUE_EX}[*] Other Picks:{Style.RESET_ALL}")

    for pick in value_picks[:6]:
        edge_marker = f"{Fore.GREEN}[+]" if pick["edge"] > 0 else f"{Fore.RED}[-]"
        edge_marker += Style.RESET_ALL

        lines.append(
            f"  {edge_marker} {pick['market']} - {pick['selection']} "
            f"{Fore.LIGHTWHITE_EX}@ {pick['odd']}{Style.RESET_ALL} | "
            f"Model {Fore.CYAN}{pick['model_probability']}%{Style.RESET_ALL} vs "
            f"{Fore.CYAN}{pick['bookmaker_probability']}%{Style.RESET_ALL} | "
            f"Edge {pick['edge']}%"
        )

    return "\n".join(lines)


def format_prediction(match, analysis):
    home = match["teams"]["home"]["name"]
    away = match["teams"]["away"]["name"]

    home_id = match["teams"]["home"]["id"]
    away_id = match["teams"]["away"]["id"]

    league = match["league"]["name"]
    country = match["league"]["country"]
    fixture_time = match["fixture"]["date"]

    goal_prediction = analysis.get("goal_prediction", {})
    home_goal_stats = goal_prediction.get("home_stats", {})
    away_goal_stats = goal_prediction.get("away_stats", {})

    reasons_text = "\n".join(
        [f"  {Fore.YELLOW}[+]{Style.RESET_ALL} {reason}" for reason in analysis["reasons"]]
    )

    home_injury_text = format_injury_list(
        home,
        analysis.get("injuries", []),
        home_id
    )

    away_injury_text = format_injury_list(
        away,
        analysis.get("injuries", []),
        away_id
    )

    odds_text = format_odds_analysis(analysis)

    goal_stats_text = ""

    if home_goal_stats and away_goal_stats:
        goal_stats_text = f"""
{Fore.LIGHTBLUE_EX}[*] STATS FROM LAST 5 MATCHES:{Style.RESET_ALL}
{format_goal_stats(home, home_goal_stats)}
{format_goal_stats(away, away_goal_stats)}

{Fore.LIGHTBLUE_EX}[*] EXPECTED GOALS:{Style.RESET_ALL}
  {Fore.CYAN}[+] {home}{Style.RESET_ALL}: {Fore.YELLOW}{goal_prediction.get("expected_home_goals", 0)}{Style.RESET_ALL}
  {Fore.RED}[-] {away}{Style.RESET_ALL}: {Fore.YELLOW}{goal_prediction.get("expected_away_goals", 0)}{Style.RESET_ALL}
  {Fore.LIGHTGREEN_EX}[*] Total{Style.RESET_ALL}: {Fore.YELLOW}{goal_prediction.get("expected_total_goals", 0)}{Style.RESET_ALL}
  {Fore.LIGHTBLUE_EX}[*] Correct Score{Style.RESET_ALL}: {goal_prediction.get("correct_score_idea", "N/A")}

{Fore.LIGHTBLUE_EX}[*] OVER/UNDER MARKETS:{Style.RESET_ALL}
  {Fore.YELLOW}[+] O1.5{Style.RESET_ALL}: {goal_prediction.get("over_1_5_pick", "N/A")} ({goal_prediction.get("over_1_5_confidence", 0)}%)
  {Fore.YELLOW}[+] O2.5{Style.RESET_ALL}: {goal_prediction.get("over_2_5_pick", "N/A")} ({goal_prediction.get("over_2_5_confidence", 0)}%)
  {Fore.YELLOW}[+] BTTS{Style.RESET_ALL}: {goal_prediction.get("btts_pick", "N/A")} ({goal_prediction.get("btts_confidence", 0)}%)
"""

    return f"""
{Fore.LIGHTBLUE_EX}{'═' * 70}{Style.RESET_ALL}
{Fore.LIGHTGREEN_EX}[*]  MATCH{Style.RESET_ALL}
{Fore.CYAN}{home:<35}{Style.RESET_ALL} {Fore.LIGHTMAGENTA_EX}VS{Style.RESET_ALL} {Fore.RED}{away:>33}{Style.RESET_ALL}
{Fore.LIGHTBLUE_EX}{'═' * 70}{Style.RESET_ALL}

{Fore.LIGHTBLUE_EX}[*] {league} - {country}{Style.RESET_ALL}
{Fore.LIGHTYELLOW_EX}[*] Kickoff: {fixture_time}{Style.RESET_ALL}

{Fore.LIGHTBLUE_EX}{'═' * 70}{Style.RESET_ALL}
{Fore.LIGHTGREEN_EX}[*] PREDICTION & CONFIDENCE{Style.RESET_ALL}
{Fore.LIGHTBLUE_EX}{'═' * 70}{Style.RESET_ALL}
{Fore.RED}[+] Prediction{Style.RESET_ALL}: {Fore.LIGHTRED_EX}{analysis["prediction"]}{Style.RESET_ALL}
{Fore.LIGHTGREEN_EX}[+] Confidence{Style.RESET_ALL}: {Fore.YELLOW}{analysis["confidence"]}%{Style.RESET_ALL}

{Fore.LIGHTBLUE_EX}[*] TEAM RATINGS:{Style.RESET_ALL}
  {Fore.CYAN}[+] {home}{Style.RESET_ALL}: {Fore.YELLOW}{analysis["home_score"]}{Style.RESET_ALL} ({analysis["home_matches_count"]} matches)
  {Fore.RED}[-] {away}{Style.RESET_ALL}: {Fore.YELLOW}{analysis["away_score"]}{Style.RESET_ALL} ({analysis["away_matches_count"]} matches)

{goal_stats_text}
{Fore.LIGHTBLUE_EX}[*] BETTING ODDS:{Style.RESET_ALL}
{odds_text}

{Fore.LIGHTBLUE_EX}[*] INJURY STATUS:{Style.RESET_ALL}
  {Fore.CYAN}[+] {home}{Style.RESET_ALL}: {Fore.YELLOW}{analysis["home_injuries"]}{Style.RESET_ALL} sidelined (penalty: {analysis["home_injury_impact"]})
  {Fore.RED}[-] {away}{Style.RESET_ALL}: {Fore.YELLOW}{analysis["away_injuries"]}{Style.RESET_ALL} sidelined (penalty: {analysis["away_injury_impact"]})

{Fore.LIGHTBLUE_EX}[*] SIDELINED PLAYERS:{Style.RESET_ALL}
{home_injury_text}
{away_injury_text}

{Fore.LIGHTBLUE_EX}[*] PREDICTION RATIONALE:{Style.RESET_ALL}
{reasons_text}


{Fore.LIGHTYELLOW_EX}[*]  Probability-based prediction, not guaranteed{Style.RESET_ALL}

"""