import unittest
from client import api
from client.models import Account, Invoice, Status

class T(unittest.TestCase):
    def test_account_email(self):
        a = api.parse_account({"id": 1, "username": "ada", "email": "ada@example.com"})
        self.assertEqual(a.email, "ada@example.com")
    def test_billable(self):
        self.assertTrue(api.is_billable(api.parse_account({"id": 1, "username": "ada", "status": "active"})))
