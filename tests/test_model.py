# -*- coding: utf-8 -*-
# @Project:final project

import unittest
from mock import MagicMock, patch
from objects.model import XGBoostModel

class TestXGBoostModel(unittest.TestCase):

    def test_grid_search(self):
        # Instantiate the model with some arbitrary parameters for testing
        injury_adjusted = True
        avg_minutes_played_cutoff = 15
        train_class = MagicMock()
        train_set = MagicMock()
        train_class.get_training_dataset.return_value = train_set
        xgb_model = XGBoostModel(injury_adjusted, avg_minutes_played_cutoff, train_class)

        # Define parameter grid for grid search
        param_grid = {
            "learning_rate": [0.1, 0.05],
            "max_depth": [3, 5],
            "n_estimators": [50, 100]
        }

        # Mock GridSearchCV object and methods
        mock_gscv = MagicMock()
        mock_gscv.best_estimator_ = MagicMock()
        mock_gscv.best_params_ = MagicMock()
        mock_gscv.best_score_ = MagicMock()
        with patch("objects.model.GridSearchCV", return_value=mock_gscv):
            # Run grid search on training data and check that output is as expected
            xgb_model.grid_search(param_grid)
            train_class.get_training_dataset.assert_called_once_with(
                injury_adjusted=injury_adjusted,
                avg_minutes_played_cutoff=avg_minutes_played_cutoff,
                force_update=False
            )
            mock_gscv.fit.assert_called_once_with(train_set.drop("HOME_WIN", axis=1), train_set["HOME_WIN"])
            self.assertEqual(xgb_model.model, mock_gscv.best_estimator_)
            self.assertEqual(xgb_model.best_params, mock_gscv.best_params_)
            self.assertEqual(xgb_model.best_score, mock_gscv.best_score_)
