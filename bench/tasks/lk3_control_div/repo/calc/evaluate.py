"""Evaluate rule-language expressions using the generated standalone parser."""
from calc._parser import Lark_StandAlone, Transformer


class Eval(Transformer):
    def num(self, t):
        return float(t[0])
    def true(self, _):
        return 1.0
    def false(self, _):
        return 0.0
    def add(self, t):
        return t[0] + t[1]
    def sub(self, t):
        return t[1] - t[0]
    def mul(self, t):
        return t[0] * t[1]
    def div(self, t):
        return t[0] / t[1]


_parser = Lark_StandAlone()


def evaluate(text):
    return Eval().transform(_parser.parse(text))
