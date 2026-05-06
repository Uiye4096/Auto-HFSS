"""
build_185g_sweep1.py — Generate L9 sweep cases for 185g model S31 improvement.

Goal: improve S31@19 from -7.9 dB to ≤ -10 dB by widening capacitor elements,
while protecting crossing frequency (≥18.5 GHz) and passband performance.

Strategy: 3×3 grid over w_C4185g × w_C2185g
  - Baseline: w_C4=1.0mm, w_C2=0.9mm → S31@19=-7.9 dB (need 2 dB more)
  - 12g best:  wC=1.45mm for both   → S31@19=-10.8 dB
  - Stepping halfway: try 1.05–1.25mm range
"""
import json
import shutil
import subprocess
import sys
from itertools import product
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _uid import next_uid

ROOT        = Path(__file__).parent.parent.parent  # HFSS_real/
MODEL_DIR   = Path(__file__).parent.parent         # 0506185GHzmodel - 副本/
BASE_AEDT   = MODEL_DIR / "diplexer185GHzmodel.aedt"
OUT_DIR     = MODEL_DIR / "runs"
INSPECT     = ROOT / "tools" / "aedt_inspect.py"

# ── Sweep axes ────────────────────────────────────────────────────────────────
W_C4_VALS = [1.05, 1.15, 1.25]   # w_C4185g (baseline 1.0)
W_C2_VALS = [0.95, 1.05, 1.15]   # w_C2185g (baseline 0.9)

# Fixed at baseline values
FIXED = {
    "L4_g3185g": "0.85mm",
    "L2_g3185g": "0.85mm",
    "L7_g3185g": "0.9mm",
}


def case_name(uid, wc4, wc2):
    return f"{uid}_wC4{int(round(wc4*100)):03d}_wC2{int(round(wc2*100)):03d}"


def build_case_named(name, wc4, wc2, dry_run=False):
    run_dir  = OUT_DIR / name
    run_dir.mkdir(parents=True, exist_ok=True)

    updates = {
        **FIXED,
        "w_C4185g": f"{wc4}mm",
        "w_C2185g": f"{wc2}mm",
    }
    up_path  = run_dir / "updates.json"
    up_path.write_text(json.dumps(updates, indent=2), encoding="utf-8")

    proj_path   = run_dir / "result.aedt"
    result_path = run_dir / "update_result.json"

    if dry_run:
        print(f"  [dry-run] {name}: {updates}")
        return run_dir

    ret = subprocess.run(
        ["python", str(INSPECT), str(BASE_AEDT),
         "--set", str(up_path),
         "--write-to", str(proj_path),
         "--out", str(result_path)],
        capture_output=True, text=True,
    )
    if ret.returncode != 0:
        print(f"  ERROR building {name}:\n{ret.stderr}")
    else:
        print(f"  Built: {name}")
    return run_dir


def main():
    dry = "--dry-run" in sys.argv
    cases = list(product(W_C4_VALS, W_C2_VALS))
    print(f"Building {len(cases)} cases (w_C4 × w_C2)...")
    print(f"  w_C4185g: {W_C4_VALS}")
    print(f"  w_C2185g: {W_C2_VALS}")
    print()

    uids = next_uid(count=len(cases)) if not dry else [f"DRY{i:03d}" for i in range(len(cases))]
    manifest = []
    for (wc4, wc2), uid in zip(cases, uids):
        run_dir = build_case_named(case_name(uid, wc4, wc2), wc4, wc2, dry_run=dry)
        manifest.append({
            "uid":     uid,
            "name":    case_name(uid, wc4, wc2),
            "run_dir": str(run_dir),
            "w_C4":    wc4,
            "w_C2":    wc2,
        })

    manifest_path = MODEL_DIR / "runs" / "sweep1_manifest.json"
    manifest_path.parent.mkdir(exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nManifest: {manifest_path}")
    print(f"Next: python scripts/run_185g_sweep1.py")


if __name__ == "__main__":
    main()
