import unittest
from calc.evaluate import evaluate

class T(unittest.TestCase):
    def test_decimals(self):
        self.assertEqual(evaluate("1.5 * 2"), 3.0)
        self.assertEqual(evaluate("0.25 + 0.5"), 0.75)
    def test_ints(self):
        self.assertEqual(evaluate("2 * (3 + 4)"), 14.0)
