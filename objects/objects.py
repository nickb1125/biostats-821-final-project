import nba_api
import pandas as pd
import numpy as np
import time
import datetime
import tqdm
from nba_api.stats.library.parameters import SeasonType, SeasonTypePlayoffs
from nba_api.stats.static import teams, players
from nba_api.stats import endpoints
import math
import requests
from bs4 import BeautifulSoup
import pickle
from random import random, choices
import itertools

team_id_to_abb = pd.DataFrame(teams.get_teams()).rename(
    columns={"full_name": "TEAM_NAME", "id": "TEAM_ID", "abbreviation": "TEAM_ABB"}
)
nba_team_ids = team_id_to_abb.TEAM_ID


def team_abb_to_id(team_abb):
    """Translates team abbreviation to id."""
    try:
        return (
            team_id_to_abb.query("TEAM_ABB == @team_abb").reset_index(drop=1).TEAM_ID[0]
        )
    except KeyError:
        raise KeyError(f"User has input non-valid team abbreviation: {team_abb}")


def team_id_to_abb_conv(team_id):
    """Translates team id to abb."""
    try:
        return (
            team_id_to_abb.query("TEAM_ID == @team_id").reset_index(drop=1).TEAM_ABB[0]
        )
    except KeyError:
        raise KeyError(f"User has input non-valid team id: {team_id}")


def scrape_current_nba_injuries(games_ahead_of_now):
    player_ids = pd.DataFrame(players.get_active_players())[["id", "full_name"]].rename(
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
                row.append(td.find("span", class_="CellPlayerName--long").text.strip())
            except AttributeError:
                row.append(td.text.strip())
        data.append(row)
    data = [row for row in data if row != []]

    # create a Pandas dataframe from the injury data and return it
    df = pd.DataFrame(
        data,
        columns=["PLAYER_NAME", "POSITION", "UPDATED", "TYPE", "EXPECTED_WHEN_BACK"],
    )

    # clean
    df["EXPECTED_WHEN_BACK"] = [
        datetime.datetime.strptime(
            when_back.replace("Expected to be out until at least ", "")
            + str(f" {datetime.datetime.now().year}"),
            "%b %d %Y",
        )
        if (when_back != "Game Time Decision") and (when_back != "Out for the season")
        else datetime.datetime.now() + datetime.timedelta(days=365)
        if (when_back == "Out for the season")
        else datetime.datetime.now() + datetime.timedelta(days=2)
        for when_back in df.EXPECTED_WHEN_BACK
    ]
    ret = df.merge(player_ids, on="PLAYER_NAME", how="left")
    gametime_date = datetime.datetime.now() + datetime.timedelta(
        days=(games_ahead_of_now * 2)
    )  # assume two days between playoff games on average
    return ret.query("EXPECTED_WHEN_BACK > @gametime_date")


def scrape_nba_playoff_projections():
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


class year:
    def __init__(self, year):
        self.year = year
        next_year_abb = str(self.year - 1999)
        if len(next_year_abb) == 1:
            next_year_abb = "0" + next_year_abb
        self.season = str(self.year) + "-" + next_year_abb
        self.game_data_cache = pd.DataFrame()
        self.playoff_game_data_cache = pd.DataFrame()
        self.playoff_boxes_cache = pd.DataFrame()
        self.regular_boxes_cache = pd.DataFrame()
        self.injured_cache = dict()
        self.roster_info_cache = pd.DataFrame()
        self.regular_boxes_cache_only_played = pd.DataFrame()
        self.update_timestamp_game_data = datetime.datetime.now()
        self.update_timestamp_regular_boxes = datetime.datetime.now()
        self.update_timestamp_playoff_game_data = datetime.datetime.now()
        self.update_timestamp_playoff_boxes = datetime.datetime.now()
        self.update_timestamp_sit_or_injured_playoff = datetime.datetime.now()
        self.update_timestamp_roster_info = datetime.datetime.now()
        print(f"-->Loading data for {self.season}...")
        loader_1 = self.roster_info.copy()
        loader_2 = self.game_data.copy()
        loader_3 = self.regular_boxes.copy()
        loader_4 = self.playoff_game_data.copy()
        loader_5 = self.playoff_boxes.copy()
        loader_6 = self.sit_or_injured_playoff.copy()

    @property
    def roster_info(self):
        if (self.roster_info_cache.empty) or (
            (datetime.datetime.now().year in [self.year, self.year + 1])
            and (
                datetime.datetime.now() - self.update_timestamp_roster_info
                > datetime.timedelta(seconds=3600)
            )
        ):
            print("---->Loading or updating player info...")
            all_players = []
            for team_id in self.regular_boxes.TEAM_ID.unique():
                roster = endpoints.commonteamroster.CommonTeamRoster(
                    team_id=team_id, season=self.season
                ).get_data_frames()[0]
                all_players.append(roster)
                time.sleep(2)
            all_players = pd.concat(all_players)
            self.roster_info_cache = all_players[
                ["TeamID", "PLAYER_ID", "POSITION"]
            ].rename({"TeamID": "TEAM_ID"}, axis=1)
            self.update_timestamp_roster_info = datetime.datetime.now()
        return self.roster_info_cache

    @property
    def game_data(self) -> None:
        """Set game data in object cache in long format."""
        if self.game_data_cache.shape[0] == 0:
            print(
                "---->Loading regular season game data for this year for the first time..."
            )
            all_games = (
                endpoints.leaguegamefinder.LeagueGameFinder(
                    season_type_nullable=SeasonType.regular, season_nullable=self.season
                )
                .get_data_frames()[0]
                .query("TEAM_ID in @nba_team_ids")
            )
            time.sleep(2)
        elif (datetime.datetime.now().year in [self.year, self.year + 1]) and (
            datetime.datetime.now() - self.update_timestamp_game_data
            > datetime.timedelta(seconds=3600)
        ):
            print("Updating resular season game data.")
            all_games = (
                endpoints.leaguegamefinder.LeagueGameFinder(
                    season_type_nullable=SeasonType.regular, season_nullable=self.season
                )
                .get_data_frames()[0]
                .query("TEAM_ID in @nba_team_ids")
            )
            self.update_timestamp_game_data = datetime.datetime.now()
            time.sleep(2)
        else:
            return self.game_data_cache
        all_games["HOME_AWAY"] = [
            "H" if x == 1 else "A" for x in all_games.MATCHUP.str.contains("vs")
        ]
        all_games = all_games[
            [
                "GAME_ID",
                "GAME_DATE",
                "HOME_AWAY",
                "TEAM_ID",
                "TEAM_ABBREVIATION",
                "PTS",
                "FGM",
                "FGA",
                "FG_PCT",
                "FG3M",
                "FG3A",
                "FG3_PCT",
                "FTM",
                "FTA",
                "FT_PCT",
                "OREB",
                "DREB",
                "REB",
                "AST",
                "STL",
                "BLK",
                "TOV",
                "PF",
                "PLUS_MINUS",
            ]
        ].copy()
        all_games = all_games.pivot(index="GAME_ID", columns="HOME_AWAY").reset_index()
        all_games.columns = all_games.columns.map(lambda x: "_".join(x))
        all_games["OUTCOME"] = [
            0 if PLUS_MINUS_H < 0 else 1 for PLUS_MINUS_H in all_games.PLUS_MINUS_H
        ]
        all_games = (
            all_games.rename(
                columns={"GAME_DATE_H": "GAME_DATE", "GAME_ID_": "GAME_ID"}
            )
            .drop(["GAME_DATE_A"], axis=1)
            .copy()
        )
        self.game_data_cache = all_games.query(
            "TEAM_ID_H in @nba_team_ids & TEAM_ID_A in @nba_team_ids"
        )
        return self.game_data_cache

    @property
    def regular_boxes(self) -> None:
        """Set regular season player box summaries"""
        if self.regular_boxes_cache.shape[0] == 0:
            print(
                "---->Loading regular season player box data for this year for the first time..."
            )
            self.regular_boxes_cache = (
                endpoints.PlayerGameLogs(
                    season_type_nullable=SeasonType.regular, season_nullable=self.season
                )
                .get_data_frames()[0]
                .query("TEAM_ID in @nba_team_ids")
            )
            time.sleep(2)
        elif (datetime.datetime.now().year in [self.year, self.year + 1]) and (
            datetime.datetime.now() - self.update_timestamp_regular_boxes
            > datetime.timedelta(seconds=3600)
        ):
            print("---->Updating regular season box data...")
            self.regular_boxes_cache = (
                endpoints.PlayerGameLogs(
                    season_type_nullable=SeasonType.regular, season_nullable=self.season
                )
                .get_data_frames()[0]
                .query("TEAM_ID in @nba_team_ids")
            )
            self.update_timestamp_regular_boxes = datetime.datetime.now()
            time.sleep(2)
        return self.regular_boxes_cache

    @property
    def regular_boxes_summary(self):
        regular_boxes = self.regular_boxes.copy()
        regular_boxes_summary = (
            regular_boxes[
                [
                    "TEAM_ID",
                    "PLAYER_ID",
                    "MIN",
                    "PTS",
                    "FGM",
                    "FGA",
                    "FG_PCT",
                    "FG3M",
                    "FG3A",
                    "FG3_PCT",
                    "FTM",
                    "FTA",
                    "FT_PCT",
                    "OREB",
                    "DREB",
                    "REB",
                    "AST",
                    "STL",
                    "BLK",
                    "TOV",
                    "PF",
                    "PLUS_MINUS",
                ]
            ]
            .fillna(0)
            .groupby(["PLAYER_ID", "TEAM_ID"])
            .agg(["mean"])
            .reset_index()
        )
        regular_boxes_summary.columns = regular_boxes_summary.columns.map(
            lambda x: "_".join(x)
        )
        regular_boxes_summary = regular_boxes_summary.rename(
            columns={"PLAYER_ID_": "PLAYER_ID", "TEAM_ID_": "TEAM_ID"}
        ).copy()
        return regular_boxes_summary

    @property
    def playoff_game_data(self) -> None:
        """Set playoff game data in object cache in wide format."""
        if self.playoff_game_data_cache.shape[0] == 0:
            print("---->Loading playoff game data for this year for the first time...")
            all_games = (
                endpoints.leaguegamefinder.LeagueGameFinder(
                    season_type_nullable=SeasonTypePlayoffs.playoffs,
                    season_nullable=self.season,
                )
                .get_data_frames()[0]
                .query("TEAM_ID in @nba_team_ids")
            )
            time.sleep(2)
        elif (datetime.datetime.now().year in [self.year, self.year + 1]) and (
            datetime.datetime.now() - self.update_timestamp_playoff_game_data
            > datetime.timedelta(seconds=3600)
        ):
            print("Updating playoff game data.")
            all_games = (
                endpoints.leaguegamefinder.LeagueGameFinder(
                    season_type_nullable=SeasonTypePlayoffs.playoffs,
                    season_nullable=self.season,
                )
                .get_data_frames()[0]
                .query("TEAM_ID in @nba_team_ids")
            )
            self.update_timestamp_playoff_game_data = datetime.datetime.now()
            time.sleep(2)
        else:
            return self.playoff_game_data_cache
        all_games["HOME_AWAY"] = [
            "H" if x == 1 else "A" for x in all_games.MATCHUP.str.contains("vs")
        ]
        all_games = all_games[
            [
                "GAME_ID",
                "GAME_DATE",
                "HOME_AWAY",
                "TEAM_ID",
                "TEAM_ABBREVIATION",
                "PTS",
                "FGM",
                "FGA",
                "FG_PCT",
                "FG3M",
                "FG3A",
                "FG3_PCT",
                "FTM",
                "FTA",
                "FT_PCT",
                "OREB",
                "DREB",
                "REB",
                "AST",
                "STL",
                "BLK",
                "TOV",
                "PF",
                "PLUS_MINUS",
            ]
        ].copy()
        all_games = all_games.pivot(index="GAME_ID", columns="HOME_AWAY").reset_index()
        all_games.columns = all_games.columns.map(lambda x: "_".join(x))
        all_games["OUTCOME"] = [
            0 if PLUS_MINUS_H < 0 else 1 for PLUS_MINUS_H in all_games.PLUS_MINUS_H
        ]
        all_games = (
            all_games.rename(
                columns={"GAME_DATE_H": "GAME_DATE", "GAME_ID_": "GAME_ID"}
            )
            .drop(["GAME_DATE_A"], axis=1)
            .copy()
        )
        self.playoff_game_data_cache = all_games.query(
            "TEAM_ID_H in @nba_team_ids & TEAM_ID_A in @nba_team_ids"
        )
        return self.playoff_game_data_cache

    @property
    def playoff_boxes(self):
        """Load player boxes for all playoff games."""
        if self.playoff_boxes_cache.shape[0] == 0:
            print(
                "---->Loading playoff player box data for this year for the first time..."
            )
            post_boxes = (
                endpoints.PlayerGameLogs(
                    season_type_nullable=SeasonTypePlayoffs.playoffs,
                    season_nullable=self.season,
                )
                .get_data_frames()[0]
                .query("TEAM_ID in @nba_team_ids")
            )
            time.sleep(2)
        elif (datetime.datetime.now().year in [self.year, self.year + 1]) and (
            datetime.datetime.now() - self.update_timestamp_playoff_boxes
            > datetime.timedelta(seconds=3600)
        ):
            print("---->Updating playoff box season game data.")
            post_boxes = (
                endpoints.PlayerGameLogs(
                    season_type_nullable=SeasonTypePlayoffs.playoffs,
                    season_nullable=self.season,
                )
                .get_data_frames()[0]
                .query("TEAM_ID in @nba_team_ids")
            )
            self.update_timestamp_playoff_boxes = datetime.datetime.now()
            time.sleep(2)
        else:
            return self.playoff_boxes_cache
        playoff_boxes_cache = post_boxes[
            [
                "GAME_ID",
                "TEAM_ID",
                "PLAYER_ID",
                "GAME_DATE",
                "MIN",
                "PTS",
                "FGM",
                "FGA",
                "FG_PCT",
                "FG3M",
                "FG3A",
                "FG3_PCT",
                "FTM",
                "FTA",
                "FT_PCT",
                "OREB",
                "DREB",
                "REB",
                "AST",
                "STL",
                "BLK",
                "TOV",
                "PF",
                "PLUS_MINUS",
            ]
        ]
        check_play_time_dist = self.regular_boxes_summary.copy()
        check_play_time_dist[
            "Regular_Season_Play_Time_Rank"
        ] = check_play_time_dist.groupby("TEAM_ID").MIN_mean.rank(ascending=False)
        player_team_rank = check_play_time_dist[
            ["PLAYER_ID", "Regular_Season_Play_Time_Rank"]
        ]
        self.playoff_boxes_cache = playoff_boxes_cache.merge(
            player_team_rank, how="left", on="PLAYER_ID"
        )
        return self.playoff_boxes_cache

    def get_playoff_results_up_to_date(self, date: str):  # Input string as "%Y-%m-%d"
        return self.playoff_game_data.query("GAME_DATE < @date")

    def get_team_rosters_from_regular_season(self):
        """Organize dictionary where keys are team_ids and items are lists of player_ids."""
        rosters_df = self.roster_info[["PLAYER_ID", "TEAM_ID"]].drop_duplicates()
        rosters_dict = {
            team: players.tolist()
            for team, players in rosters_df.groupby("TEAM_ID")["PLAYER_ID"]
        }
        return rosters_dict

    def get_players_played_in_each_playoff_game(self):
        """Organize nested dictionary where outer key is team_id inner key is game_date and item is list of player_ids."""
        played = self.playoff_boxes[["TEAM_ID", "PLAYER_ID", "GAME_ID"]]
        nested_dict = {team: dict() for team in played.TEAM_ID.unique()}
        for team in nested_dict.keys():
            played_team = played.query("TEAM_ID == @team")
            nested_dict[team].update(
                {
                    game_id: players.tolist()
                    for game_id, players in played_team.groupby("GAME_ID")["PLAYER_ID"]
                }
            )
        return nested_dict

    @property
    def sit_or_injured_playoff(self):
        """Gets whether players sat on each playoff game date for year in nested dict."""
        if len(self.injured_cache) == 0 or (
            (datetime.datetime.now().year in [self.year, self.year + 1])
            and (
                datetime.datetime.now() - self.update_timestamp_sit_or_injured_playoff
                > datetime.timedelta(seconds=3600)
            )
        ):
            roster_dict = self.get_team_rosters_from_regular_season()
            played_dict = self.get_players_played_in_each_playoff_game()
            injury_dict = {
                team: {
                    game_id: [
                        player
                        for player in roster_dict[team]
                        if player not in played_dict.get(team, {}).get(game_id, [])
                    ]
                    for game_id in played_dict.get(team, {}).keys()
                }
                for team in roster_dict.keys()
            }
            self.injured_cache = injury_dict
            self.update_timestamp_sit_or_injured_playoff = datetime.datetime.now()
        return self.injured_cache

    def reweight_replacements_for_missing_player(
        self, possible_replacement_player_ids, remove_injured, injured_player_id
    ):
        """Reweights replacement players for ONE missing player"""
        if len(possible_replacement_player_ids) == 0:
            raise KeyError("No valid replacements.")
        team_id = remove_injured.reset_index(drop=1).TEAM_ID[0]
        possile_replacement_box_summary = self.regular_boxes_summary.query(
            "(PLAYER_ID in @possible_replacement_player_ids) & (TEAM_ID == @team_id)"
        ).sort_values(by="MIN_mean", ascending=False)
        min_diff = (
            self.regular_boxes_summary.query("PLAYER_ID == @injured_player_id")
            .reset_index(drop=0)
            .MIN_mean[0]
        )
        max_minutes = (
            min_diff.copy()
        )  # set max minutes to number of minutes adjusted player was playing and incriment up if needed
        if min_diff <= 0:
            return pd.DataFrame(columns=["PLAYER_ID"])
        while (min_diff > 0) & (max_minutes <= 48):
            replacement_df = []
            for index, row in possile_replacement_box_summary.iterrows():
                if (min_diff > 0) & (row.MIN_mean < max_minutes):
                    min_diff = min_diff - (max_minutes - row.MIN_mean)
                    if min_diff < 0:
                        player_min_new = max_minutes + min_diff
                    else:
                        player_min_new = max_minutes
                    prop_orig_time = player_min_new / row.MIN_mean
                    updated_stats = (
                        pd.DataFrame(row)
                        .T.drop(
                            [
                                "PLAYER_ID",
                                "TEAM_ID",
                                "FG_PCT_mean",
                                "FG3_PCT_mean",
                                "FT_PCT_mean",
                                "PLUS_MINUS_mean",
                            ],
                            axis=1,
                        )
                        .mul(prop_orig_time, axis=0)
                        .copy()
                    )
                    updated_stats["FG_PCT_mean"] = (
                        updated_stats.FGM_mean / updated_stats.FGA_mean
                    )
                    updated_stats["FG3_PCT_mean"] = (
                        updated_stats.FG3M_mean / updated_stats.FG3A_mean
                    )
                    updated_stats["FT_PCT_mean"] = (
                        updated_stats.FTM_mean / updated_stats.FTA_mean
                    )
                    updated_stats["PLAYER_ID"] = row.PLAYER_ID
                    updated_stats["TEAM_ID"] = row.TEAM_ID
                    replacement_df.append(updated_stats)
            max_minutes += 1
        replacement_df = pd.concat(replacement_df)
        if min_diff > 0:
            raise KeyError(
                f"Warning: Not enough eligible players on bench to account for all injuries with full 40 minutes of play for injury_id {injured_player_id}."
            )
        return replacement_df

    def get_team_record(self, team_abb):
        home_games = np.array(
            self.game_data.query("TEAM_ABBREVIATION_H == 'BOS'").OUTCOME
        )
        away_games = 1 - np.array(
            self.game_data.query("TEAM_ABBREVIATION_A == 'BOS'").OUTCOME
        )
        return np.mean(np.append(home_games, away_games))

    def reweight_stats(
        self, team_id, game_id, avg_minutes_played_cutoff, games_ahead_of_today
    ):
        """Get injury reweighted predicted stats."""
        if game_id == 0:
            injured = [
                player_id
                for player_id in scrape_current_nba_injuries(
                    games_ahead_of_today
                ).PLAYER_ID
                if not math.isnan(player_id)
            ]
        else:
            injured = self.sit_or_injured_playoff[team_id][game_id]
        on_roster_still = self.get_team_rosters_from_regular_season()[team_id]
        # Only considered injury needing replacement if average minutes is greater than 30
        injured = (
            self.regular_boxes_summary.query(
                "(TEAM_ID == @team_id) & (PLAYER_ID in @injured) & (MIN_mean > 30) & (PLAYER_ID in @on_roster_still)"
            )
            .reset_index(drop=1)
            .PLAYER_ID.tolist()
        )  # remove players below injury adjustment cutoff (we dont care if a player that doesnt play is injured)
        remove_injured = self.regular_boxes_summary.query(
            "(PLAYER_ID not in @injured) & (PLAYER_ID in @on_roster_still) & (TEAM_ID == @team_id)"
        )
        for injured_player_id in injured:
            try:
                injured_pos = (
                    self.roster_info.query("PLAYER_ID == @injured_player_id")
                    .reset_index(drop=1)
                    .POSITION[0]
                )
            except KeyError:
                continue  # player is no longer on roster
            # Possible Positions: ['G-F', 'F-G', 'G', 'C', 'F-C', 'F', 'C-F']
            if (injured_pos == "G-F") or (injured_pos == "F-G"):
                possible_replacement_player_ids = (
                    self.roster_info.query(
                        "(PLAYER_ID in @on_roster_still) & ('G' in POSITION | 'F' in POSITION) & (PLAYER_ID not in @injured)"
                    )
                    .reset_index(drop=1)
                    .PLAYER_ID.tolist()
                )
            if injured_pos == "G":
                possible_replacement_player_ids = (
                    self.roster_info.query(
                        "(PLAYER_ID in @on_roster_still) & ('G' in POSITION) & (PLAYER_ID not in @injured)"
                    )
                    .reset_index(drop=1)
                    .PLAYER_ID.tolist()
                )
            if injured_pos == "C":
                possible_replacement_player_ids = (
                    self.roster_info.query(
                        "(PLAYER_ID in @on_roster_still) & ('C' in POSITION) & (PLAYER_ID not in @injured)"
                    )
                    .reset_index(drop=1)
                    .PLAYER_ID.tolist()
                )
            if (injured_pos == "F-C") or (injured_pos == "C-F"):
                possible_replacement_player_ids = (
                    self.roster_info.query(
                        "(PLAYER_ID in @on_roster_still) & ('C' in POSITION | 'F' in POSITION) & (PLAYER_ID not in @injured)"
                    )
                    .reset_index(drop=1)
                    .PLAYER_ID.tolist()
                )
            if injured_pos == "F":
                possible_replacement_player_ids = (
                    self.roster_info.query(
                        "(PLAYER_ID in @on_roster_still) & ('F' in POSITION) & (PLAYER_ID not in @injured)"
                    )
                    .reset_index(drop=1)
                    .PLAYER_ID.tolist()
                )
            else:
                possible_replacement_player_ids = (
                    self.roster_info.query(
                        "(PLAYER_ID in @on_roster_still) & (PLAYER_ID not in @injured)"
                    )
                    .reset_index(drop=1)
                    .PLAYER_ID.tolist()
                )
            try:
                replacement_df = self.reweight_replacements_for_missing_player(
                    possible_replacement_player_ids=possible_replacement_player_ids,
                    remove_injured=remove_injured,
                    injured_player_id=injured_player_id,
                )
            except KeyError:  # if none left in position move to other positions
                possible_replacement_player_ids = (
                    self.roster_info.query(
                        "(PLAYER_ID in @on_roster_still) & (PLAYER_ID not in @injured)"
                    )
                    .reset_index(drop=1)
                    .PLAYER_ID.tolist()
                )
                replacement_df = self.reweight_replacements_for_missing_player(
                    possible_replacement_player_ids=possible_replacement_player_ids,
                    remove_injured=remove_injured,
                    injured_player_id=injured_player_id,
                )
            replaced_player_ids = replacement_df.PLAYER_ID.tolist()
            remove_injured = pd.concat(
                [
                    remove_injured.query("PLAYER_ID not in @replaced_player_ids"),
                    replacement_df,
                ]
            )
        return remove_injured.drop(["TEAM_ID", "PLUS_MINUS_mean"], axis=1)

    def get_regular_season_summary_stats_unadjusted(self, team_id):
        """Get team regular season summary statistics for all teams."""
        on_roster_still = self.get_team_rosters_from_regular_season()[team_id]
        players_summary = self.regular_boxes_summary.query(
            "(PLAYER_ID in @on_roster_still) & (TEAM_ID == @team_id)"
        )
        return players_summary.drop(["TEAM_ID", "PLUS_MINUS_mean"], axis=1)

    def get_home_win_percentage(self, team_id):
        """Get home win percentage for team"""
        return self.game_data.query("TEAM_ID_H == @team_id").OUTCOME.mean()

    def get_away_win_percentage(self, team_id):
        """Get away win percentage for team"""
        return 1 - self.game_data.query("TEAM_ID_A == @team_id").OUTCOME.mean()

    def feature_creator(
        self,
        home_team,
        away_team,
        game_id,
        injury_adjusted: bool,
        avg_minutes_played_cutoff,
        games_ahead_of_today,
    ):
        if injury_adjusted:
            home_reweighted = (
                self.reweight_stats(
                    team_id=home_team,
                    game_id=game_id,
                    avg_minutes_played_cutoff=avg_minutes_played_cutoff,
                    games_ahead_of_today=games_ahead_of_today,
                )
                .query("MIN_mean >= @avg_minutes_played_cutoff")
                .drop(["MIN_mean", "PLAYER_ID"], axis=1)
                .add_suffix("_H")
                .rename(columns=lambda x: x.replace("_mean", ""))
            )
            depth_at_cutoff = home_reweighted.shape[0]
            home_reweighted = (
                home_reweighted.agg(["mean", "median", "max"]).stack().to_frame().T
            )
            home_reweighted.columns = [
                "_".join(map(str, c)) for c in home_reweighted.columns
            ]
            home_reweighted["depth_at_cutoff_H"] = depth_at_cutoff
            home_reweighted["home_win_percentage"] = self.get_home_win_percentage(
                away_team
            )
            away_reweighted = (
                self.reweight_stats(
                    team_id=away_team,
                    game_id=game_id,
                    avg_minutes_played_cutoff=avg_minutes_played_cutoff,
                    games_ahead_of_today=games_ahead_of_today,
                )
                .query("MIN_mean >= @avg_minutes_played_cutoff")
                .drop(["MIN_mean", "PLAYER_ID"], axis=1)
                .add_suffix("_A")
                .rename(columns=lambda x: x.replace("_mean", ""))
            )
            depth_at_cutoff = away_reweighted.shape[0]
            away_reweighted = (
                away_reweighted.agg(["mean", "median", "max"]).stack().to_frame().T
            )
            away_reweighted.columns = [
                "_".join(map(str, c)) for c in away_reweighted.columns
            ]
            away_reweighted["depth_at_cutoff_A"] = depth_at_cutoff
            away_reweighted["road_win_percentage"] = self.get_away_win_percentage(
                away_team
            )
        else:
            home_reweighted = (
                self.get_regular_season_summary_stats_unadjusted(team_id=home_team)
                .query("MIN_mean >= @avg_minutes_played_cutoff")
                .drop(["MIN_mean", "PLAYER_ID"], axis=1)
                .add_suffix("_H")
                .rename(columns=lambda x: x.replace("_mean", ""))
            )
            depth_at_cutoff = home_reweighted.shape[0]
            home_reweighted = (
                home_reweighted.agg(["mean", "median", "max"]).stack().to_frame().T
            )
            home_reweighted.columns = [
                "_".join(map(str, c)) for c in home_reweighted.columns
            ]
            home_reweighted["depth_at_cutoff_H"] = depth_at_cutoff
            home_reweighted["home_win_percentage"] = self.get_home_win_percentage(
                away_team
            )
            away_reweighted = (
                self.get_regular_season_summary_stats_unadjusted(team_id=away_team)
                .query("MIN_mean >= @avg_minutes_played_cutoff")
                .drop(["MIN_mean", "PLAYER_ID"], axis=1)
                .add_suffix("_A")
                .rename(columns=lambda x: x.replace("_mean", ""))
            )
            depth_at_cutoff = away_reweighted.shape[0]
            away_reweighted = (
                away_reweighted.agg(["mean", "median", "max"]).stack().to_frame().T
            )
            away_reweighted.columns = [
                "_".join(map(str, c)) for c in away_reweighted.columns
            ]
            away_reweighted["depth_at_cutoff_A"] = depth_at_cutoff
            away_reweighted["road_win_percentage"] = self.get_away_win_percentage(
                away_team
            )
        adjusted_df = pd.concat([home_reweighted, away_reweighted], axis=1)
        return adjusted_df

    def get_features_for_game(
        self, game_id, injury_adjusted: bool, avg_minutes_played_cutoff
    ):
        """Return model features for past game."""
        game = self.playoff_game_data.query("GAME_ID == @game_id")
        if game.empty:
            raise IndexError(
                "Game requested is not a valid playoff game for this year."
            )
        home_team = game.reset_index(drop=1).TEAM_ID_H[0]
        away_team = game.reset_index(drop=1).TEAM_ID_A[0]
        features = self.feature_creator(
            home_team=home_team,
            away_team=away_team,
            game_id=game_id,
            injury_adjusted=injury_adjusted,
            avg_minutes_played_cutoff=avg_minutes_played_cutoff,
            games_ahead_of_today=0,
        )
        return features

    def get_features_for_upcoming(
        self,
        home_team,
        away_team,
        injury_adjusted,
        avg_minutes_played_cutoff,
        games_ahead_of_today,
    ):
        """Return model features for upcoming game."""
        features = self.feature_creator(
            home_team=home_team,
            away_team=away_team,
            game_id=0,
            injury_adjusted=injury_adjusted,
            avg_minutes_played_cutoff=avg_minutes_played_cutoff,
            games_ahead_of_today=games_ahead_of_today,
        )
        return features

    def get_train_for_all_playoff_games(
        self, injury_adjusted: bool, avg_minutes_played_cutoff: int
    ):
        """Return dataframe of all adjusted features and game outcomes for this year."""
        features = []
        for _, row in self.playoff_game_data.iterrows():
            feature = self.get_features_for_game(
                game_id=row.GAME_ID,
                injury_adjusted=injury_adjusted,
                avg_minutes_played_cutoff=avg_minutes_played_cutoff,
            )
            feature["HOME_WIN"] = row.OUTCOME
            features.append(feature)
        return pd.concat(features)


class training_dataset:
    def __init__(self, since=2000):
        self.training_sets_cache = dict()
        self.years_cache = dict()
        self.since = since
        print(
            f"Loading NBA data from {self.since} until {datetime.datetime.now().year - 2}..."
        )
        self.load_year_data()

    def get_training_dataset(
        self, injury_adjusted: bool, avg_minutes_played_cutoff: int, force_update: bool
    ):
        settings_string = f"injury_adjusted = {injury_adjusted}, avg_minutes_played_cutoff = {avg_minutes_played_cutoff}"
        if (force_update == True) or (
            self.since not in self.training_sets_cache.keys()
        ):
            self.load_train_data(
                injury_adjusted=injury_adjusted,
                avg_minutes_played_cutoff=avg_minutes_played_cutoff,
            )
        elif settings_string not in self.training_sets_cache.get(self.since).keys():
            self.load_train_data(
                injury_adjusted=injury_adjusted,
                avg_minutes_played_cutoff=avg_minutes_played_cutoff,
            )
        all_train = []
        for year, settings_dict in self.training_sets_cache.items():
            all_train.append(settings_dict.get(settings_string))
        return pd.concat(all_train)

    def year(self, year_id):
        """Get year object."""
        return self.years_cache.get(year_id)

    def load_year_data(self):
        """Load all year classes."""
        for year_get in range(self.since, datetime.datetime.now().year - 2):
            try:
                self.years_cache.update({year_get: year(year_get)})
            except:
                print("Timeout occured. Try one more time.")
                time.sleep(60)
                self.years_cache.update({year_get: year(year_get)})

    def load_train_data(
        self, injury_adjusted: bool, avg_minutes_played_cutoff: int
    ) -> None:
        """Load training and outcomes for all years."""
        print(
            f"Loading training data for years from from {self.since} until {datetime.datetime.now().year - 2}..."
        )
        for year_load in range(self.since, datetime.datetime.now().year - 2):
            print(
                f"---->Loading training for {year_load} with injury_adjustments = {injury_adjusted} and avg_minutes_played_cutoff = {avg_minutes_played_cutoff}..."
            )
            training = self.year(year_load).get_train_for_all_playoff_games(
                injury_adjusted=injury_adjusted,
                avg_minutes_played_cutoff=avg_minutes_played_cutoff,
            )
            if year_load not in self.training_sets_cache.keys():
                self.training_sets_cache.update(
                    {
                        year_load: {
                            f"injury_adjusted = {injury_adjusted}, avg_minutes_played_cutoff = {avg_minutes_played_cutoff}": training
                        }
                    }
                )
            else:
                self.training_sets_cache.get(year_load).update(
                    {
                        f"injury_adjusted = {injury_adjusted}, avg_minutes_played_cutoff = {avg_minutes_played_cutoff}": training
                    }
                )


class current_state:
    def __init__(self):
        if datetime.datetime.now().month <= 8:
            self.year = datetime.datetime.now().year - 1
        else:
            self.year = datetime.datetime.now().year
        self.created_on = datetime.datetime.now()
        self.year_class = {}
        with open("data/best_playoff_model.pickle", "rb") as handle:
            self.model = pickle.load(handle)
        loader_year_class = self.get_current_year_class
        self.script = {
            "R1": [
                ("1_EAST", "8_EAST"),
                ("2_EAST", "7_EAST"),
                ("3_EAST", "6_EAST"),
                ("4_EAST", "5_EAST"),
                ("1_WEST", "8_WEST"),
                ("2_WEST", "7_WEST"),
                ("3_WEST", "6_WEST"),
                ("4_WEST", "5_WEST"),
            ],
            "R2": [
                ("1_EAST_8_EAST", "4_EAST_5_EAST"),
                ("2_EAST_7_EAST", "3_EAST_6_EAST"),
                ("1_WEST_8_WEST", "4_WEST_5_WEST"),
                ("2_WEST_7_WEST", "3_WEST_6_WEST"),
            ],
            "R3": [
                ("1_EAST_8_EAST_4_EAST_5_EAST", "2_EAST_7_EAST_3_EAST_6_EAST"),
                ("1_WEST_8_WEST_4_WEST_5_WEST", "2_WEST_7_WEST_3_WEST_6_WEST"),
            ],
            "R4": [
                (
                    "1_EAST_8_EAST_4_EAST_5_EAST_2_EAST_7_EAST_3_EAST_6_EAST",
                    "1_WEST_8_WEST_4_WEST_5_WEST_2_WEST_7_WEST_3_WEST_6_WEST",
                )
            ],
        }

    def print_current_team_injuries(self, team_id, games_ahead_of_today):
        """Prints current team injuries"""
        all_injuries = scrape_current_nba_injuries(games_ahead_of_today)
        this_year = self.get_current_year_class.get("current")
        players_this_team = (
            this_year.roster_info.query("TEAM_ID == @team_id")
            .reset_index(drop=1)
            .PLAYER_ID
        )
        injured_players = (
            all_injuries.query("PLAYER_ID in @players_this_team")
            .reset_index(drop=1)
            .PLAYER_NAME.tolist()
        )
        return injured_players

    def get_current_max_playoff_seed_probs(self):
        """Gets teams with max probability of each seed in tourney."""
        seeds = self.get_playoff_picture_liklihood()
        ret = dict()
        for team_abb, seed_dict in seeds.items():
            team_seeds = []
            team_probs = []
            for seed, prob in seed_dict.items():
                team_seeds.append(seed)
                team_probs.append(prob)
            if np.sum(team_probs) == 0:
                continue
            seed_choice = team_seeds[team_probs.index(max(team_probs))]
            with_prob = seed_dict[seed_choice]
            seed_choice = seed_choice.replace("_SEED", "")
            ret.update({seed_choice: {team_abb: with_prob}})
        return ret

    def get_base_seeds(self):
        """Gets base seeds for simulation"""
        current_round_state = self.get_current_max_playoff_seed_probs()
        seeds = []
        for key, this_dict in current_round_state.items():
            this_seed = pd.DataFrame({"SEED": [key]})
            for team_abb, prob in this_dict.items():
                this_seed["TEAM_ABB"] = team_abb
            seeds.append(this_seed)
        seeds = pd.concat(seeds)
        return seeds

    def get_current_tourney_state(self):
        """Gets the state of the tournement currently. If hasnt started just gets max seed probs."""
        seeds = self.get_base_seeds()
        this_year = self.year_class.get("current")
        games_thus_far = this_year.playoff_game_data[
            ["TEAM_ABBREVIATION_H", "TEAM_ABBREVIATION_A", "OUTCOME"]
        ].copy()
        games_thus_far = (
            games_thus_far.merge(
                seeds, left_on="TEAM_ABBREVIATION_H", right_on="TEAM_ABB"
            )
            .rename(columns={"SEED": "SEED_H"})
            .drop(["TEAM_ABB"], axis=1)
            .merge(seeds, left_on="TEAM_ABBREVIATION_A", right_on="TEAM_ABB")
            .rename(columns={"SEED": "SEED_A"})
            .drop(["TEAM_ABB"], axis=1)
            .copy()
        )
        games_thus_far["WINNER"] = [
            row.TEAM_ABBREVIATION_H if row.OUTCOME == 1 else row.TEAM_ABBREVIATION_A
            for _, row in games_thus_far.iterrows()
        ]
        games_thus_far
        got_this_far = True
        current_round_state = {"R0": self.get_current_max_playoff_seed_probs()}
        for round in ["R1", "R2", "R3", "R4"]:
            matchups = self.script[round]
            current_round_state.update({round: dict()})
            for matchup in matchups:
                games_in_this_matchup = games_thus_far.query(
                    "(SEED_H == @matchup[0] & SEED_A == @matchup[1]) or (SEED_H == @matchup[1] & SEED_A == @matchup[0])"
                )
                matchup_status = dict(games_in_this_matchup.WINNER.value_counts())
                for team in [
                    games_in_this_matchup.TEAM_ABBREVIATION_A.unique()[0],
                    games_in_this_matchup.TEAM_ABBREVIATION_H.unique()[0],
                ]:
                    if team not in matchup_status.keys():
                        matchup_status.update({team: 0})
                current_round_state[round].update(
                    {f"{matchup[0]}_{matchup[1]}": matchup_status}
                )
                finished = False
                for key, value in matchup_status.items():
                    if value == 4:
                        finished = True
                        new_seed = pd.DataFrame(
                            {"Seed": [matchup[0] + "_" + matchup[1]], "TEAM_ABB": [key]}
                        )
                        seeds = pd.concat([seeds, new_seed])
                if not finished:
                    got_this_far = False
            if not got_this_far:
                break
        return current_round_state

    def get_playoff_picture_liklihood(self):
        """Gets all probabilities of seeds for tourney."""
        playoff_proj = scrape_nba_playoff_projections()
        west = playoff_proj["West"]
        east = playoff_proj["East"]
        seed_columns = [
            "1_SEED_PROB",
            "2_SEED_PROB",
            "3_SEED_PROB",
            "4_SEED_PROB",
            "5_SEED_PROB",
            "6_SEED_PROB",
            "7_SEED_PROB",
            "8_SEED_PROB",
        ]
        west[seed_columns] = west[seed_columns].applymap(float)
        east[seed_columns] = east[seed_columns].applymap(float)
        possible_seeds_dict = dict()
        for index, row in east.iterrows():
            team_id = team_id_to_abb_conv(row.TEAM_ID)
            possible_seeds_dict.update({team_id: dict()})
            for seed in range(1, 9):
                possible_seeds_dict[team_id].update(
                    {f"{seed}_EAST": row[f"{seed}_SEED_PROB"]}
                )
        for index, row in west.iterrows():
            team_id = team_id_to_abb_conv(row.TEAM_ID)
            possible_seeds_dict.update({team_id: dict()})
            for seed in range(1, 9):
                possible_seeds_dict[team_id].update(
                    {f"{seed}_WEST": row[f"{seed}_SEED_PROB"]}
                )
        return possible_seeds_dict

    @property
    def get_current_year_class(self):
        if len(self.year_class.keys()) == 0:
            self.year_class.update({"current": year(self.year)})
        return self.year_class

    def predict_matchup(self, home_abb, away_abb, games_ahead_of_today=0):
        """Predicts upcoming matchup."""
        home_id, away_id = team_abb_to_id(home_abb), team_abb_to_id(away_abb)
        features = self.year_class.get("current").get_features_for_upcoming(
            home_team=home_id,
            away_team=away_id,
            injury_adjusted=self.model.injury_adjusted,
            avg_minutes_played_cutoff=self.model.avg_minutes_played_cutoff,
            games_ahead_of_today=games_ahead_of_today,
        )
        prob = self.model.model.predict_proba(features)
        return prob[0][1]  # Return home win probabilities

    def predict_series(
        self,
        higher_seed_abb,
        lower_seed_abb,
        higher_already_won=0,
        lower_already_won=0,
        for_simulation=False,
        series_starts_in_how_many_games=0,
    ):
        """Get probabilities of each team winning in games 4-7 of the series."""
        if (higher_already_won > 4) or (lower_already_won > 4):
            return KeyError("A team cant win more than 4 games in a series")
        if higher_already_won == 4:
            num_games = higher_already_won + lower_already_won
            return {higher_seed_abb: {num_games: 1}}
        if lower_already_won == 4:
            num_games = higher_already_won + lower_already_won
            return {lower_already_won: {num_games: 1}}
        prob_game_1 = self.predict_matchup(
            home_abb=higher_seed_abb,
            away_abb=lower_seed_abb,
            games_ahead_of_today=series_starts_in_how_many_games,
        )
        prob_game_2 = self.predict_matchup(
            home_abb=higher_seed_abb,
            away_abb=lower_seed_abb,
            games_ahead_of_today=series_starts_in_how_many_games + 1,
        )
        prob_game_3 = self.predict_matchup(
            home_abb=lower_seed_abb,
            away_abb=higher_seed_abb,
            games_ahead_of_today=series_starts_in_how_many_games + 2,
        )
        prob_game_4 = self.predict_matchup(
            home_abb=lower_seed_abb,
            away_abb=higher_seed_abb,
            games_ahead_of_today=series_starts_in_how_many_games + 3,
        )
        prob_game_5 = self.predict_matchup(
            home_abb=higher_seed_abb,
            away_abb=lower_seed_abb,
            games_ahead_of_today=series_starts_in_how_many_games + 4,
        )
        prob_game_6 = self.predict_matchup(
            home_abb=lower_seed_abb,
            away_abb=higher_seed_abb,
            games_ahead_of_today=series_starts_in_how_many_games + 5,
        )
        prob_game_7 = self.predict_matchup(
            home_abb=higher_seed_abb,
            away_abb=lower_seed_abb,
            games_ahead_of_today=series_starts_in_how_many_games + 6,
        )
        if not for_simulation:
            higher_id, lower_id = team_abb_to_id(higher_seed_abb), team_abb_to_id(
                lower_seed_abb
            )
            print(
                "Accounting for the following injuries and appropriate return timetables..."
            )

            print(
                f"""Injured for {higher_seed_abb}: 
            \n --->Projected Game 1:{self.print_current_team_injuries(higher_id, games_ahead_of_today = series_starts_in_how_many_games)}
            \n --->Projected Game 2:{self.print_current_team_injuries(higher_id, games_ahead_of_today = series_starts_in_how_many_games + 1)}
            \n --->Projected Game 3:{self.print_current_team_injuries(higher_id, games_ahead_of_today = series_starts_in_how_many_games + 2)}
            \n --->Projected Game 4:{self.print_current_team_injuries(higher_id, games_ahead_of_today = series_starts_in_how_many_games + 3)}
            \n --->Projected Game 5:{self.print_current_team_injuries(higher_id, games_ahead_of_today = series_starts_in_how_many_games + 4)}
            \n --->Projected Game 6:{self.print_current_team_injuries(higher_id, games_ahead_of_today = series_starts_in_how_many_games + 5)}
            \n --->Projected Game 7:{self.print_current_team_injuries(higher_id, games_ahead_of_today = series_starts_in_how_many_games + 6)} \n"""
            )

            print(
                f"""Injured for {lower_seed_abb}: 
            \n --->Projected Game 1:{self.print_current_team_injuries(lower_id, games_ahead_of_today = series_starts_in_how_many_games)}
            \n --->Projected Game 2:{self.print_current_team_injuries(lower_id, games_ahead_of_today = series_starts_in_how_many_games + 1)}
            \n --->Projected Game 3:{self.print_current_team_injuries(lower_id, games_ahead_of_today = series_starts_in_how_many_games + 2)}
            \n --->Projected Game 4:{self.print_current_team_injuries(lower_id, games_ahead_of_today = series_starts_in_how_many_games + 3)}
            \n --->Projected Game 5:{self.print_current_team_injuries(lower_id, games_ahead_of_today = series_starts_in_how_many_games + 4)}
            \n --->Projected Game 6:{self.print_current_team_injuries(lower_id, games_ahead_of_today = series_starts_in_how_many_games + 5)}
            \n --->Projected Game 7:{self.print_current_team_injuries(lower_id, games_ahead_of_today = series_starts_in_how_many_games + 6)} \n"""
            )

            print(
                f"{higher_seed_abb}-{lower_seed_abb} series is currently {higher_already_won}-{lower_already_won} \n"
            )
        prob_higher_wins_each_game = (
            prob_game_1,
            prob_game_2,
            prob_game_3,
            prob_game_4,
            prob_game_5,
            prob_game_6,
            prob_game_7,
        )
        num_already_played = higher_already_won + lower_already_won
        already_occured = np.append(
            np.repeat(0, lower_already_won), np.repeat(1, higher_already_won)
        )
        prob_higher_wins_each_game = np.append(
            already_occured, prob_higher_wins_each_game[num_already_played:]
        )
        if num_already_played < 4:
            games_left_to_play = list(range(4, 8))
        else:
            games_left_to_play = list(range(num_already_played + 1, 8))
        # Get possible sample space
        sample_space_previously_over = []
        for game in games_left_to_play:
            sample_space_new = list(
                itertools.product([0, 1], repeat=game - num_already_played)
            )
            sample_space = [
                tuple(np.append(already_occured, outcome))
                for outcome in sample_space_new
            ]
            sample_space_without_previously_over = [
                outcome
                for outcome in sample_space
                if (outcome[: game - 1] not in sample_space_previously_over)
            ]
            ended_this_round = [
                outcome
                for outcome in sample_space_without_previously_over
                if ((outcome.count(1) == 4) and (outcome[-1] == 1))
                or ((outcome.count(0) == 4) and (outcome[-1] == 0))
            ]
            sample_space_previously_over.extend(ended_this_round)
        outcomes = {higher_seed_abb: dict(), lower_seed_abb: dict()}
        for outcome in sample_space_previously_over:
            num_games = len(outcome)
            higher_win_prob_list = prob_higher_wins_each_game[:num_games]
            prob_of_what_occured = np.product(
                list(
                    map(
                        lambda x, y: 1 - y if x == 0 else y,
                        outcome,
                        higher_win_prob_list,
                    )
                ),
                dtype=np.float64,
            )
            if outcome.count(1) == 4:
                if num_games in outcomes[higher_seed_abb].keys():
                    outcomes[higher_seed_abb][num_games].append(prob_of_what_occured)
                else:
                    outcomes[higher_seed_abb].update(
                        {num_games: [prob_of_what_occured]}
                    )
            elif outcome.count(0) == 4:
                if num_games in outcomes[lower_seed_abb].keys():
                    outcomes[lower_seed_abb][num_games].append(prob_of_what_occured)
                else:
                    outcomes[lower_seed_abb].update({num_games: [prob_of_what_occured]})
            else:
                raise KeyError("Proper number of wins was not obtained for either team")
        total_prob_higher, total_prob_lower = 0, 0
        for team_abb, value in outcomes.items():
            for inner_key, inner_value in value.items():
                prob = np.sum(inner_value)
                outcomes[team_abb][inner_key] = prob
                if not for_simulation:
                    print(
                        f"        {team_abb} wins in {inner_key}: {round(prob*100, 2)}%"
                    )
                if team_abb == higher_seed_abb:
                    total_prob_higher += prob
                else:
                    total_prob_lower += prob
        if not for_simulation:
            print("__________Total Probabilities__________")
            print(
                f"        {higher_seed_abb} wins series: {round(total_prob_higher*100, 2)}%"
            )
            print(
                f"        {lower_seed_abb} wins series: {round(total_prob_lower*100, 2)}%"
            )
        if for_simulation:
            return outcomes

    def simulate_playoffs_from_this_point(self):
        """Simulates playoffs."""
        print(f"Simulating {self.year} NBA-playoffs")
        print(f"_____Pre-Playoffs_____")
        current_state = self.get_current_tourney_state()
        for seed, dictio in current_state["R0"].items():
            for team, prob in dictio.items():
                print(
                    f"{team} secures {seed[0]} seed in the {seed[2:]} with probability {prob}"
                )
        current_round_num = max([int(key[1]) for key in current_state.keys()])
        base_seeds = self.get_base_seeds()
        seeds = base_seeds.copy()
        curr_year = self.year_class.get("current")
        rounds_to_play = list(range(1, 5))
        games_from_now = 0
        for this_round in rounds_to_play:
            round_str = f"R{this_round}"
            # if previous round
            if current_round_num > this_round:
                current_round = current_state[f"R{current_round_num}"]
                for seed_reward, series_dict in current_round.items():
                    won_teams = 0
                    teams_record = dict()
                    for team_abb, games_won in series_dict.items():
                        if games_won == 4:
                            teams_record.update({"Won": (team_abb, games_won)})
                            won_teams += 1
                            seeds = pd.concat(
                                [
                                    seeds,
                                    pd.DataFrame(
                                        {"SEED": seed_reward, "TEAM_ABB": team_abb}
                                    ),
                                ]
                            )
                        else:
                            teams_record.update({"Lost": (team_abb, games_won)})
                    won, lost = teams_record["Won"], teams_record["Lost"]
                    print(
                        f"{won[0]} wins  {won[0]}-{lost[0]} in {won[1]+lost[1]} with probability 100%"
                    )
                    if won_teams != 1:
                        raise KeyError(
                            f"No team won four games in {series_dict}! Or both did! Check whats up with this record or contact developer."
                        )
                    games_from_now = 0
            # if current round
            elif current_round_num == this_round:
                print(f"_____ROUND {this_round} SIMULATION_____")
                current_round = current_state[f"R{current_round_num}"]
                matchups_split = self.script[round_str]
                all_round_matchups = ["_".join(matchup) for matchup in matchups_split]
                matchups_not_shown = list(
                    set(all_round_matchups) - set(current_round.keys())
                )
                for matchup in matchups_not_shown:
                    match = [
                        match for match in matchups_split if "_".join(match) == matchup
                    ][0]
                    current_round.update(
                        {
                            matchup: {
                                seeds.query("SEED == @match[0]")
                                .reset_index(drop=1)
                                .TEAM_ABB[0]: 0,
                                seeds.query("SEED == @match[1]")
                                .reset_index(drop=1)
                                .TEAM_ABB[0]: 0,
                            }
                        }
                    )
                # finish round by simulation
                for seed_reward, series_dict in current_round.items():
                    both_teams = list(series_dict.keys())
                    team_1, team_2 = both_teams[0], both_teams[1]
                    team_1_already_won, team_2_already_won = (
                        series_dict[team_1],
                        series_dict[team_2],
                    )
                    team_1_seed = int(
                        base_seeds.query("TEAM_ABB == @team_1")
                        .reset_index(drop=1)
                        .SEED[0][0]
                    )
                    team_2_seed = int(
                        base_seeds.query("TEAM_ABB == @team_2")
                        .reset_index(drop=1)
                        .SEED[0][0]
                    )
                    if team_1_seed < team_2_seed:
                        probs_dict = self.predict_series(
                            higher_seed_abb=team_1,
                            lower_seed_abb=team_2,
                            higher_already_won=team_1_already_won,
                            lower_already_won=team_2_already_won,
                            for_simulation=True,
                        )
                    elif team_1_seed > team_2_seed:
                        probs_dict = self.predict_series(
                            higher_seed_abb=team_2,
                            lower_seed_abb=team_1,
                            higher_already_won=team_2_already_won,
                            lower_already_won=team_1_already_won,
                            for_simulation=True,
                        )
                    elif this_round == 4:
                        team_1_record, team_2_record = curr_year.get_team_record(
                            team_1
                        ), curr_year.get_team_record(team_2)
                        if team_1_record > team_2_record:
                            probs_dict = self.predict_series(
                                higher_seed_abb=team_1,
                                lower_seed_abb=team_2,
                                higher_already_won=team_1_already_won,
                                lower_already_won=team_2_already_won,
                                for_simulation=True,
                                series_starts_in_how_many_games=-(
                                    team_1_already_won + team_2_already_won
                                ),
                            )
                        else:
                            probs_dict = self.predict_series(
                                higher_seed_abb=team_2,
                                lower_seed_abb=team_1,
                                higher_already_won=team_2_already_won,
                                lower_already_won=team_1_already_won,
                                for_simulation=True,
                                series_starts_in_how_many_games=-(
                                    team_1_already_won + team_2_already_won
                                ),
                            )
                    possible = []
                    probs = []
                    total_prob = dict()
                    for team, game_dict in probs_dict.items():
                        total_prob.update({team: 0})
                        for game, prob in game_dict.items():
                            possible.append(
                                (
                                    team,
                                    game,
                                )
                            )
                            probs.append(prob)
                            total_prob[team] += prob
                    occurs = choices(possible, probs)[0]
                    if occurs[0] == team_1:
                        winner, loser = team_1, team_2
                    else:
                        winner, loser = team_2, team_1
                    if team_1_already_won > team_2_already_won:
                        print(
                            f"{winner} wins {winner}-{loser} in {occurs[1]} with probability {round(total_prob[winner]*100, 2)}% (Currently {team_1_already_won}-{team_2_already_won} {team_1})"
                        )
                    else:
                        print(
                            f"{winner} wins {winner}-{loser} in {occurs[1]} with probability {round(total_prob[winner]*100, 2)}% (Currently {team_2_already_won}-{team_1_already_won} {team_2})"
                        )
                    seeds = pd.concat(
                        [
                            seeds,
                            pd.DataFrame({"SEED": [seed_reward], "TEAM_ABB": [winner]}),
                        ]
                    )
                    games_from_now = 3
            # if future round
            else:
                print(f"_____ROUND {this_round} SIMULATION_____")
                matchups_split = self.script[round_str]
                all_round_matchups = ["_".join(matchup) for matchup in matchups_split]
                current_round = dict()
                for matchup in all_round_matchups:
                    match = [
                        match for match in matchups_split if "_".join(match) == matchup
                    ][0]
                    current_round.update(
                        {
                            matchup: {
                                seeds.query("SEED == @match[0]")
                                .reset_index(drop=1)
                                .TEAM_ABB[0]: 0,
                                seeds.query("SEED == @match[1]")
                                .reset_index(drop=1)
                                .TEAM_ABB[0]: 0,
                            }
                        }
                    )
                for seed_reward, series_dict in current_round.items():
                    both_teams = list(series_dict.keys())
                    team_1, team_2 = both_teams[0], both_teams[1]
                    team_1_seed = int(
                        base_seeds.query("TEAM_ABB == @team_1")
                        .reset_index(drop=1)
                        .SEED[0][0]
                    )
                    team_2_seed = int(
                        base_seeds.query("TEAM_ABB == @team_2")
                        .reset_index(drop=1)
                        .SEED[0][0]
                    )
                    if team_1_seed < team_2_seed:
                        probs_dict = self.predict_series(
                            higher_seed_abb=team_1,
                            lower_seed_abb=team_2,
                            higher_already_won=0,
                            lower_already_won=0,
                            for_simulation=True,
                            series_starts_in_how_many_games=games_from_now,
                        )
                    elif team_1_seed > team_2_seed:
                        probs_dict = self.predict_series(
                            higher_seed_abb=team_2,
                            lower_seed_abb=team_1,
                            higher_already_won=0,
                            lower_already_won=0,
                            for_simulation=True,
                            series_starts_in_how_many_games=games_from_now,
                        )
                    elif this_round == 4:
                        team_1_record, team_2_record = curr_year.get_team_record(
                            team_1
                        ), curr_year.get_team_record(team_2)
                        if team_1_record > team_2_record:
                            probs_dict = self.predict_series(
                                higher_seed_abb=team_1,
                                lower_seed_abb=team_2,
                                higher_already_won=team_1_already_won,
                                lower_already_won=team_2_already_won,
                                for_simulation=True,
                                series_starts_in_how_many_games=games_from_now,
                            )
                        else:
                            probs_dict = self.predict_series(
                                higher_seed_abb=team_2,
                                lower_seed_abb=team_1,
                                higher_already_won=team_2_already_won,
                                lower_already_won=team_1_already_won,
                                for_simulation=True,
                                series_starts_in_how_many_games=games_from_now,
                            )
                    possible = []
                    probs = []
                    total_prob = dict()
                    for team, game_dict in probs_dict.items():
                        total_prob.update({team: 0})
                        for game, prob in game_dict.items():
                            possible.append(
                                (
                                    team,
                                    game,
                                )
                            )
                            probs.append(prob)
                            total_prob[team] += prob
                    occurs = choices(possible, probs)[0]
                    if occurs[0] == team_1:
                        winner, loser = team_1, team_2
                    else:
                        winner, loser = team_2, team_1
                    print(
                        f"{winner} wins {winner}-{loser} in {occurs[1]} with probability {round(total_prob[winner]*100, 2)}%"
                    )
                    seeds = pd.concat(
                        [
                            seeds,
                            pd.DataFrame({"SEED": [seed_reward], "TEAM_ABB": [winner]}),
                        ]
                    )
                    games_from_now += 7

    def get_probs_of_each_round(self):
        base_seeds = self.get_base_seeds()
        current_state = self.get_current_tourney_state()
        prob_of_seed = {row.SEED: {row.TEAM_ABB: 1} for _, row in base_seeds.iterrows()}
        for this_round, matchups in self.script.items():
            print(f"Loading {this_round} win probabilities...")
            if this_round not in current_state.keys():
                current_state.update({this_round: dict()})
            for matchup in matchups:
                seed_reward = "_".join(matchup)
                if this_round == "R4":
                    year_class = self.get_current_year_class.get("current")
                    team_1_record = year_class.get_team_record(matchup[0])
                    team_2_record = year_class.get_team_record(matchup[1])
                    if team_1_record > team_2_record:
                        higher_seed_probs = prob_of_seed[matchup[0]]
                        lower_seed_probs = prob_of_seed[matchup[1]]
                    else:
                        higher_seed_probs = prob_of_seed[matchup[1]]
                        lower_seed_probs = prob_of_seed[matchup[0]]
                else:
                    higher_seed_probs = prob_of_seed[matchup[0]]
                    lower_seed_probs = prob_of_seed[matchup[1]]
                prob_of_matchups_dict = {
                    f"{higher_seed_abb}_{lower_seed_abb}": higher_seed_probs[
                        higher_seed_abb
                    ]
                    * lower_seed_probs[lower_seed_abb]
                    for higher_seed_abb in higher_seed_probs
                    for lower_seed_abb in lower_seed_probs
                }
                prob_of_seed.update({seed_reward: dict()})
                for possible_matchup, prob_of_matchup in prob_of_matchups_dict.items():
                    higher_seed, lower_seed = possible_matchup[:3], possible_matchup[4:]
                    if seed_reward in current_state[this_round].keys():
                        current_state_of_matchup = current_state[this_round][
                            seed_reward
                        ]
                        higher_seed_won = current_state_of_matchup[higher_seed]
                        lower_seed_won = current_state_of_matchup[lower_seed]
                        if (higher_seed_won == 4) or (lower_seed_won == 4):
                            print(
                                f"{higher_seed}-{lower_seed} series was completed {higher_seed_won}-{lower_seed_won}"
                            )
                        else:
                            print(
                                f"{higher_seed}-{lower_seed} is currently in progress {higher_seed_won}-{lower_seed_won}"
                            )
                    else:
                        higher_seed_won, lower_seed_won = 0, 0
                    predict_series_dict = self.predict_series(
                        higher_seed,
                        lower_seed,
                        higher_already_won=higher_seed_won,
                        lower_already_won=lower_seed_won,
                        for_simulation=True,
                    )
                    prob_higher_seed_wins = np.sum(
                        list(predict_series_dict[higher_seed].values())
                    )
                    if higher_seed in prob_of_seed[seed_reward]:
                        prob_of_seed[seed_reward][higher_seed] += (
                            prob_higher_seed_wins * prob_of_matchup
                        )
                    else:
                        prob_of_seed[seed_reward].update(
                            {higher_seed: prob_higher_seed_wins * prob_of_matchup}
                        )
                    if lower_seed in prob_of_seed[seed_reward]:
                        prob_of_seed[seed_reward][lower_seed] += (
                            1 - prob_higher_seed_wins
                        ) * prob_of_matchup
                    else:
                        prob_of_seed[seed_reward].update(
                            {lower_seed: (1 - prob_higher_seed_wins) * prob_of_matchup}
                        )
            if this_round == "R4":
                round_probabilities = [
                    (team_abb, prob_of_seed[seed_reward][team_abb])
                    for team_abb in prob_of_seed[seed_reward]
                ]
                round_probabilities.sort(key=lambda x: x[1], reverse=True)
                print(f"_______NBA FINALS________")
                for team_prob in round_probabilities:
                    print(f"{team_prob[0]} wins: {round(team_prob[1] * 100, 2)}%")
                return
            winning_seeds_this_round = list(
                itertools.chain(*self.script[f"R{int(this_round[1]) + 1}"])
            )
            print(f"_______ROUND {this_round[1]}________")
            prob_of_round_dict = {}
            for team_abb in base_seeds.TEAM_ABB:
                total_prob = 0
                for winning_seed in winning_seeds_this_round:
                    try:
                        total_prob += prob_of_seed[winning_seed][team_abb]
                    except KeyError:
                        total_prob += 0
                prob_of_round_dict.update({team_abb: total_prob})
            round_probabilities = dict(
                sorted(prob_of_round_dict.items(), key=lambda item: -item[1])
            )
            for team_abb, prob in round_probabilities.items():
                print(f"{team_abb} wins: {round(prob * 100, 2)}%")
            print("\n \n \n")


# Define XGBoost model class:


class XGBoostModel:
    def __init__(self, injury_adjusted, avg_minutes_played_cutoff):
        self.injury_adjusted = injury_adjusted
        self.avg_minutes_played_cutoff = avg_minutes_played_cutoff
        self.train_set = train_class.get_training_dataset(
            injury_adjusted=self.injury_adjusted,
            avg_minutes_played_cutoff=self.avg_minutes_played_cutoff,
            force_update=False,
        )
        self.model = None
        self.best_params = None
        self.best_score = None

    def grid_search(self, param_grid):
        xgb_clf = xgb.XGBClassifier(objective="binary:logistic", n_jobs=-1)
        grid_search = GridSearchCV(
            estimator=xgb_clf, param_grid=param_grid, scoring="roc_auc", cv=5, verbose=0
        )
        y = self.train_set["HOME_WIN"]
        X = self.train_set.drop("HOME_WIN", axis=1)

        grid_search.fit(X, y)
        self.model = grid_search.best_estimator_
        self.best_params = grid_search.best_params_
        self.best_score = grid_search.best_score_
