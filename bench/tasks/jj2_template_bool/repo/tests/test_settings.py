import unittest
from app import settings, flags, retry

class T(unittest.TestCase):
    def test_debug_flag(self):
        self.assertIs(settings.DEBUG, False)
        self.assertIs(settings.USE_CACHE, True)
        self.assertTrue(retry.cache_enabled())
    def test_timeout(self):
        self.assertEqual(settings.TIMEOUT_SECONDS, 30)
