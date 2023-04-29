# -*- coding: utf-8 -*-
# @Project:final project
# @email: 2997260832@qq.com
# @author: ShuYue
# @Created on 2023/4/28-9:57
import unittest
import datetime
import pandas as pd
from objects.helper import scrape_current_nba_injuries, scrape_nba_playoff_projections

class TestMyModule(unittest.TestCase):
    def test_scrape_current_nba_injuries(self):
        injuries = scrape_current_nba_injuries(games_ahead_of_now=1)
        self.assertIsInstance(injuries, pd.DataFrame)
        self.assertTrue(all(injuries.columns == ["PLAYER_NAME", "POSITION", "UPDATED", "TYPE", "EXPECTED_WHEN_BACK", "PLAYER_ID"]))
        self.assertFalse(injuries.isnull().values.any())
        self.assertGreater(len(injuries), 0)

        injuries = scrape_current_nba_injuries(games_ahead_of_now=10)
        expected_date = datetime.datetime.now() + datetime.timedelta(days=20)
        self.assertTrue(all(injuries["EXPECTED_WHEN_BACK"] > expected_date))

    def test_scrape_nba_playoff_projections(self):
        projections = scrape_nba_playoff_projections()
        self.assertIsInstance(projections, dict)
        self.assertIn("West", projections.keys())
        self.assertIn("East", projections.keys())

        west_data = projections["West"]
        self.assertIsInstance(west_data, pd.DataFrame)
        self.assertTrue(all(west_data.columns == ["TEAM_NAME", "1_SEED_PROB", "2_SEED_PROB", "3_SEED_PROB", "4_SEED_PROB", "5_SEED_PROB", "6_SEED_PROB", "7_SEED_PROB", "8_SEED_PROB", "TEAM_ID"]))
        self.assertFalse(west_data.isnull().values.any())
        self.assertGreater(len(west_data), 0)

        east_data = projections["East"]
        self.assertIsInstance(east_data, pd.DataFrame)
        self.assertTrue(all(east_data.columns == ["TEAM_NAME", "1_SEED_PROB", "2_SEED_PROB", "3_SEED_PROB", "4_SEED_PROB", "5_SEED_PROB", "6_SEED_PROB", "7_SEED_PROB", "8_SEED_PROB", "TEAM_ID"]))
        self.assertFalse(east_data.isnull().values.any())
        self.assertGreater(len(east_data), 0)

if __name__ == "__main__":
    unittest.main()
