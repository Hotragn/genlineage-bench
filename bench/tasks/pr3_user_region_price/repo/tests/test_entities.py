import unittest
from models.entities import Product, Coupon
class T(unittest.TestCase):
    def test_free_product_rejected(self):
        self.assertFalse(Product(sku="A1", price_cents=0).validate())
        self.assertTrue(Product(sku="A1", price_cents=1).validate())
        self.assertFalse(Product(sku="", price_cents=5).validate())
    def test_coupon(self):
        self.assertTrue(Coupon(code="X", percent_off=10).validate())
