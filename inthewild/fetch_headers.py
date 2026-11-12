"""Resolve header presence for a seeded sample of path-detected generated files by fetching (read-only) the file at
the PR head commit (GitHub REST `pulls/<n>` for head.sha, then raw.githubusercontent.com). Falls back to the last
commit in AIDev that touched the file when the head copy is missing (e.g. file removed later in the PR).
Run: venv/bin/python -I build/inthewild/fetch_headers.py out/header_sample.csv out/header_fetch.csv
Cache of fetched first-40-lines in out/header_cache/ (one JSON per pr/file)."""
import csv, hashlib, json, os, subprocess, sys, time, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gendetect import header_class

src, dst = sys.argv[1], sys.argv[2]
cache = os.path.join(os.path.dirname(dst), "header_cache"); os.makedirs(cache, exist_ok=True)

def head_sha(repo, num):
    r = subprocess.run(["gh", "api", f"repos/{repo}/pulls/{num}", "--jq", ".head.sha"], capture_output=True, text=True, timeout=60)
    return r.stdout.strip() if r.returncode == 0 else None

def raw(repo, sha, path):
    u = f"https://raw.githubusercontent.com/{repo}/{sha}/" + urllib.parse.quote(path)
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "research-client"}), timeout=30) as f:
            data = f.read(20000)
        return data.decode("utf-8", errors="replace").splitlines()[:40]
    except Exception as e:
        return None

rows = list(csv.DictReader(open(src)))
out = []
for i, r in enumerate(rows):
    key = hashlib.sha1((r["pr_id"] + r["file"]).encode()).hexdigest(); cp = os.path.join(cache, key + ".json")
    if os.path.exists(cp): rec = json.load(open(cp))
    else:
        parts = r["html_url"].split("/"); repo = parts[3] + "/" + parts[4]; num = parts[6]
        sha = head_sha(repo, num); lines = raw(repo, sha, r["file"]) if sha else None; used = "head"
        if lines is None: lines = raw(repo, r["last_sha"], r["file"]); used = "last_commit"
        rec = dict(repo=repo, head_sha=sha, used=used if lines is not None else "unavailable", lines=lines)
        json.dump(rec, open(cp, "w")); time.sleep(0.3)
    lines = rec["lines"]
    cls = header_class(lines[:15]) if lines is not None else None
    out.append(dict(r, fetched=rec["used"], hdr_fetched=("strong" if cls == "strong" else ("weak" if cls == "weak" else "none")) if lines is not None else "unavailable",
                    first_line=(lines[0][:120] if lines else "")))
    if i % 20 == 0: print(i, flush=True)
with open(dst, "w", newline="") as fo:
    w = csv.DictWriter(fo, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
import collections
print(collections.Counter(o["hdr_fetched"] for o in out))
print(collections.Counter((o["hdr_status_patch"], o["hdr_fetched"]) for o in out))
