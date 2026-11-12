"""Export LineageGuard lineage (component A, genlineage/lineage.py infer) as NetworkX-compatible node-link JSON.

Graph (directed multigraph):
  nodes: file:<path> (role: output | input | generator | build), cmd:<command>, line:<path>:<lineno> (1-based)
  edges: produced_by    file:<output>          -> cmd:<command>
         generated_from file:<output>          -> file:<input>
         derived_from   line:<output>:<n>      -> line:<input>:<m>   (deleting input line m changes output line n)
         part_of        line:<path>:<n>        -> file:<path>
Usage:
  python -I lineage_graph/export.py <bench_root> <tasks_dir> <out_dir> [--split test]
  -> <out_dir>/<task>.json (node-link, key "links") and <out_dir>/summary.json (graph sizes, inference cost)
Load: networkx.node_link_graph(json.load(f), edges="links")   (networkx >= 3.4; older versions use the default key)
"""
import json, os, sys, time

def build_graph(lin, name=""):
    nodes, links = {}, []
    def node(i, **a):
        if i not in nodes: nodes[i] = {"id": i, **a}
        return i
    for out, o in sorted(lin.get("outputs", {}).items()):
        fo = node(f"file:{out}", kind="file", path=out, role="output", noisy_lines=o.get("noisy_lines", 0))
        c = node(f"cmd:{o['command']}", kind="command", command=o["command"])
        links.append({"source": fo, "target": c, "type": "produced_by"})
        for i in o["inputs"]:
            role = "generator" if i in o["generators"] else ("build" if i in o["build"] else "input")
            fi = node(f"file:{i}", kind="file", path=i, role=role)
            if nodes[fi].get("role") == "output": nodes[fi]["role"] = "output+input"
            links.append({"source": fo, "target": fi, "type": "generated_from"})
    for out, entries in sorted(lin.get("line_map", {}).items()):
        for inp, in_line, text, out_idx in entries:
            li = node(f"line:{inp}:{in_line}", kind="line", path=inp, line=in_line, text=text)
            links.append({"source": li, "target": f"file:{inp}", "type": "part_of"})
            for k in out_idx:
                lo = node(f"line:{out}:{k + 1}", kind="line", path=out, line=k + 1)
                links.append({"source": lo, "target": f"file:{out}", "type": "part_of"})
                links.append({"source": lo, "target": li, "type": "derived_from"})
    # dedupe part_of edges
    seen, ded = set(), []
    for l in links:
        k = (l["source"], l["target"], l["type"])
        if l["type"] == "part_of" and k in seen: continue
        seen.add(k); ded.append(l)
    return {"directed": True, "multigraph": True, "graph": {"name": name, "commands": lin.get("commands", []),
            "inference_seconds": lin.get("seconds"), "regen_runs": lin.get("regen_runs")},
            "nodes": list(nodes.values()), "links": ded}

def get_lineage_neighbors(graph, path):
    """Agent-facing tool. `path` is a repo-relative file path, optionally with `:<line>`.
    Returns a JSON-serializable dict describing how the file/line relates to generation:
      for a generated output: the command that writes it, the files it is generated from, and (for a line) the input
      lines whose deletion changes that line; for an input: the outputs (and output lines) derived from it."""
    fid = f"file:{path.split(':')[0]}" if ":" in path and path.rsplit(":", 1)[1].isdigit() else f"file:{path}"
    line = int(path.rsplit(":", 1)[1]) if ":" in path and path.rsplit(":", 1)[1].isdigit() else None
    p = fid[5:]
    out = {"path": p, "line": line, "is_generated": False, "written_by": [], "generated_from": [], "derived_outputs": [],
           "line_sources": [], "line_derivatives": []}
    for l in graph["links"]:
        s, t, ty = l["source"], l["target"], l["type"]
        if ty == "produced_by" and s == fid: out["is_generated"] = True; out["written_by"].append(t[4:])
        elif ty == "generated_from" and s == fid: out["generated_from"].append(t[5:])
        elif ty == "generated_from" and t == fid: out["derived_outputs"].append(s[5:])
        elif ty == "derived_from" and line is not None:
            if s == f"line:{p}:{line}": out["line_sources"].append(t[5:])
            if t == f"line:{p}:{line}": out["line_derivatives"].append(s[5:])
    texts = {n["id"]: n.get("text") for n in graph["nodes"] if n.get("kind") == "line"}
    out["line_sources"] = [{"at": x, "text": texts.get("line:" + x)} for x in sorted(set(out["line_sources"]))]
    out["line_derivatives"] = sorted(set(out["line_derivatives"]))
    for k in ("written_by", "generated_from", "derived_outputs"): out[k] = sorted(set(out[k]))
    if out["is_generated"]:
        out["advice"] = (f"{p} is rewritten by `{', '.join(out['written_by'])}`; an edit here is lost on regeneration unless the generator "
                         f"preserves it. Change {', '.join(out['generated_from']) or 'the generator inputs'} instead.")
    return out

if __name__ == "__main__":
    bench, tasks_dir, od = sys.argv[1], sys.argv[2], sys.argv[3]
    split = sys.argv[sys.argv.index("--split") + 1] if "--split" in sys.argv else "test"
    sys.path.insert(0, bench)
    from genlineage.lineage import infer
    idx = json.load(open(os.path.join(tasks_dir, "index.json"))); os.makedirs(od, exist_ok=True); summ = []
    for t in sorted(idx):
        if split != "all" and idx[t]["split"] != split: continue
        t0 = time.time(); lin = infer(os.path.join(tasks_dir, t, "repo")); wall = time.time() - t0
        g = build_graph(lin, t); json.dump(g, open(os.path.join(od, f"{t}.json"), "w"), indent=1)
        cnt = lambda ty: sum(l["type"] == ty for l in g["links"])
        summ.append(dict(task=t, nodes=len(g["nodes"]), edges=len(g["links"]), file_nodes=sum(n["kind"] == "file" for n in g["nodes"]),
                         line_nodes=sum(n["kind"] == "line" for n in g["nodes"]), command_nodes=sum(n["kind"] == "command" for n in g["nodes"]),
                         produced_by=cnt("produced_by"), generated_from=cnt("generated_from"), derived_from=cnt("derived_from"),
                         infer_seconds=lin["seconds"], regen_runs=lin["regen_runs"], wall_seconds=round(wall, 2)))
        print(json.dumps(summ[-1]), flush=True)
    json.dump(summ, open(os.path.join(od, "summary.json"), "w"), indent=1)
