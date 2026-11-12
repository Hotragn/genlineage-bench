import unittest
from app import settings, flags, retry

class T(unittest.TestCase):
    def test_all_features(self):
        for f in ("fast_checkout", "beta_search", "gift_cards"):
            self.assertTrue(flags.is_enabled(f), f)
    def test_count(self):
        self.assertEqual(len(flags.ENABLED), 3)
