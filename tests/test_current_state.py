# -*- coding: utf-8 -*-
# @Project:finalProject

import unittest
from unittest.mock import patch
from objects.current_state import current_state
import pandas as pd
class TestCurrentState(unittest.TestCase):
    def setUp(self):

        self.curr = current_state()

    def test_print_current_team_injuries(self):

        team_id = "1610612737" # Atlanta Hawks
        games_ahead_of_today = 0
        injuries = self.curr.print_current_team_injuries(team_id, games_ahead_of_today)
        assert isinstance(injuries, list)

    def test_get_current_max_playoff_seed_probs(self):
        max_prob_seeds = self.curr.get_current_max_playoff_seed_probs()
        assert isinstance(max_prob_seeds, dict)

    def test_get_base_seeds(self):
        base_seeds = self.curr.get_base_seeds()
        assert isinstance(base_seeds, pd.DataFrame)

    def test_get_current_tourney_state(self):
        tourney_state = self.curr.get_current_tourney_state()
        assert isinstance(tourney_state, dict)

    def test_get_playoff_picture_liklihood(self):
        playoff_prob = self.curr.get_playoff_picture_liklihood()
        assert isinstance(playoff_prob, dict)

    def test_predict_matchup(self):
        home_abb, away_abb = "LAL", "MIA"  # Los Angeles Lakers vs Miami Heat
        prob = self.curr.predict_matchup(home_abb, away_abb)
        assert isinstance(prob, float)





    def test_predict_series(self):
        higher_seed_abb = 'LAL'
        lower_seed_abb = 'GSW'
        higher_already_won = 2
        lower_already_won = 1
        series_starts_in_how_many_games = 3
        expected_outcomes = {
            higher_seed_abb: {
                4: 0.106864,
                5: 0.26518,
                6: 0.496616,
                7: 0.13134
            },
            lower_seed_abb: {
                4: 0.2025,
                5: 0.34389,
                6: 0.2916,
                7: 0.16201
            }
        }
        actual_outcomes = self.curr.predict_series(
            higher_seed_abb=higher_seed_abb,
            lower_seed_abb=lower_seed_abb,
            higher_already_won=higher_already_won,
            lower_already_won=lower_already_won,
            series_starts_in_how_many_games=series_starts_in_how_many_games,
            for_simulation=True
        )
        self.assertAlmostEqual(actual_outcomes[higher_seed_abb][4], expected_outcomes[higher_seed_abb][4], delta=0.001)
        self.assertAlmostEqual(actual_outcomes[higher_seed_abb][5], expected_outcomes[higher_seed_abb][5], delta=0.001)
        self.assertAlmostEqual(actual_outcomes[higher_seed_abb][6], expected_outcomes[higher_seed_abb][6], delta=0.001)
        self.assertAlmostEqual(actual_outcomes[higher_seed_abb][7], expected_outcomes[higher_seed_abb][7], delta=0.001)
        self.assertAlmostEqual(actual_outcomes[lower_seed_abb][4], expected_outcomes[lower_seed_abb][4], delta=0.001)
        self.assertAlmostEqual(actual_outcomes[lower_seed_abb][5], expected_outcomes[lower_seed_abb][5], delta=0.001)
        self.assertAlmostEqual(actual_outcomes[lower_seed_abb][6], expected_outcomes[lower_seed_abb][6], delta=0.001)
        self.assertAlmostEqual(actual_outcomes[lower_seed_abb][7], expected_outcomes[lower_seed_abb][7], delta=0.001)

        @patch.object(current_state, 'get_base_seeds')
        @patch.object(current_state, 'get_current_tourney_state')
        @patch.object(current_state, 'get_current_year_class')
        @patch.object(current_state, 'predict_series')
        def test_get_probs_of_each_round(self, mock_predict, mock_year_class, mock_tourney, mock_seeds):
            base_seeds = {'SEED': [1, 2], 'TEAM_ABB': ['AAA', 'BBB']}
            mock_seeds.return_value = base_seeds

            curr_state = {
                'R1': [('AAA', 'BBB')]
            }
            mock_tourney.return_value = curr_state

            team_record = {
                'AAA': 10,
                'BBB': 12
            }
            mock_year_class.get_team_record.side_effect = lambda team: team_record[team]
            mock_year_class.get.return_value = mock_year_class

            mock_predict.return_value = {
                'AAA': {
                    0: 0.4,
                    1: 0.6
                },
                'BBB': {
                    0: 0.5,
                    1: 0.5
                }
            }

            cs = current_state()
            cs.script = {'R1': [('AAA', 'BBB')]}
            cs.get_probs_of_each_round()

            self.assertEqual(mock_predict.call_count, 1)
            mock_predict.assert_called_with('AAA', 'BBB', higher_already_won=0, lower_already_won=0,
                                            for_simulation=True)
