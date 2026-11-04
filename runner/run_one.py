#!/usr/bin/env python3
"""Run the proposed verifier on one frozen benchmark instance; print one JSON row.

Protocol identical to scripts/_run_one_instance.py of the archived experiment:
  warmup = 0, repeats = 3, method = "main", timeout enforced by the caller (60 s).
"""
from __future__ import annotations
import hashlib, json, platform, statistics, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.benchmarks.rmt_fms_generator import generate_rmt_fms
from src.model.validation import validate_model
from src.verifier import verify


def model_hash(tpn) -> str:
    data = {
        "places": sorted(tpn.places.keys()),
        "transitions": sorted([
            {"name": n, "label": t.label, "fault": t.is_fault,
             "earliest": str(t.interval.earliest), "latest": str(t.interval.latest)}
            for n, t in tpn.transitions.items()], key=lambda x: x["name"]),
        "arcs": sorted(f"{a.from_node}->{a.to_node}" for a in tpn.arcs),
        "initial_marking": sorted(tpn.initial_marking.items()),
        "completion_markings": [sorted(m.items()) for m in tpn.completion_markings],
    }
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:16]


def main() -> int:
    model_id = sys.argv[1]
    params = json.loads(sys.argv[2])
    row = {"model_id": model_id, "family": "rmt_fms", "method": "main",
           "verdict": None, "execution_status": "ERROR", "model_hash": None,
           "L": None, "H": None, "runtime_total": None,
           "runtime_total_median": None, "n_repeats": 3, "n_warmup": 0,
           "python": platform.python_version(), "error": None}
    try:
        tpn, L, H = generate_rmt_fms(**params)
        errs = validate_model(tpn)
        if errs:
            row["error"] = "VALIDATION: " + "; ".join(errs)
            row["verdict"] = "INC"; row["execution_status"] = "ERROR"
            print(json.dumps(row)); return 0
        row.update({"L": int(L), "H": float(H), "model_hash": model_hash(tpn)})
        times = []
        out = None
        for _ in range(3):
            t0 = time.perf_counter()
            out = verify(tpn, L, H)
            elapsed = time.perf_counter() - t0
            v = out.get("stats", {}).get("runtime_total")
            times.append(float(v) if v is not None else elapsed)
        row["verdict"] = out.get("result")
        row["execution_status"] = "COMPLETED"
        row["runtime_total"] = times[-1]
        row["runtime_total_median"] = statistics.median(times)
    except Exception as exc:  # noqa: BLE001
        row["error"] = f"{type(exc).__name__}: {exc}"
    print(json.dumps(row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
