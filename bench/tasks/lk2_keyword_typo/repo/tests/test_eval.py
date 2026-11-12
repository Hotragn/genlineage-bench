import unittest
from calc.evaluate import evaluate

class T(unittest.TestCase):
    def test_true_literal(self):
        self.assertEqual(evaluate("true + 1"), 2.0)
    def test_false_literal(self):
        self.assertEqual(evaluate("false * 3"), 0.0)
