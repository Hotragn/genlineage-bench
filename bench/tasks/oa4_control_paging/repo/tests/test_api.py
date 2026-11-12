import unittest
from client import api
from client.models import Account, Invoice, Status

class T(unittest.TestCase):
    def test_page_slices(self):
        self.assertEqual(api.page_slices(10, 4), [(0, 4), (4, 8), (8, 10)])
    def test_total(self):
        inv = [Invoice(id=1, account_id=1, amount_cents=250), Invoice(id=2, account_id=1, amount_cents=50)]
        self.assertEqual(api.total_cents(inv), 300)
