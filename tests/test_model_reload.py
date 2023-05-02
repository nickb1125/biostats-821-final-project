# -*- coding: utf-8 -*-
# @Project:final project
# @email: 2997260832@qq.com
# @author: ShuYue
# @Created on 2023/4/28-9:57
import unittest
from unittest.mock import patch
from objects.model_reload import model_retrain


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
