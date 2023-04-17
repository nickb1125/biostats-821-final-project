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


def scrape_current_nba_injuries():
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
        when_back.replace("Expected to be out until at least", "")
        for when_back in df.EXPECTED_WHEN_BACK
    ]
    return df.merge(player_ids, on="PLAYER_NAME", how="left")


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
                time.sleep(1)
            all_players = pd.concat(all_players)
            self.roster_info_cache = all_players[
                ["TeamID", "PLAYER_ID", "POSITION"]
            ].rename({"TeamID": "TEAM_ID"}, axis=1)
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
            time.sleep(1)
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
            time.sleep(1)
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
            time.sleep(1)
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
            time.sleep(1)
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
            time.sleep(1)
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
            time.sleep(1)
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
            time.sleep(1)
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
            time.sleep(1)
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
        while (min_diff > 0) & (max_minutes <= 40):
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
            raise UserWarning(
                f"Warning: Not enough eligible players on bench to account for all injuries with full 40 minutes of play for injury_id {injured_player_id}."
            )
        return replacement_df

    def reweight_stats(self, team_id, game_id, avg_minutes_played_cutoff):
        """Get injury reweighted predicted stats."""
        if game_id == 0:
            injured = [
                player_id
                for player_id in scrape_current_nba_injuries().PLAYER_ID
                if not math.isnan(player_id)
            ]
        else:
            injured = self.sit_or_injured_playoff[team_id][game_id]
        on_roster_still = self.get_team_rosters_from_regular_season()[team_id]
        injured = (
            self.regular_boxes_summary.query(
                "(TEAM_ID == @team_id) & (PLAYER_ID in @injured) & (MIN_mean > @avg_minutes_played_cutoff) & (PLAYER_ID in @on_roster_still)"
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
    ):
        if injury_adjusted:
            home_reweighted = (
                self.reweight_stats(
                    team_id=home_team,
                    game_id=game_id,
                    avg_minutes_played_cutoff=avg_minutes_played_cutoff,
                )
                .query("MIN_mean >= @avg_minutes_played_cutoff")
                .drop(["MIN_mean", "PLAYER_ID"], axis=1)
                .add_suffix("_H")
                .rename(columns=lambda x: x.replace("_mean", ""))
            )
            depth_at_cutoff = home_reweighted.shape[0]
            home_reweighted = (
                home_reweighted.agg(["mean", "sum", "median", "max", "min"])
                .stack()
                .to_frame()
                .T
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
                )
                .query("MIN_mean >= @avg_minutes_played_cutoff")
                .drop(["MIN_mean", "PLAYER_ID"], axis=1)
                .add_suffix("_A")
                .rename(columns=lambda x: x.replace("_mean", ""))
            )
            depth_at_cutoff = away_reweighted.shape[0]
            away_reweighted = (
                away_reweighted.agg(["mean", "sum", "median", "max", "min"])
                .stack()
                .to_frame()
                .T
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
                home_reweighted.agg(["mean", "sum", "median", "max", "min"])
                .stack()
                .to_frame()
                .T
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
                away_reweighted.agg(["mean", "sum", "median", "max", "min"])
                .stack()
                .to_frame()
                .T
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
        )
        return features

    def get_features_for_upcoming(
        self, home_team, away_team, injury_adjusted, avg_minutes_played_cutoff
    ):
        """Return model features for upcoming game."""
        features = self.feature_creator(
            home_team=home_team,
            away_team=away_team,
            game_id=0,
            injury_adjusted=injury_adjusted,
            avg_minutes_played_cutoff=avg_minutes_played_cutoff,
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
            self.training_sets_cache.update(
                {
                    year_load: {
                        f"injury_adjusted = {injury_adjusted}, avg_minutes_played_cutoff = {avg_minutes_played_cutoff}": training
                    }
                }
            )


class current_state:
    def __init__(self):
        if datetime.datetime.now().month <= 8:
            self.year = datetime.datetime.now().year - 1
        else:
            self.year = datetime.datetime.now().year
        self.created_on = datetime.datetime.now()
        self.year_class = dict()
        self.injury_adjusted = True  # FIX THIS WHEN WILL TRAINS MODEL HYPTERPARAMTER
        self.avg_minutes_played_cutoff = (
            20  # FIX THIS WHEN WILL TRAINS MODEL HYPTERPARAMTER
        )
        self.model = "INSERT MODEL HERE"

    @property
    def get_current_year_class(self):
        if len(self.year_cache.keys()) == 0:
            self.year_class = year(self.year)
        return self.year_cache

    def predict_matchup(self, model, home_abb, away_abb):
        """Predicts upcoming matchup."""
        features = self.year_cache.get("current").get_features_for_upcoming(
            home_team=home_abb,
            away_team=away_abb,
            injury_adjusted=self.injury_adjusted,
            avg_minutes_played_cutoff=self.avg_minutes_played_cutoff,
        )
        prob = self.model.predict_proba(features)
        return prob[1]  # Return home win probability

    def predict_playoff_picture(self):
        """Return table of probabilities for each playoff round for each team."""
        pass

    def simulate_playoffs_from_this_point():
        """Simulates current playoff picture."""
        pass
