"""Tests for the lineage graph export (no generator needed: uses a synthetic lineage dict, then any exported task
graph if present). Run: venv/bin/python -I lineage_graph/test_export.py"""
import glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from export import build_graph, get_lineage_neighbors
LIN = {"commands": ["make gen"], "seconds": 1.0, "regen_runs": 5,
       "outputs": {"gen/m.py": {"command": "make gen", "inputs": ["spec.yaml", "tools/gen.py", "Makefile"], "generators": ["tools/gen.py"],
                                "build": ["Makefile"], "specs": ["spec.yaml"], "noisy_lines": 0}},
       "line_map": {"gen/m.py": [["spec.yaml", 3, "email: str", [9, 10]]]}}
def test_synthetic():
    g = build_graph(LIN, "t")
    types = sorted({l["type"] for l in g["links"]})
    assert types == ["derived_from", "generated_from", "part_of", "produced_by"], types
    n = get_lineage_neighbors(g, "gen/m.py:10")
    assert n["is_generated"] and n["written_by"] == ["make gen"] and n["generated_from"] == ["Makefile", "spec.yaml", "tools/gen.py"]
    assert n["line_sources"] == [{"at": "spec.yaml:3", "text": "email: str"}], n["line_sources"]
    m = get_lineage_neighbors(g, "spec.yaml:3")
    assert not m["is_generated"] and m["derived_outputs"] == ["gen/m.py"] and m["line_derivatives"] == ["gen/m.py:10", "gen/m.py:11"]
    assert get_lineage_neighbors(g, "README.md")["derived_outputs"] == []
def test_networkx_roundtrip():
    import networkx as nx
    for f in sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "*.json"))):
        if f.endswith("summary.json"): continue
        d = json.load(open(f)); G = nx.node_link_graph(d, edges="links")
        assert G.number_of_nodes() == len(d["nodes"]) and G.number_of_edges() == len(d["links"]), f
if __name__ == "__main__":
    test_synthetic(); print("ok synthetic"); test_networkx_roundtrip(); print("ok networkx roundtrip")
