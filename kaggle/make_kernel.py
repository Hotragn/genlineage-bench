"""Build a Kaggle kernel dir with the bench bundled. Usage: python kaggle/make_kernel.py <slug> '<plan json>'"""
import base64, io, json, os, sys, tarfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
slug, plan = sys.argv[1], sys.argv[2]
buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode="w:gz") as tf:
    for sub in ("bench", "genlineage", "scripts", "bin"):
        tf.add(os.path.join(ROOT, sub), arcname=sub, filter=lambda ti: None if ("__pycache__" in ti.name or "_validate" in ti.name or "kaggle/kernels" in ti.name or "results/runs" in ti.name or ti.name.endswith(".pyc")) else ti)
src = open(os.path.join(ROOT, "kaggle", "runner_template.py")).read().replace("__BUNDLE__", base64.b64encode(buf.getvalue()).decode()).replace("__PLAN__", plan)
d = os.path.join(ROOT, "kaggle", "kernels", slug); os.makedirs(d, exist_ok=True)
open(os.path.join(d, "run.py"), "w").write(src)
json.dump({"id": f"pettuganihotragn/{slug}", "title": slug, "code_file": "run.py", "language": "python", "kernel_type": "script",
           "is_private": True, "enable_gpu": True, "enable_internet": True, "machine_shape": "NvidiaTeslaT4",
           "dataset_sources": [], "competition_sources": [], "kernel_sources": []}, open(os.path.join(d, "kernel-metadata.json"), "w"), indent=1)
print(d, len(src) // 1024, "KB")
