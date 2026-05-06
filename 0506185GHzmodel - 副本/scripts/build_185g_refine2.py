"""
build_185g_refine2.py — Phase 3: 2D sweep (k × wC4) to find balanced trade-off.

Insight from refine1:
  - k=0.96 gives cross=18.524 ✓ but S31@19=-8.0 (deficit 2 dB)
  - k=0.97 gives cross=18.476 ✗ but S31@19=-8.8 (deficit 1.2 dB)
  - Widening wC4 recovers S31 but drops crossing

Strategy: jointly sweep k × wC4 to find the balance point.
  k:   [0.96, 0.97]       — crossing control
  wC4: [1.15, 1.20, 1.25, 1.30]  — S31 recovery
  wC2: fixed at 1.05
→ 8 cases (UIDs 015-022)
"""
import json
import subprocess
import sys
from itertools import product
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _uid import next_uid

ROOT      = Path(__file__).parent.parent.parent
MODEL_DIR = Path(__file__).parent.parent
BASE_AEDT = MODEL_DIR / "diplexer185GHzmodel.aedt"
OUT_DIR   = MODEL_DIR / "runs"
INSPECT   = ROOT / "tools" / "aedt_inspect.py"

W_C2 = 1.05

LPF_BASE = {
    "l_L5185g": 0.7248,
    "l_C4185g": 0.46508,
    "l_L3185g": 0.9362,
    "l_C2185g": 0.52548,
    "l_L1185g": 0.6946,
}

K_VALS   = [0.96, 0.97]
WC4_VALS = [1.15, 1.20, 1.25, 1.30]


def build_case(uid, k, wc4, dry_run=False):
    name    = f"{uid}_k{int(round(k*100)):03d}_wC4{int(round(wc4*100)):03d}"
    run_dir = OUT_DIR / name
    run_dir.mkdir(parents=True, exist_ok=True)

    updates = {
        "w_C4185g":  f"{wc4}mm",
        "w_C2185g":  f"{W_C2}mm",
        "L4_g3185g": "0.85mm",
        "L2_g3185g": "0.85mm",
        "L7_g3185g": "0.9mm",
    }
    for var, base in LPF_BASE.items():
        updates[var] = f"{round(base * k, 6)}mm"

    up_path = run_dir / "updates.json"
    up_path.write_text(json.dumps(updates, indent=2), encoding="utf-8")

    if dry_run:
        print(f"  [dry] {name}  k={k}  wC4={wc4}")
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
        print(f"  Built: {name}")
    return run_dir, name


def main():
    dry   = "--dry-run" in sys.argv
    cases = list(product(K_VALS, WC4_VALS))
    print(f"Building {len(cases)} cases (k × wC4), wC2={W_C2}...")
    print(f"  k:   {K_VALS}")
    print(f"  wC4: {WC4_VALS}\n")

    uids = next_uid(count=len(cases)) if not dry else [f"DRY{i:03d}" for i in range(len(cases))]
    manifest = []
    for (k, wc4), uid in zip(cases, uids):
        run_dir, name = build_case(uid, k, wc4, dry_run=dry)
        manifest.append({"uid": uid, "name": name, "run_dir": str(run_dir),
                         "k": k, "w_C4": wc4, "w_C2": W_C2})

    mp = MODEL_DIR / "runs" / "refine2_manifest.json"
    mp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nManifest: {mp}")
    print(f"Next: python scripts/run_185g_refine2.py")


if __name__ == "__main__":
    main()
