import unittest

from pycparser import c_ast, c_parser


class CallCollector(c_ast.NodeVisitor):
    def __init__(self):
        self.names = []

    def visit_FuncCall(self, node):
        self.names.append(node.name.name)
        self.generic_visit(node)


class TestVisitorElse(unittest.TestCase):
    def test_visitor_visits_else_branch(self):
        ast = c_parser.CParser().parse("void f(int x) { if (x) a(); else b(); }")
        v = CallCollector()
        v.visit(ast)
        self.assertEqual(v.names, ["a", "b"])
