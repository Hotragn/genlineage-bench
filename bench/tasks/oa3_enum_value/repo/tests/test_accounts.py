import unittest
from client import api
from client.models import Account, Invoice, Status

class T(unittest.TestCase):
    def test_archived_status(self):
        a = api.parse_account({"id": 1, "username": "old", "status": "archived"})
        self.assertEqual(a.status.value, "archived")
        self.assertFalse(api.is_billable(a))
    def test_active(self):
        self.assertTrue(api.is_billable(api.parse_account({"id": 2, "username": "new", "status": "active"})))
