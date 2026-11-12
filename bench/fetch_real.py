"""Materialize the yt-dlp based real-repository tasks (bench/tasks_real/ry*).

We do not ship the yt-dlp snapshot itself, because upstream hardcodes several public service keys in its extractors
and those trip secret scanners. Each ry task keeps only the files the benchmark changed or added (repo/: Makefile,
tests/, the injected bug, the regenerated output) plus upstream_manifest.json, which pins the upstream commit and
lists the SHA-256 of every file in the finished task repository. This script downloads that commit once, fills in the
untouched upstream files, and refuses to continue unless every file matches the manifest and nothing extra is left.

Usage: python bench/fetch_real.py [task_id ...]     (no arguments: all ry tasks; a no-op when already complete)
       python bench/fetch_real.py --strip           (remove the fetched files again)"""
import hashlib, io, json, os, shutil, sys, tarfile, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "tasks_real")
CACHE = os.path.join(os.path.dirname(HERE), ".cache", "upstream")

def _sha(p):
    with open(p, "rb") as f: return hashlib.sha256(f.read()).hexdigest()

def _tree(repo):
    out = {}
    for d, _, fs in os.walk(repo):
        for f in fs:
            p = os.path.join(d, f); out[os.path.relpath(p, repo)] = p
    return out

def check(task):
    """Return a list of problems; empty means repo/ matches the manifest exactly."""
    root = os.path.join(OUT, task); man = json.load(open(os.path.join(root, "upstream_manifest.json")))
    have = _tree(os.path.join(root, "repo")); bad = []
    for rel, h in man["files"].items():
        if rel not in have: bad.append(f"missing {rel}")
        elif _sha(have[rel]) != h: bad.append(f"hash mismatch {rel}")
    bad += [f"unexpected {rel}" for rel in have if rel not in man["files"]]
    return bad

def _tarball(man):
    os.makedirs(CACHE, exist_ok=True); path = os.path.join(CACHE, f"yt-dlp-{man['commit']}.tar.gz")
    if not os.path.exists(path):
        print("downloading", man["tarball"], flush=True)
        with urllib.request.urlopen(man["tarball"], timeout=300) as r: data = r.read()
        open(path + ".part", "wb").write(data); os.replace(path + ".part", path)
    return path

def ensure(task):
    root = os.path.join(OUT, task); man = json.load(open(os.path.join(root, "upstream_manifest.json")))
    if not check(task): return
    repo = os.path.join(root, "repo"); overlay = set(man["overlay"])
    with tarfile.open(_tarball(man)) as tf:
        for m in tf.getmembers():
            if not m.isfile(): continue
            rel = m.name.split("/", 1)[1] if "/" in m.name else ""
            if not rel or rel in overlay or rel not in man["files"]: continue  # trimmed paths are not in the manifest
            dst = os.path.join(repo, rel); os.makedirs(os.path.dirname(dst), exist_ok=True)
            with tf.extractfile(m) as src, open(dst, "wb") as f: shutil.copyfileobj(src, f)
            os.chmod(dst, m.mode & 0o777)
    bad = check(task)
    if bad: raise SystemExit(f"{task}: upstream files do not match the manifest ({len(bad)} problems, first: {bad[:5]})")
    print(f"{task}: {len(man['files'])} files verified against upstream_manifest.json", flush=True)

def strip(task):
    """Undo ensure(): keep only the overlay files (the state that is committed)."""
    root = os.path.join(OUT, task); man = json.load(open(os.path.join(root, "upstream_manifest.json")))
    repo = os.path.join(root, "repo"); keep = set(man["overlay"])
    for rel, p in _tree(repo).items():
        if rel not in keep: os.remove(p)
    for d, _, _ in sorted(os.walk(repo), key=lambda x: -len(x[0])):
        if d != repo and not os.listdir(d): os.rmdir(d)

def ry_tasks():
    return sorted(t for t in os.listdir(OUT) if os.path.exists(os.path.join(OUT, t, "upstream_manifest.json")))

def ensure_all():
    for t in ry_tasks(): ensure(t)

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--strip"]
    for t in (args or ry_tasks()): (strip if "--strip" in sys.argv else ensure)(t)
