# -*- coding: utf-8 -*-
# @Project:finalProject
# @email: 2997260832@qq.com
# @author: ShuYue
# @Created on 2023/4/29-21:59
import unittest
from unittest.mock import patch, MagicMock
from objects.trainer import training_dataset


class TestTrainingDataset(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.ds = training_dataset(since=2010)

    def test_load_year_data(self):
        self.assertEqual(len(self.ds.years_cache), len(range(2010, 2021)))

    def test_year(self):
        self.assertIsInstance(self.ds.year(2015), MagicMock)

    def test_load_train_data(self):
        self.ds.load_train_data(injury_adjusted=True, avg_minutes_played_cutoff=20)
        self.assertEqual(len(self.ds.training_sets_cache), len(range(2010, 2021)))
