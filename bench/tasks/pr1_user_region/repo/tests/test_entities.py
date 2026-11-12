import unittest
from models.entities import Product, Coupon
class T(unittest.TestCase):
    def test_full_discount(self):
        self.assertTrue(Coupon(code="FREE", percent_off=100).validate())
        self.assertFalse(Coupon(code="BAD", percent_off=101).validate())
        self.assertFalse(Coupon(code="ZERO", percent_off=0).validate())
    def test_product(self):
        self.assertTrue(Product(sku="A1", price_cents=100).validate())
