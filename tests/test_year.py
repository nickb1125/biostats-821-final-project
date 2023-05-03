import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import pandas as pd
from objects.year import year
from nba_api.stats.library.parameters import SeasonType, SeasonTypePlayoffs
import nba_api.stats

class TestYear(unittest.TestCase):

    def setUp(self):
        self.year = year(2022)
        self.stats = nba_api.stats

    def test_roster_info(self):
        self.assertTrue(self.year.roster_info_cache.empty)
        roster_mock = MagicMock(return_value=pd.DataFrame({
            "TeamID": [1],
            "PLAYER_ID": [1],
            "POSITION": ["PG"]
        }))
        with patch("endpoints.commonteamroster.CommonTeamRoster", roster_mock):
            roster_info = self.year.roster_info
            roster_mock.assert_called_once_with(team_id=1, season="2022-23")
            self.assertFalse(roster_info.empty)
            self.assertIsInstance(roster_info, pd.DataFrame)
            self.assertIn("TEAM_ID", roster_info.columns)
            self.assertIn("PLAYER_ID", roster_info.columns)
            self.assertIn("POSITION", roster_info.columns)

    def test_game_data(self):
        self.assertTrue(self.year.game_data_cache.empty)
        game_data_mock = MagicMock(return_value=pd.DataFrame({
            "GAME_ID": [1, 2],
            "TEAM_ID": [1, 2],
            "TEAM_ABBREVIATION": ["LAC", "LAL"],
            "PTS": [100, 110]
        }))
        with patch("endpoints.leaguegamefinder.LeagueGameFinder", game_data_mock):
            game_data = self.year.game_data
            game_data_mock.assert_called_once_with(
                season_type_nullable=SeasonType.regular, season_nullable="2022-23"
            )
            self.assertFalse(game_data.empty)
            self.assertIsInstance(game_data, pd.DataFrame)
            self.assertIn("GAME_ID", game_data.columns)
            self.assertIn("PTS_H", game_data.columns)
            self.assertIn("TEAM_ID_A", game_data.columns)

    def test_regular_boxes(self):
        self.assertTrue(self.year.regular_boxes_cache.empty)
        boxes_mock = MagicMock(return_value=pd.DataFrame({
            "GAME_ID": [1, 1],
            "PLAYER_ID": [1, 2],
            "PTS": [10, 20]
        }))
        with patch("endpoints.PlayerGameLogs", boxes_mock):
            boxes = self.year.regular_boxes
            boxes_mock.assert_called_once_with(
                season_type_nullable=SeasonType.regular, season_nullable="2022-23"
            )
            self.assertFalse(boxes.empty)
            self.assertIsInstance(boxes, pd.DataFrame)
            self.assertIn("GAME_ID", boxes.columns)
            self.assertIn("PTS", boxes.columns)


    def test_regular_boxes_summary(self):
        # Test if the returned dataframe has the correct columns
        self.assertListEqual(list(self.stats.regular_boxes_summary.columns),
                             ['PLAYER_ID', 'TEAM_ID', 'MIN_mean', 'PTS_mean', 'FGM_mean', 'FGA_mean',
                              'FG_PCT_mean', 'FG3M_mean', 'FG3A_mean', 'FG3_PCT_mean', 'FTM_mean', 'FTA_mean',
                              'FT_PCT_mean', 'OREB_mean', 'DREB_mean', 'REB_mean', 'AST_mean', 'STL_mean',
                              'BLK_mean', 'TOV_mean', 'PF_mean', 'PLUS_MINUS_mean'])

    def test_playoff_game_data(self):
        # Test if the returned dataframe is not empty
        self.assertFalse(self.stats.playoff_game_data.empty)

        # Test if the returned dataframe contains the expected columns
        self.assertListEqual(list(self.stats.playoff_game_data.columns),
                             ['GAME_ID_', 'TEAM_ABBREVIATION_A', 'TEAM_ID_A', 'PTS_A', 'FGM_A', 'FGA_A', 'FG_PCT_A',
                              'FG3M_A', 'FG3A_A', 'FG3_PCT_A', 'FTM_A', 'FTA_A', 'FT_PCT_A', 'OREB_A', 'DREB_A',
                              'REB_A', 'AST_A', 'STL_A', 'BLK_A', 'TOV_A', 'PF_A', 'PLUS_MINUS_A',
                              'TEAM_ABBREVIATION_H',
                              'TEAM_ID_H', 'PTS_H', 'FGM_H', 'FGA_H', 'FG_PCT_H', 'FG3M_H', 'FG3A_H', 'FG3_PCT_H',
                              'FTM_H', 'FTA_H', 'FT_PCT_H', 'OREB_H', 'DREB_H', 'REB_H', 'AST_H', 'STL_H',
                              'BLK_H', 'TOV_H', 'PF_H', 'PLUS_MINUS_H', 'OUTCOME'])

    def test_playoff_boxes(self):
        # Test if the returned dataframe is not empty
        self.assertFalse(self.stats.playoff_boxes.empty)

        # Test if the returned dataframe contains the expected columns
        self.assertListEqual(list(self.stats.playoff_boxes.columns),
                             ['GAME_ID', 'TEAM_ID', 'PLAYER_ID', 'GAME_DATE', 'MIN', 'PTS', 'FGM', 'FGA',
                              'FG_PCT', 'FG3M', 'FG3A', 'FG3_PCT', 'FTM', 'FTA', 'FT_PCT', 'OREB', 'DREB',
                              'REB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'PLUS_MINUS', 'Regular_Season_Play_Time_Rank'])

    def test_get_playoff_results_up_to_date(self):
        date = datetime.now().strftime("%Y-%m-%d")  # Current date
        # Test if the returned dataframe is not empty
        self.assertFalse(self.stats.get_playoff_results_up_to_date(date).empty)

    def test_get_team_rosters_from_regular_season(self):
        rosters_dict = self.year.get_team_rosters_from_regular_season()
        self.assertIsInstance(rosters_dict, dict)
        for team, players in rosters_dict.items():
            self.assertIsInstance(team, int)
            self.assertIsInstance(players, list)
            for player in players:
                self.assertIsInstance(player, int)

    def test_get_players_played_in_each_playoff_game(self):
        played_dict = self.year.get_players_played_in_each_playoff_game()
        self.assertIsInstance(played_dict, dict)
        for team, games in played_dict.items():
            self.assertIsInstance(team, int)
            self.assertIsInstance(games, dict)
            for game_id, players in games.items():
                self.assertIsInstance(game_id, str)
                self.assertIsInstance(players, list)
                for player in players:
                    self.assertIsInstance(player, int)

    def test_reweight_replacements_for_missing_player(self):
        player_ids = [1, 2, 3, 4, 5]
        remove_injured = pd.DataFrame({'PLAYER_ID': [1], 'TEAM_ID': [1]})
        injured_player_id = 1
        replacement_df = self.year.reweight_replacements_for_missing_player(player_ids, remove_injured,
                                                                            injured_player_id)
        self.assertIsInstance(replacement_df, pd.DataFrame)
        for col in ['MIN_mean', 'FGM_mean', 'FGA_mean', 'FG3M_mean', 'FG3A_mean', 'FTM_mean', 'FTA_mean', 'OREB_mean',
                    'DREB_mean', 'REB_mean', 'AST_mean', 'STL_mean', 'BLK_mean', 'TOV_mean', 'PF_mean']:
            self.assertIn(col, replacement_df.columns)
        for player in replacement_df['PLAYER_ID']:
            self.assertIsInstance(player, int)

    def test_get_team_record(self):
        team_abb = 'BOS'
        record = self.year.get_team_record(team_abb)
        self.assertIsInstance(record, float)
        self.assertGreaterEqual(record, 0)
        self.assertLessEqual(record, 1)

    def test_reweight_stats(self):
        team_id = 1610612751  # Brooklyn Nets
        game_id = 0
        avg_minutes_played_cutoff = 30
        games_ahead_of_today = 0
        stats_df = self.year.reweight_stats(team_id, game_id, avg_minutes_played_cutoff, games_ahead_of_today)
        self.assertIsInstance(stats_df, pd.DataFrame)

    def test_get_regular_season_summary_stats_unadjusted(self):
        team_id = 1610612760  # Oklahoma City Thunder
        summary_stats_df = self.year.get_regular_season_summary_stats_unadjusted(team_id)
        self.assertIsInstance(summary_stats_df, pd.DataFrame)

    def test_get_home_win_percentage(self):
        team_id = 1610612737  # Atlanta Hawks
        home_win_percentage = self.year.get_home_win_percentage(team_id)
        self.assertIsInstance(home_win_percentage, float)

    def test_get_away_win_percentage(self):
        team_id = 1610612740  # New Orleans Pelicans
        away_win_percentage = self.year.get_away_win_percentage(team_id)
        self.assertIsInstance(away_win_percentage, float)

    def test_feature_creator(self):
        home_team = 1610612766
        away_team = 1610612764
        game_id = '0042200313'
        injury_adjusted = True
        avg_minutes_played_cutoff = 10.0
        games_ahead_of_today = 0

        expected_columns = ['AGE_mean_H', 'AGE_mean_A', 'FG_PCT_mean_H', 'FG_PCT_mean_A', 'FT_PCT_mean_H',
                            'FT_PCT_mean_A', 'FG3_PCT_mean_H', 'FG3_PCT_mean_A', 'REB_mean_H', 'REB_mean_A',
                            'AST_mean_H', 'AST_mean_A', 'STL_mean_H', 'STL_mean_A', 'BLK_mean_H', 'BLK_mean_A',
                            'TOV_mean_H', 'TOV_mean_A', 'PF_mean_H', 'PF_mean_A', 'PTS_mean_H', 'PTS_mean_A',
                            'PLUS_MINUS_mean_H', 'PLUS_MINUS_mean_A', 'depth_at_cutoff_H', 'home_win_percentage',
                            'depth_at_cutoff_A', 'road_win_percentage']

        features = self.year.feature_creator(home_team, away_team, game_id, injury_adjusted,
                                             avg_minutes_played_cutoff, games_ahead_of_today)

        # check if the output dataframe has the expected columns
        self.assertListEqual(list(features.columns), expected_columns)

        # check if the output dataframe has correct dimensions
        self.assertEqual(features.shape, (1, len(expected_columns)))

    def test_get_train_for_all_playoff_games(self):
        injury_adjusted = True
        avg_minutes_played_cutoff = 10.0

        # check if the output dataframe has expected columns
        expected_columns = ['AGE_mean_H', 'AGE_mean_A', 'FG_PCT_mean_H', 'FG_PCT_mean_A', 'FT_PCT_mean_H',
                            'FT_PCT_mean_A', 'FG3_PCT_mean_H', 'FG3_PCT_mean_A', 'REB_mean_H', 'REB_mean_A',
                            'AST_mean_H', 'AST_mean_A', 'STL_mean_H', 'STL_mean_A', 'BLK_mean_H', 'BLK_mean_A',
                            'TOV_mean_H', 'TOV_mean_A', 'PF_mean_H', 'PF_mean_A', 'PTS_mean_H', 'PTS_mean_A',
                            'PLUS_MINUS_mean_H', 'PLUS_MINUS_mean_A', 'depth_at_cutoff_H', 'home_win_percentage',
                            'depth_at_cutoff_A', 'road_win_percentage', 'HOME_WIN']

        train_data = self.year.get_train_for_all_playoff_games(injury_adjusted, avg_minutes_played_cutoff)

        # check if the output dataframe has the expected columns
        self.assertListEqual(list(train_data.columns), expected_columns)

        # check if the output dataframe has the expected dimensions
        self.assertTrue(train_data.shape[0] > 0)
        self.assertEqual(len(train_data), self.year.playoff_game_data.shape[0])

if __name__ == "__main__":
    unittest.main()
