import unittest
from models.entities import Product, Coupon
class T(unittest.TestCase):
    def test_default_currency(self):
        self.assertEqual(Product(sku="A", price_cents=1).currency, "EUR")
    def test_coupon(self):
        self.assertTrue(Coupon(code="X", percent_off=10).validate())
