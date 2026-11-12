import unittest

from pycparser import c_generator, c_parser


class TestStructRefRoundTrip(unittest.TestCase):
    def test_member_access_round_trip(self):
        src = "struct s { int x; }; int f(struct s *p, struct s q) { return p->x + q.x; }"
        ast = c_parser.CParser().parse(src)
        out = c_generator.CGenerator().visit(ast)
        self.assertIn("p->x", out)
        self.assertIn("q.x", out)
