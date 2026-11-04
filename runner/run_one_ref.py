#!/usr/bin/env python3
"""Run the history-preserving MSCG-LP reference on one frozen instance.

Protocol identical to configs/fullscale_protocol_corrected.yaml:
  method = "mscg_lp_complete", warmup 0, repeats 1, per-case timeout enforced by caller (180 s).
"""
from __future__ import annotations
import hashlib, json, platform, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.benchmarks.rmt_fms_generator import generate_rmt_fms
from src.model.validation import validate_model
from src.baselines.mscg_lp_complete import verify_mscg_lp_complete


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
    model_id, params = sys.argv[1], json.loads(sys.argv[2])
    row = {"model_id": model_id, "family": "rmt_fms", "method": "mscg_lp_complete",
           "verdict": None, "execution_status": "ERROR", "model_hash": None,
           "L": None, "H": None, "runtime_total": None, "runtime_total_median": None,
           "n_repeats": 1, "n_warmup": 0, "python": platform.python_version(), "error": None}
    try:
        tpn, L, H = generate_rmt_fms(**params)
        errs = validate_model(tpn)
        if errs:
            row["error"] = "VALIDATION: " + "; ".join(errs)
            row["verdict"] = "INC"; row["execution_status"] = "ERROR"
            print(json.dumps(row)); return 0
        row.update({"L": int(L), "H": float(H), "model_hash": model_hash(tpn)})
        t0 = time.perf_counter()
        out = verify_mscg_lp_complete(tpn, L, H)
        elapsed = time.perf_counter() - t0
        v = out.get("stats", {}).get("runtime_total")
        rt = float(v) if v is not None else elapsed
        row.update({"verdict": out.get("result"), "execution_status": "COMPLETED",
                    "runtime_total": rt, "runtime_total_median": rt})
    except Exception as exc:  # noqa: BLE001
        row["error"] = f"{type(exc).__name__}: {exc}"
    print(json.dumps(row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
