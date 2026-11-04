#!/usr/bin/env python3
"""Run every instance of one shard through the proposed verifier (60 s per case)."""
from __future__ import annotations
import csv, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
shard = sys.argv[1]
here = Path(__file__).resolve().parent
rows = list(csv.DictReader(open(ROOT / "instances" / f"shard_{int(shard):03d}.csv")))
out = ROOT / "results"; out.mkdir(exist_ok=True)
fields = ["model_id", "verdict", "execution_status", "model_hash", "L", "H",
          "runtime_total", "runtime_total_median", "n_repeats", "n_warmup", "error"]
recs = []
for i, r in enumerate(rows, 1):
    params = {"n_machines": int(r["n_machines"]), "n_parts": int(r["n_parts"]),
              "ops_per_part": int(r["ops_per_part"]), "wip_bound": int(r["wip_bound"]),
              "unobservable_ratio": float(r["unobservable_ratio"]),
              "fault_locations": int(r["fault_locations"]),
              "interval_width_factor": float(r["interval_width_factor"]),
              "adjustable_ratio": float(r["adjustable_ratio"]), "seed": int(r["seed"])}
    try:
        p = subprocess.run([sys.executable, str(here / "run_one.py"), r["model_id"],
                            json.dumps(params)], capture_output=True, text=True, timeout=60)
        rec = json.loads(p.stdout.strip().splitlines()[-1])
    except subprocess.TimeoutExpired:
        rec = {"model_id": r["model_id"], "verdict": "INC", "execution_status": "TIMEOUT",
               "model_hash": None, "L": r["L"], "H": r["H"], "runtime_total": 60.0,
               "runtime_total_median": 60.0, "n_repeats": 3, "n_warmup": 0,
               "error": "worker timeout after 60s"}
    except Exception as exc:  # noqa: BLE001
        rec = {"model_id": r["model_id"], "verdict": None, "execution_status": "ERROR",
               "error": f"{type(exc).__name__}: {exc}"}
    rec["expected_model_hash"] = r["model_hash"]
    rec["expected_L"] = r["L"]; rec["expected_H"] = r["H"]
    recs.append(rec)
    if i % 25 == 0:
        print(f"shard {shard}: {i}/{len(rows)}", flush=True)
with (out / f"shard_{int(shard):03d}.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields + ["expected_model_hash", "expected_L", "expected_H"],
                       extrasaction="ignore")
    w.writeheader(); w.writerows(recs)
print("done", shard, len(recs))
