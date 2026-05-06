"""
build_185g_refine1.py — Phase 2: k-scale LPF element lengths to recover crossing frequency.

Starting point: case 002 (wC4=1.05, wC2=1.05) — S31 targets met, crossing=18.381 (deficit 119 MHz).
Goal: find k in [0.94, 0.98] that raises crossing to ≥18.5 GHz without hurting S31.

In 185g model, l_sub_LPF185g is an expression referencing all LPF element lengths,
so scaling them automatically adjusts substrate length — no port alignment correction needed.

LPF element baselines (k=1.0):
  l_L5185g  = 0.7248 mm
  l_C4185g  = 0.46508 mm
  l_L3185g  = 0.9362 mm
  l_C2185g  = 0.52548 mm
  l_L1185g  = 0.6946 mm
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _uid import next_uid

ROOT      = Path(__file__).parent.parent.parent
MODEL_DIR = Path(__file__).parent.parent
BASE_AEDT = MODEL_DIR / "diplexer185GHzmodel.aedt"
OUT_DIR   = MODEL_DIR / "runs"
INSPECT   = ROOT / "tools" / "aedt_inspect.py"

# ── Fixed from case 002 ───────────────────────────────────────────────────────
W_C4 = 1.05
W_C2 = 1.05

# ── LPF element base lengths (k=1.0) ─────────────────────────────────────────
LPF_BASE = {
    "l_L5185g": 0.7248,
    "l_C4185g": 0.46508,
    "l_L3185g": 0.9362,
    "l_C2185g": 0.52548,
    "l_L1185g": 0.6946,
}

# ── k sweep ───────────────────────────────────────────────────────────────────
K_VALS = [0.94, 0.95, 0.96, 0.97, 0.98]


def build_case(uid, k, dry_run=False):
    name    = f"{uid}_k{int(round(k*100)):03d}"
    run_dir = OUT_DIR / name
    run_dir.mkdir(parents=True, exist_ok=True)

    updates = {
        "w_C4185g": f"{W_C4}mm",
        "w_C2185g": f"{W_C2}mm",
        "L4_g3185g": "0.85mm",
        "L2_g3185g": "0.85mm",
        "L7_g3185g": "0.9mm",
    }
    for var, base in LPF_BASE.items():
        updates[var] = f"{round(base * k, 6)}mm"

    up_path = run_dir / "updates.json"
    up_path.write_text(json.dumps(updates, indent=2), encoding="utf-8")

    if dry_run:
        print(f"  [dry] {name}  k={k}  l_L5={updates['l_L5185g']}")
        return run_dir, name

    proj_path   = run_dir / "result.aedt"
    result_path = run_dir / "update_result.json"
    ret = subprocess.run(
        ["python", str(INSPECT), str(BASE_AEDT),
         "--set", str(up_path),
         "--write-to", str(proj_path),
         "--out", str(result_path)],
        capture_output=True, text=True,
    )
    if ret.returncode != 0:
        print(f"  ERROR {name}:\n{ret.stderr}")
    else:
        print(f"  Built: {name}  (k={k})")
    return run_dir, name


def main():
    dry = "--dry-run" in sys.argv
    print(f"Building {len(K_VALS)} refine cases (k sweep, wC4={W_C4}, wC2={W_C2})...")
    print(f"  k values: {K_VALS}\n")

    uids = next_uid(count=len(K_VALS)) if not dry else [f"DRY{i:03d}" for i in range(len(K_VALS))]
    manifest = []
    for k, uid in zip(K_VALS, uids):
        run_dir, name = build_case(uid, k, dry_run=dry)
        manifest.append({"uid": uid, "name": name, "run_dir": str(run_dir), "k": k,
                         "w_C4": W_C4, "w_C2": W_C2})

    mp = MODEL_DIR / "runs" / "refine1_manifest.json"
    mp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nManifest: {mp}")
    print(f"Next: python scripts/run_185g_refine1.py")


if __name__ == "__main__":
    main()
