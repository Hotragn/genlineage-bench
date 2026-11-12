import unittest
from calc.evaluate import evaluate

class T(unittest.TestCase):
    def test_sub(self):
        self.assertEqual(evaluate("10 - 4"), 6.0)
        self.assertEqual(evaluate("10 - 4 - 1"), 5.0)
    def test_add(self):
        self.assertEqual(evaluate("1 + 2"), 3.0)
