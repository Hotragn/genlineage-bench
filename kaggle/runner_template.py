# GenLineage-Bench Kaggle GPU runner (T4 x2). Two ollama servers, one per GPU, each running one model's grid shard.
import base64, io, json, os, subprocess, sys, tarfile, time, shutil, threading
BUNDLE = "__BUNDLE__"
PLAN = json.loads('__PLAN__')   # {"gpu0": [[model, tag, conds, seeds], ...], "gpu1": [...]}
W = "/kaggle/working/gl"; os.makedirs(W, exist_ok=True)
tarfile.open(fileobj=io.BytesIO(base64.b64decode(BUNDLE))).extractall(W)
def sh(c, quiet=False):
    r = subprocess.run(c, shell=True, capture_output=True, text=True)
    if not quiet: print("$", c, "\n", r.stdout[-2000:], r.stderr[-2000:], flush=True)
    return r
sh("nvidia-smi --query-gpu=name,memory.total --format=csv; python --version")
# Kaggle's system python lacks a working ensurepip, so build the pinned venv with uv (same CPython minor version as our box: 3.13)
sh("pip install -q uv && uv venv /kaggle/working/venv --python 3.13 && uv pip install -q --python /kaggle/working/venv/bin/python -r " + W + "/genlineage/requirements.txt && uv pip freeze --python /kaggle/working/venv/bin/python | grep -iE 'grpc|protobuf|datamodel|lark|jinja|black|isort|pydantic'")
PY = "/kaggle/working/venv/bin/python"
T0 = time.time(); BUDGET_S = float(os.environ.get("GL_BUDGET_S", PLAN.pop("budget_s", 4.9 * 3600)))
os.environ["GL_DEADLINE"] = str(T0 + BUDGET_S)   # run_grid stops starting new cells after this (GPU quota guard)
v = sh(f"cd {W} && {PY} bench/build.py --validate-only 2>&1 | tail -1")
if "ALL OK" not in v.stdout:
    raise SystemExit("benchmark validation failed on this machine; refusing to run the grid")
sh("(command -v zstd || apt-get install -y zstd) >/dev/null 2>&1; curl -fsSL https://ollama.com/install.sh | sh >/tmp/inst.log 2>&1; tail -2 /tmp/inst.log; ollama --version")
for g, port in (("0", 11434), ("1", 11435)):
    subprocess.Popen(f"CUDA_VISIBLE_DEVICES={g} OLLAMA_HOST=127.0.0.1:{port} OLLAMA_NUM_PARALLEL=1 OLLAMA_KEEP_ALIVE=24h ollama serve >/tmp/serve{g}.log 2>&1", shell=True)
time.sleep(10)
models = sorted({j[0] for k in PLAN for j in PLAN[k]})
for m in models:
    t = time.time(); sh(f"OLLAMA_HOST=127.0.0.1:11434 ollama pull {m} >/tmp/pull.log 2>&1; tail -c 200 /tmp/pull.log"); print("pulled", m, round(time.time() - t), "s", flush=True)
sh("OLLAMA_HOST=127.0.0.1:11434 ollama list")
def lane(gpu, port, jobs):
    for job in jobs:
        m, tag, conds, seeds = job[:4]; extra = job[4] if len(job) > 4 else []
        env = dict(os.environ, OLLAMA_URL=f"http://127.0.0.1:{port}")
        t = time.time()
        with open(f"/kaggle/working/log_{tag}.txt", "a") as f:
            subprocess.run([PY, "scripts/run_grid.py", "--model", m, "--tag", tag, "--conds", conds, "--seeds", seeds, "--order", "task_major"] + extra, cwd=W, env=env, stdout=f, stderr=subprocess.STDOUT)
        print(f"lane gpu{gpu} done {tag} {round(time.time()-t)} s", flush=True)
        subprocess.run(f"OLLAMA_HOST=127.0.0.1:{port} ollama stop {m}", shell=True)
        shutil.make_archive(f"/kaggle/working/runs_{tag}", "gztar", W + "/results/runs", tag)
ths = [threading.Thread(target=lane, args=(g[-1], 11434 + int(g[-1]), PLAN[g])) for g in PLAN]
[t.start() for t in ths]
while any(t.is_alive() for t in ths):
    time.sleep(600)
    sh("cd " + W + "/results/runs && find . -name transcript.json | cut -d/ -f2 | sort | uniq -c", quiet=False)
    try: shutil.make_archive("/kaggle/working/runs_partial", "gztar", W + "/results", "runs")  # survives a session timeout
    except Exception as e: print("partial archive failed", e, flush=True)
shutil.make_archive("/kaggle/working/runs_all", "gztar", W + "/results", "runs")
sh("tail -5 /tmp/serve0.log /tmp/serve1.log")
