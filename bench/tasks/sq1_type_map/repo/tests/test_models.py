import typing, unittest
from db.models import Invoices
from db import queries

class T(unittest.TestCase):
    def test_paid_annotation(self):
        self.assertIs(typing.get_type_hints(Invoices)["paid"], bool)
    def test_revenue(self):
        rows = [Invoices(1, "a", 10.5, True), Invoices(2, "b", 3.0, False)]
        self.assertEqual(queries.revenue(rows), 10.5)
