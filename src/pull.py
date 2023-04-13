nba_team_abbs = pd.DataFrame(teams.get_teams()).abbreviation

class year:
    def __init__(self, year):
        self.year = year
        self.season = str(self.year) + "-" + str(self.year-1999)
        self.game_data_cache = pd.DataFrame()
        self.playoff_game_data_cache = pd.DataFrame()
        self.playoff_boxes_cache = pd.DataFrame()
        self.regular_boxes_cache = pd.DataFrame()
        self.injured_cache = dict()
        self.playoff_player_info_cache = pd.DataFrame()
        self.regular_boxes_cache_only_played = pd.DataFrame()

    @property
    def playoff_player_info(self):
        if self.playoff_player_info_cache.empty:
            print("Loading player info for year for first time.")
            all_players = []
            for team_id in tqdm.tqdm(self.playoff_boxes.TEAM_ID.unique()):
                roster = endpoints.commonteamroster.CommonTeamRoster(team_id = team_id, season = self.season).get_data_frames()[0]
                all_players.append(roster)
                time.sleep(1)
            all_players = pd.concat(all_players)
            self.playoff_player_info_cache = all_players[["TeamID", "PLAYER_ID", "POSITION"]]
        return self.playoff_player_info_cache
    
    @property
    def game_data(self) -> None:
        """Set game data in object cache in long format."""
        if self.game_data_cache.shape[0] == 0:
            print("Loading resular season data for this year for the first time.")
            try:
                self.game_data_cache = endpoints.leaguegamefinder.LeagueGameFinder(season_type_nullable = SeasonType.regular, season_nullable = self.season).get_data_frames()[0].query("TEAM_ABBREVIATION in @nba_team_abbs")
            except JSONDecodeError:
                raise JSONDecodeError('NBA API Timeout. Try again later.')
            return self.game_data_cache
        if datetime.datetime.now().year in [self.year, self.year + 1]:
            print("Updating resular season game data.")
            try:
                self.game_data_cache = endpoints.leaguegamefinder.LeagueGameFinder(season_type_nullable = SeasonType.regular, season_nullable = self.season).get_data_frames()[0].query("TEAM_ABBREVIATION in @nba_team_abbs")
            except JSONDecodeError:
                raise JSONDecodeError('NBA API Timeout. Try again later.')
            return self.game_data_cache
        return self.game_data_cache
        

    @property
    def regular_boxes(self) -> None:
        """Set regular season player box summaries"""
        if self.regular_boxes_cache.shape[0] == 0:
            print("Loading regular season box data for this year for the first time.")
            try:
                pull = endpoints.PlayerGameLogs(season_type_nullable = SeasonType.regular, season_nullable = self.season).get_data_frames()[0].query("TEAM_ABBREVIATION in @nba_team_abbs")
                self.regular_boxes_cache_only_played = pull.copy()
                result = []
                for _, row in tqdm.tqdm(self.game_data[['TEAM_ID', 'GAME_ID']].iterrows()):
                    # loop through each player_id for the corresponding team
                    for player_id in self.get_team_rosters_from_regular_season()[row['TEAM_ID']]:
                        # create a copy of the row with a new column for the player_id
                        new_row = row.copy()
                        new_row['PLAYER_ID'] = player_id
                        result.append(new_row)
                result = pd.DataFrame(result)
                self.regular_boxes_cache = result.merge(pull, how = 'left', on = ['GAME_ID', 'TEAM_ID', 'PLAYER_ID'])
            except JSONDecodeError:
                raise JSONDecodeError('NBA API Timeout. Try again later.')
        elif datetime.datetime.now().year in [self.year, self.year + 1]:
            print("Updating resular season box data.")
            try:
                pull = endpoints.PlayerGameLogs(season_type_nullable = SeasonType.regular, season_nullable = self.season).get_data_frames()[0].query("TEAM_ABBREVIATION in @nba_team_abbs")
                self.regular_boxes_cache_only_played = pull.copy()
                result = []
                for _, row in tqdm.tqdm(self.game_data[['TEAM_ID', 'GAME_ID']].iterrows()):
                    # loop through each player_id for the corresponding team
                    for player_id in self.get_team_rosters_from_regular_season()[row['TEAM_ID']]:
                        # create a copy of the row with a new column for the player_id
                        new_row = row.copy()
                        new_row['PLAYER_ID'] = player_id
                        result.append(new_row)
                result = pd.DataFrame(result)
                self.regular_boxes_cache = result.merge(pull, how = 'left', on = ['GAME_ID', 'TEAM_ID', 'PLAYER_ID'])
            except JSONDecodeError:
                raise JSONDecodeError('NBA API Timeout. Try again later.')
        return self.regular_boxes_cache

    @property
    def regular_boxes_summary(self):
        regular_boxes = self.regular_boxes
        regular_boxes_summary = regular_boxes[['TEAM_ID', 'PLAYER_ID', 'MIN', 'PTS', 'FGM', 'FGA', 'FG_PCT', 
                                                'FG3M', 'FG3A', 'FG3_PCT', 'FTM', 'FTA', 'FT_PCT', 'OREB', 'DREB',
                                                'REB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'PLUS_MINUS']].fillna(0).groupby(["PLAYER_ID", "TEAM_ID"]).agg(['mean']).reset_index()
        regular_boxes_summary.columns = regular_boxes_summary.columns.map(lambda x: "_".join(x))
        regular_boxes_summary = regular_boxes_summary.rename(columns = {'PLAYER_ID_' : 'PLAYER_ID', 'TEAM_ID_' : 'TEAM_ID'}).copy()
        return regular_boxes_summary
    
    @property
    def playoff_game_data(self) -> None:
        """Set playoff game data in object cache in wide format."""
        if self.playoff_game_data_cache.shape[0] == 0:
            print("Loading playoff game data for this year for the first time.")
            try:
                all_games = endpoints.leaguegamefinder.LeagueGameFinder(season_type_nullable = SeasonTypePlayoffs.playoffs, 
                                              season_nullable = self.season).get_data_frames()[0].query("TEAM_ABBREVIATION in @nba_team_abbs")
            except JSONDecodeError:
                raise JSONDecodeError('NBA API Timeout. Try again later.')
        elif datetime.datetime.now().year in [self.year, self.year + 1]:
            print("Updating playoff game data.")
            try:
                all_games = endpoints.leaguegamefinder.LeagueGameFinder(season_type_nullable = SeasonTypePlayoffs.playoffs, 
                                              season_nullable = self.season).get_data_frames()[0].query("TEAM_ABBREVIATION in @nba_team_abbs")
            except JSONDecodeError:
                raise JSONDecodeError('NBA API Timeout. Try again later.')
        else:
            return self.playoff_game_data_cache
        all_games['HOME_AWAY'] = ["H" if x == 1 else "A" for x in all_games.MATCHUP.str.contains("vs")]
        all_games = all_games[['GAME_ID', 'GAME_DATE', 'HOME_AWAY', 'TEAM_ID', 'TEAM_ABBREVIATION', 'PTS', 'FGM', 'FGA', 'FG_PCT', 
                                        'FG3M', 'FG3A', 'FG3_PCT', 'FTM', 'FTA', 'FT_PCT', 'OREB', 'DREB',
                                        'REB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'PLUS_MINUS']].copy()
        all_games = all_games.pivot(index='GAME_ID', columns='HOME_AWAY').reset_index()
        all_games.columns = all_games.columns.map(lambda x: "_".join(x))
        all_games["OUTCOME"] = [0 if PLUS_MINUS_H < 0 else 1 for PLUS_MINUS_H in all_games.PLUS_MINUS_H]
        all_games = all_games.rename(columns = {'GAME_DATE_H' : 'GAME_DATE', "GAME_ID_" : "GAME_ID"}).drop(["GAME_DATE_A"], axis = 1).copy()
        self.playoff_game_data_cache = all_games.replace({'NOH': 'NOP',
                               'NOK': 'NOP',
                               'NOH': 'NOP',
                               'NJN': 'BKN',
                               'SEA': 'OKC',
                               'VAN': 'MEM',
                               'KCK': 'SAC',
                               'SDC': 'LAC',
                               'WSB': 'WAS',
                               'PHO': 'PHX'}, regex=True).query("TEAM_ABBREVIATION_H in @nba_team_abbs & TEAM_ABBREVIATION_A in @nba_team_abbs")
        return self.playoff_game_data_cache

    @property
    def playoff_boxes(self):
        """Load player boxes for all playoff games."""
        if self.playoff_boxes_cache.shape[0] == 0:
            print("Loading playoff box data for this year for the first time.")
            try:
                post_boxes = endpoints.PlayerGameLogs(season_type_nullable = SeasonTypePlayoffs.playoffs, 
                                              season_nullable = self.season).get_data_frames()[0].query("TEAM_ABBREVIATION in @nba_team_abbs")
            except JSONDecodeError:
                raise JSONDecodeError('NBA API Timeout. Try again later.')
        elif datetime.datetime.now().year in [self.year, self.year + 1]:
            print("Updating playoff box season game data.")
            try:
                post_boxes = endpoints.PlayerGameLogs(season_type_nullable = SeasonTypePlayoffs.playoffs, 
                                              season_nullable = self.season).get_data_frames()[0].query("TEAM_ABBREVIATION @nba_team_abbs")
            except JSONDecodeError:
                raise JSONDecodeError('NBA API Timeout. Try again later.')
        else:
            return self.playoff_boxes_cache 
        self.playoff_boxes_cache = post_boxes[['GAME_ID', 'TEAM_ID', 'PLAYER_ID', 'GAME_DATE', 'MIN', 'PTS', 'FGM', 'FGA', 'FG_PCT', 
                                                'FG3M', 'FG3A', 'FG3_PCT', 'FTM', 'FTA', 'FT_PCT', 'OREB', 'DREB',
                                                'REB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'PLUS_MINUS']]
        return self.playoff_boxes_cache 
            

    def get_regular_season_summary_stats(self):
        """Get team regular season summary statistics for all teams."""
        summary = self.game_data[['TEAM_ABBREVIATION', 'PTS', 'FGM', 'FGA', 'FG_PCT', 
                                  'FG3M', 'FG3A', 'FG3_PCT', 'FTM', 'FTA', 'FT_PCT', 'OREB', 'DREB',
                                  'REB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'PLUS_MINUS']].groupby('TEAM_ABBREVIATION').fillna(0).agg(['mean']).reset_index()
        summary.columns = summary.columns.map(lambda x: "_".join(x))
        summary = summary.rename(columns = {'TEAM_ABBREVIATION_' : 'TEAM_ABBREVIATION'}).copy()
        summary_filtered = summary.replace({'NOH': 'NOP',
                               'NOK': 'NOP',
                               'NOH': 'NOP',
                               'NJN': 'BKN',
                               'SEA': 'OKC',
                               'VAN': 'MEM',
                               'KCK': 'SAC',
                               'SDC': 'LAC',
                               'WSB': 'WAS',
                               'PHO': 'PHX'}, regex=True).query("TEAM_ABBREVIATION in @nba_team_abbs")
        return(summary_filtered)

    def get_playoff_results_up_to_date(self, date : str): # Input string as "%Y-%m-%d"
        return self.playoff_game_data.query("GAME_DATE < @date")

    def get_team_rosters_from_regular_season(self):
        """Organize dictionary where keys are team_ids and items are lists of player_ids."""
        if self.regular_boxes_cache_only_played.empty:
            load = self.regular_boxes
        rosters_df = self.regular_boxes_cache_only_played[['PLAYER_ID', 'TEAM_ID']].drop_duplicates()
        rosters_dict = {team: players.tolist() for team, players in rosters_df.groupby('TEAM_ID')['PLAYER_ID']}
        return(rosters_dict)
        
    def get_players_played_in_each_playoff_game(self):
        """Organize nested dictionary where outer key is team_id inner key is game_date and item is list of player_ids."""
        played = self.playoff_boxes[["TEAM_ID", "PLAYER_ID", "GAME_ID"]]
        nested_dict = {team : dict() for team in played.TEAM_ID.unique()}
        for team in nested_dict.keys():
            played_team = played.query("TEAM_ID == @team")
            nested_dict[team].update({game_id:players.tolist() for game_id, players in played_team.groupby('GAME_ID')['PLAYER_ID']})
        return nested_dict

    @property
    def sit_or_injured_playoff(self):
        """Gets whether players sat on each playoff game date for year in nested dict."""
        if datetime.datetime.now().year in [self.year + 1]:
            raise ValueError("sit_or_injured playoff property is only to be used on past seasons. Use current_injured() funciton instead")
        if len(self.injured_cache) == 0:
            roster_dict = self.get_team_rosters_from_regular_season()
            played_dict = self.get_players_played_in_each_playoff_game()
            injury_dict = {
                team: {
                    game_id: [player for player in roster_dict[team] if player not in played_dict.get(team, {}).get(game_id, [])]
                    for game_id in played_dict.get(team, {}).keys()
                }
                for team in roster_dict.keys()
            }
            self.injured_cache = injury_dict
        return self.injured_cache
    
    def reweight_replacements_for_missing_player(self, possible_replacement_player_ids, remove_injured, injured_player_id):
        """Reweights replacement players for ONE missing player"""
        possile_replacement_box_summary = self.regular_boxes_summary.query("PLAYER_ID in @possible_replacement_player_ids").sort_values(by = "MIN_mean", ascending=False)
        min_diff = self.regular_boxes_summary.query("PLAYER_ID == @injured_player_id").reset_index(drop = 0).MIN_mean[0]
        max_minutes = 30
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
                    updated_stats = pd.DataFrame(row).T.drop(['PLAYER_ID', 'TEAM_ID', 'FG_PCT_mean', 'FG3_PCT_mean', 'FT_PCT_mean', 'PLUS_MINUS_mean'], 
                                                        axis = 1).mul(prop_orig_time, axis=0).copy()
                    updated_stats['FG_PCT_mean'] = updated_stats.FGM_mean / updated_stats.FGA_mean
                    updated_stats['FG3_PCT_mean'] = updated_stats.FG3M_mean / updated_stats.FG3A_mean
                    updated_stats['FT_PCT_mean'] = updated_stats.FTM_mean / updated_stats.FTA_mean
                    updated_stats['PLAYER_ID'] = row.PLAYER_ID
                    updated_stats['TEAM_ID'] = row.TEAM_ID
                    replacement_df.append(updated_stats)
                    max_minutes += 1
        replacement_df = pd.concat(replacement_df)
        if min_diff > 0:
            raise UserWarning(f"Warning: Not enough eligible players on bench to account for all injuries with full 40 minutes of play for injury_id {injured_player_id}.")
        return replacement_df

    def reweight_stats(self, team_id, game_id, top_n_players = 10):
        """Get injury reweighted predicted stats."""
        injured = self.sit_or_injured_playoff[team_id][game_id]
        team_boxes = self.regular_boxes_summary.query("TEAM_ID == @team_id")
        team_boxes = team_boxes.merge(self.playoff_player_info, how = 'left', on = "PLAYER_ID").sort_values(by = "MIN_mean", ascending=False).copy()
        injured = team_boxes[:top_n_players].query("PLAYER_ID in @injured").reset_index(drop = 1).PLAYER_ID.tolist()
        remove_injured = team_boxes.query("PLAYER_ID not in @injured")
        for injured_player_id in injured:
            try:
                injured_pos = self.playoff_player_info.query("PLAYER_ID == @injured_player_id").reset_index(drop = 1).POSITION[0]
            except KeyError:
                continue  # player is no longer on roster
            possible_replacement_player_ids = self.playoff_player_info.query("TeamID == @team_id & (POSITION in @injured_pos | @injured_pos in POSITION)").reset_index(drop = 1).PLAYER_ID.tolist()
            replacement_df = self.reweight_replacements_for_missing_player(possible_replacement_player_ids = possible_replacement_player_ids, 
                                                                           remove_injured = remove_injured, injured_player_id = injured_player_id)
            replaced_player_ids = replacement_df.PLAYER_ID.tolist()
            remove_injured = pd.concat([remove_injured.query("PLAYER_ID not in @replaced_player_ids"), replacement_df])
        remove_injured = pd.DataFrame(remove_injured.sum(axis = 0, numeric_only=True)).T
        return remove_injured.drop(["MIN_mean", "TeamID", "TEAM_ID", "PLAYER_ID"], axis = 1)
            

    def get_injury_adjusted_features(self, game_id):
        """Return summary statistics for team under same injury conditions."""
        game = self.playoff_game_data.query("GAME_ID == @game_id")
        if game.empty:
            raise IndexError("Game requested is not a valid playoff game for this year.")
        home_team = game.reset_index(drop = 1).TEAM_ID_H[0]
        away_team = game.reset_index(drop = 1).TEAM_ID_A[0]
        home_reweighted =self.reweight_stats(team_id = home_team, game_id = game_id).add_suffix('_H')
        away_reweighted =self.reweight_stats(team_id = away_team, game_id = game_id).add_suffix('_A')
        adjusted_df = pd.concat([home_reweighted, away_reweighted], axis = 1)
        return adjusted_df

    def get_train_for_all_playoff_games(self):
        """Return dataframe of all adjusted features and game outcomes for this year."""
        features = []
        for _, row in self.playoff_game_data.iterrows():
            feature = self.get_injury_adjusted_features(game_id = row.GAME_ID)
            feature.HOME_WIN = row.OUTCOME
            features.append(feature)
        return pd.concat(features)