from football_api import (
    search_team,
    get_next_match,
    is_match_within_next_3_days,
    get_last_matches,
    get_head_to_head,
    get_injuries,
    get_best_available_odds,
    parse_bet365_odds,
    debug_print_odds_markets
)
from predictor import analyze_match
from formatter import format_prediction
from colorama import Fore, Style, init


init(autoreset=True)

DEBUG_ODDS = False


def section(title):
    print()
    print(f"{Fore.LIGHTBLUE_EX}{title.upper()}{Style.RESET_ALL}")
    print(f"{Fore.LIGHTBLACK_EX}{'-' * len(title)}{Style.RESET_ALL}")


def status_ok(message):
    print(f"{Fore.GREEN}[+]{Style.RESET_ALL} {message}")


def status_info(message):
    print(f"{Fore.LIGHTBLUE_EX}[*]{Style.RESET_ALL} {message}")


def status_warn(message):
    print(f"{Fore.YELLOW}[!]{Style.RESET_ALL} {message}")


def status_error(message):
    print(f"{Fore.RED}[-]{Style.RESET_ALL} {message}")


def banner():
    print()
    print(f"{Fore.LIGHTBLUE_EX}FOOTBALL MATCH PREDICTION BOT{Style.RESET_ALL}")
    print(f"{Fore.LIGHTBLACK_EX}Form • Injuries • Goals • H2H • Bet365 Value Analysis{Style.RESET_ALL}")
    print()


def choose_team(team_results):
    if not team_results:
        return None

    section("Teams found")

    for index, item in enumerate(team_results[:10], start=1):
        team = item["team"]
        country = team.get("country", "Unknown")

        print(
            f"{Fore.LIGHTGREEN_EX}{index:>2}.{Style.RESET_ALL} "
            f"{Fore.CYAN}{team['name']:<34}{Style.RESET_ALL} "
            f"{Fore.YELLOW}{country}{Style.RESET_ALL}"
        )

    while True:
        choice = input(
            f"\n{Fore.LIGHTBLUE_EX}Choose team number:{Style.RESET_ALL} "
        ).strip()

        if choice.isdigit():
            choice = int(choice)

            if 1 <= choice <= min(10, len(team_results)):
                return team_results[choice - 1]["team"]

        status_error("Invalid choice. Try again.")


def print_matches_used(team_name, matches):
    section(f"Last 5 matches used: {team_name}")

    if not matches:
        status_error("No completed matches found.")
        return

    for match in matches:
        home = match["teams"]["home"]["name"]
        away = match["teams"]["away"]["name"]
        hg = match["goals"]["home"]
        ag = match["goals"]["away"]
        date = match["fixture"]["date"][:10]
        league = match["league"]["name"]

        print(
            f"{Fore.LIGHTBLACK_EX}{date}{Style.RESET_ALL} | "
            f"{Fore.BLUE}{league:<28}{Style.RESET_ALL} | "
            f"{Fore.CYAN}{home}{Style.RESET_ALL} "
            f"{Fore.WHITE}{hg}-{ag}{Style.RESET_ALL} "
            f"{Fore.MAGENTA}{away}{Style.RESET_ALL}"
        )


def print_match_card(match):
    home = match["teams"]["home"]["name"]
    away = match["teams"]["away"]["name"]
    league = match["league"]["name"]
    country = match["league"]["country"]
    kickoff = match["fixture"]["date"]
    fixture_id = match["fixture"]["id"]

    section("Next match")

    print(
        f"{Fore.CYAN}{home}{Style.RESET_ALL} "
        f"{Fore.YELLOW}vs{Style.RESET_ALL} "
        f"{Fore.MAGENTA}{away}{Style.RESET_ALL}"
    )

    print(f"{Fore.GREEN}Competition:{Style.RESET_ALL} {league} - {country}")
    print(f"{Fore.YELLOW}Kickoff:{Style.RESET_ALL} {kickoff}")
    print(f"{Fore.LIGHTBLACK_EX}Fixture ID:{Style.RESET_ALL} {fixture_id}")


def run_bot():
    banner()

    team_name = input(
        f"{Fore.YELLOW}Enter the team you want to analyze:{Style.RESET_ALL} "
    ).strip()

    if not team_name:
        status_error("You did not enter a team name.")
        return

    section("Team search")
    status_info("Searching Sportmonks for matching teams...")

    team_results = search_team(team_name)
    selected_team = choose_team(team_results)

    if selected_team is None:
        status_error("No team found with that name.")
        return

    team_id = selected_team["id"]
    team_name = selected_team["name"]

    status_ok(f"Selected team: {Fore.LIGHTGREEN_EX}{team_name}{Style.RESET_ALL}")

    section("Match lookup")
    status_info("Looking for the next match in the next 3 days...")

    match = get_next_match(team_id, team_name)

    if match is None:
        status_error(f"No upcoming match found for {team_name}.")
        return

    if not is_match_within_next_3_days(match):
        next_match_date = match["fixture"]["date"]
        status_warn(f"{team_name}'s next match is not in the next 3 days.")
        status_warn(f"Next match date: {next_match_date}")
        return

    print_match_card(match)

    fixture_id = match["fixture"]["id"]

    home_team = match["teams"]["home"]
    away_team = match["teams"]["away"]

    home_id = home_team["id"]
    away_id = away_team["id"]

    section("Data collection")

    status_info("Fetching last 5 completed matches for both teams...")

    home_last_matches = get_last_matches(home_id, home_team["name"], limit=5)
    away_last_matches = get_last_matches(away_id, away_team["name"], limit=5)

    status_ok(
        f"{Fore.CYAN}{home_team['name']}{Style.RESET_ALL} completed matches found: "
        f"{Fore.LIGHTGREEN_EX}{len(home_last_matches)}{Style.RESET_ALL}"
    )

    status_ok(
        f"{Fore.MAGENTA}{away_team['name']}{Style.RESET_ALL} completed matches found: "
        f"{Fore.LIGHTGREEN_EX}{len(away_last_matches)}{Style.RESET_ALL}"
    )

    print_matches_used(home_team["name"], home_last_matches)
    print_matches_used(away_team["name"], away_last_matches)

    section("Advanced data")

    status_info("Fetching head-to-head data...")
    h2h_matches = get_head_to_head(home_id, away_id)
    status_ok(f"Head-to-head records found: {Fore.LIGHTGREEN_EX}{len(h2h_matches)}{Style.RESET_ALL}")

    status_info("Fetching sidelined/injury data...")
    injuries = get_injuries(
        fixture_id,
        home_id=home_id,
        away_id=away_id,
        home_recent_matches=home_last_matches,
        away_recent_matches=away_last_matches
    )

    status_ok(f"Injury records found: {Fore.LIGHTGREEN_EX}{len(injuries)}{Style.RESET_ALL}")

    status_info("Fetching Bet365 odds...")
    raw_odds, odds_source = get_best_available_odds(fixture_id)
    bet365_odds = parse_bet365_odds(raw_odds)

    status_ok(f"Odds source: {Fore.LIGHTGREEN_EX}{odds_source}{Style.RESET_ALL}")
    status_ok(f"Odds records found: {Fore.LIGHTGREEN_EX}{len(raw_odds)}{Style.RESET_ALL}")

    if DEBUG_ODDS:
        debug_print_odds_markets(raw_odds, limit=40)

    section("Analysis result")

    analysis = analyze_match(
        home_team,
        away_team,
        home_last_matches,
        away_last_matches,
        h2h_matches,
        injuries,
        bet365_odds
    )

    message = format_prediction(match, analysis)
    print(message)


if __name__ == "__main__":
    run_bot()