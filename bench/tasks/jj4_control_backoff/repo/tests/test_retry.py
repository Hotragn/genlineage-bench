import unittest
from app import settings, flags, retry

class T(unittest.TestCase):
    def test_backoff(self):
        self.assertEqual(retry.backoff_schedule(), [1, 2, 4])
    def test_retries_setting(self):
        self.assertEqual(settings.RETRIES, 3)
