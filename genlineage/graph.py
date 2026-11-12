"""Export inferred lineage as typed graph edges, so it can be merged into a NetworkX code graph.

Nodes: repo-relative file paths (kind='file', generated=True/False) and commands ('cmd:<command>', kind='command').
Edges (all lowercase, like the call edges of common AST code graphs):
  output --generated_from--> input        (deleting the input changes the output, or breaks generation)
  output --produced_by-->    cmd:<command>
  input  --consumed_by-->    cmd:<command>
  output --line_from-->      input        one edge per mapped (output line -> input line) pair, with attrs out_line, in_line, text
merge with any graph whose file nodes are repo-relative paths: networkx.compose(code_graph, lineage_graph(lin)).
"""
import networkx as nx

def lineage_graph(lin, line_edges=True):
    G = nx.MultiDiGraph()
    for out, o in (lin or {}).get("outputs", {}).items():
        cmd = "cmd:" + o["command"]
        G.add_node(out, kind="file", generated=True); G.add_node(cmd, kind="command")
        G.add_edge(out, cmd, key="produced_by", type="produced_by")
        for i in o["inputs"]:
            role = "generator" if i in o.get("generators", []) else ("build" if i in o.get("build", []) else "spec")
            if i not in G: G.add_node(i, kind="file", generated=False)
            G.add_edge(out, i, key="generated_from", type="generated_from", role=role)
            G.add_edge(i, cmd, key="consumed_by", type="consumed_by")
    if line_edges:
        for out, entries in (lin or {}).get("line_map", {}).items():
            for src, ln, text, hit in entries:
                for h in hit:
                    G.add_edge(out, src, key=f"line_from:{h + 1}:{ln}", type="line_from", out_line=h + 1, in_line=ln, text=text)
    return G

def get_lineage_neighbors(G, node, edge_type=None, direction="out"):
    """Tool-shaped accessor (like a code graph's get_code_neighbors): neighbours of a file over lineage edges."""
    if node not in G: return []
    es = G.out_edges(node, data=True) if direction == "out" else G.in_edges(node, data=True)
    res = []
    for u, v, d in es:
        if edge_type and d["type"] != edge_type: continue
        res.append({"source": u, "target": v, **d})
    return res

if __name__ == "__main__":
    import json, sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from genlineage.lineage import infer
    repo = sys.argv[1]; lin = infer(repo); G = lineage_graph(lin)
    print(json.dumps({"nodes": G.number_of_nodes(), "edges": G.number_of_edges(),
                      "edge_types": sorted({d['type'] for _, _, d in G.edges(data=True)})}, indent=1))
    for out in lin["outputs"]:
        print(out, [ (e["target"], e.get("role")) for e in get_lineage_neighbors(G, out, "generated_from")])
        print("  line_from sample:", [(e["out_line"], e["target"], e["in_line"], e["text"]) for e in get_lineage_neighbors(G, out, "line_from")][:3])
    nx.write_graphml(nx.DiGraph(G), os.environ.get("GRAPHML", "/tmp/lineage.graphml"))
