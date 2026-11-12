import unittest
from app import settings, flags, retry

class T(unittest.TestCase):
    def test_beta_search(self):
        self.assertTrue(flags.is_enabled("beta_search"))
    def test_unknown(self):
        self.assertFalse(flags.is_enabled("beta_serach"))
        self.assertEqual(len(flags.ENABLED), 3)
