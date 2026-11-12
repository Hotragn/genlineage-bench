import unittest
from client.models import Customer
class T(unittest.TestCase):
    def test_postal_code(self):
        c = Customer.model_validate({"id": 1, "name": "Ada", "address": {"street": "1 Main", "city": "Oslo", "postal_code": "0150", "country": "NO"}})
        self.assertEqual(c.address.postal_code, "0150")
    def test_no_postal_code(self):
        c = Customer.model_validate({"id": 2, "name": "Bo", "address": {"street": "2 Main", "city": "Rome", "country": "IT"}})
        self.assertIsNone(c.address.postal_code)
