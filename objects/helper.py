"""Create helper file."""
from nba_api.stats.static import teams, players
import pandas as pd
import datetime
from bs4 import BeautifulSoup
import requests

team_id_to_abb = pd.DataFrame(teams.get_teams()).rename(
    columns={"full_name": "TEAM_NAME",
             "id": "TEAM_ID", "abbreviation": "TEAM_ABB"}
)
nba_team_ids = team_id_to_abb.TEAM_ID


def team_abb_to_id(team_abb):
    """Translate team abbreviation to id."""
    try:
        return (
            team_id_to_abb.query(
                "TEAM_ABB == @team_abb").reset_index(drop=1).TEAM_ID[0]
        )
    except KeyError:
        raise KeyError(
            f"User has input non-valid team abbreviation: {team_abb}")


def team_id_to_abb_conv(team_id):
    """Translate team id to abb."""
    try:
        return (
            team_id_to_abb.query(
                "TEAM_ID == @team_id").reset_index(drop=1).TEAM_ABB[0]
        )
    except KeyError:
        raise KeyError(f"User has input non-valid team id: {team_id}")


def scrape_current_nba_injuries(games_ahead_of_now):
    """Scrape injuries."""
    player_ids = pd.DataFrame(
        players.get_active_players())[["id", "full_name"]].rename(
        columns={"full_name": "PLAYER_NAME", "id": "PLAYER_ID"}
    )
    url = "https://www.cbssports.com/nba/injuries/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # find the table containing injury data
    table = soup.find("div", class_="Page-colMain")

    # extract the injury data
    data = []
    for tr in table.find_all("tr"):
        row = []
        for td in tr.find_all("td"):
            try:
                row.append(td.find("span",
                                   class_="CellPlayerName--long").text.strip())
            except AttributeError:
                row.append(td.text.strip())
        data.append(row)
    data = [row for row in data if row != []]

    # create a Pandas dataframe from the injury data and return it
    df = pd.DataFrame(
        data,
        columns=["PLAYER_NAME",
                 "POSITION", "UPDATED", "TYPE", "EXPECTED_WHEN_BACK"],
    )

    # clean
    df["EXPECTED_WHEN_BACK"] = [
        datetime.datetime.strptime(
            when_back.replace("Expected to be out until at least ", "")
            + str(f" {datetime.datetime.now().year}"),
            "%b %d %Y",
        )
        if (when_back != "Game Time Decision")
        and (when_back != "Out for the season")
        else datetime.datetime.now() + datetime.timedelta(days=365)
        if (when_back == "Out for the season")
        else datetime.datetime.now() + datetime.timedelta(days=2)
        for when_back in df.EXPECTED_WHEN_BACK
    ]
    ret = df.merge(player_ids, on="PLAYER_NAME", how="left")
    gametime_date = datetime.datetime.now() + datetime.timedelta(
        days=(games_ahead_of_now * 2)
    )  # assume two days between playoff games on average
    return ret.query("(PLAYER_ID.notna()) & (EXPECTED_WHEN_BACK > @gametime_date)")


def scrape_nba_playoff_projections():
    """Scrape playoff projections."""
    team_ids = pd.DataFrame(teams.get_teams())[["id", "full_name"]].rename(
        columns={"full_name": "TEAM_NAME", "id": "TEAM_ID"}
    )
    url = "https://www.basketball-reference.com/friv/playoff_prob.html"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # find tables
    table_e = soup.find(
        "div", {"class": "table_container", "id": "div_projected_standings_e"}
    )
    table_w = soup.find(
        "div", {"class": "table_container", "id": "div_projected_standings_w"}
    )
    data = []
    for tr in table_e.find_all("tr"):
        row = []
        for td in tr.find_all("td"):
            row.append(td.text.strip())
        data.append(row)
    data = list(
        map(
            lambda row: [
                row[i] if row[i] != "" else 0.0
                for i in [0, 9, 10, 11, 12, 13, 14, 15, 16]
            ],
            [row for row in data if len(row) == 21],
        )
    )
    headers = [
        "TEAM_NAME",
        "1_SEED_PROB",
        "2_SEED_PROB",
        "3_SEED_PROB",
        "4_SEED_PROB",
        "5_SEED_PROB",
        "6_SEED_PROB",
        "7_SEED_PROB",
        "8_SEED_PROB",
    ]
    data_e = pd.DataFrame(data, columns=headers).merge(
        team_ids, on="TEAM_NAME", how="left"
    )
    data = []
    for tr in table_w.find_all("tr"):
        row = []
        for td in tr.find_all("td"):
            row.append(td.text.strip())
        data.append(row)
    data = list(
        map(
            lambda row: [
                row[i] if row[i] != "" else 0.0
                for i in [0, 9, 10, 11, 12, 13, 14, 15, 16]
            ],
            [row for row in data if len(row) == 21],
        )
    )
    data_w = pd.DataFrame(data, columns=headers).merge(
        team_ids, on="TEAM_NAME", how="left"
    )
    return {"West": data_w, "East": data_e}
