import unittest
from client import api
from client.models import Account, Invoice, Status

class T(unittest.TestCase):
    def test_long_username(self):
        self.assertEqual(api.parse_account({"id": 1, "username": "margarethill"}).username, "margarethill")
    def test_too_long_username(self):
        with self.assertRaises(Exception):
            api.parse_account({"id": 1, "username": "x" * 33})
