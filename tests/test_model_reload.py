# -*- coding: utf-8 -*-
# @Project:final project

import unittest
from unittest.mock import patch
from objects.model_reload import model_retrain
from objects.model import XGBoostModel
import __main__

__main__.XGBoostModel = XGBoostModel

class TestModelRetrain(unittest.TestCase):

    def test_update_model_yes(self):
        with patch('builtins.input', return_value='Yes'):
            result = model_retrain()
        self.assertIsNone(result)

    def test_update_model_no(self):
        with patch('builtins.input', return_value='No'):
            result = model_retrain()
        self.assertIsNone(result)

    def test_no_pretrained_model(self):
        with patch('builtins.input', return_value='Yes'):
            result = model_retrain()
        self.assertIsNone(result)

    def test_invalid_user_input(self):
        with patch('builtins.input', return_value='Invalid'):
            with self.assertRaises(SystemExit):
                model_retrain()
