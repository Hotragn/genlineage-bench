import typing, unittest
from db.models import Invoices
from db import queries

class T(unittest.TestCase):
    def test_anonymous(self):
        inv = Invoices(id=1, total=5.0, paid=False)
        self.assertIsNone(inv.customer)
        self.assertEqual(queries.outstanding([inv]), [inv])
