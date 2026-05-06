"""
build_185g_refine3.py — Phase 4: sweep L2_g3185g to shift HPF cutoff / crossing freq.

Starting point: case 015 (k=0.96, wC4=1.15, wC2=1.05)
  cross=18.372 GHz (need +128 MHz)
  S31@19=-9.8 dB  (need -0.2 dB)

Hypothesis: reducing L2_g3185g from 0.85mm toward 0.75mm (analogous to 12g best
where L2_g312g=0.75 vs L4_g312g=0.85) shifts the HPF passband edge to higher
frequency, raising the crossing frequency without touching the LPF stopband.

Sweep: L2_g3185g = [0.75, 0.78, 0.81, 0.84]  (4 cases, UIDs 023-026)
All other params fixed at case 015 values.
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

# ── Fixed from case 015 ───────────────────────────────────────────────────────
K     = 0.96
W_C4  = 1.15
W_C2  = 1.05

LPF_BASE = {
    "l_L5185g": 0.7248,
    "l_C4185g": 0.46508,
    "l_L3185g": 0.9362,
    "l_C2185g": 0.52548,
    "l_L1185g": 0.6946,
}

# ── Sweep axis ────────────────────────────────────────────────────────────────
L2G3_VALS = [0.75, 0.78, 0.81, 0.84]   # L2_g3185g (baseline 0.85)


def build_case(uid, l2g3, dry_run=False):
    name    = f"{uid}_L2g3_{int(round(l2g3*100)):03d}"
    run_dir = OUT_DIR / name
    run_dir.mkdir(parents=True, exist_ok=True)

    updates = {
        "w_C4185g":   f"{W_C4}mm",
        "w_C2185g":   f"{W_C2}mm",
        "L4_g3185g":  "0.85mm",
        "L2_g3185g":  f"{l2g3}mm",
        "L7_g3185g":  "0.9mm",
    }
    for var, base in LPF_BASE.items():
        updates[var] = f"{round(base * K, 6)}mm"

    up_path = run_dir / "updates.json"
    up_path.write_text(json.dumps(updates, indent=2), encoding="utf-8")

    if dry_run:
        print(f"  [dry] {name}  L2_g3={l2g3}")
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
    dry = "--dry-run" in sys.argv
    print(f"Building {len(L2G3_VALS)} cases (L2_g3 sweep)")
    print(f"  Base: k={K}, wC4={W_C4}, wC2={W_C2}")
    print(f"  L2_g3185g: {L2G3_VALS}  (baseline 0.85)\n")

    uids = next_uid(count=len(L2G3_VALS)) if not dry else [f"DRY{i:03d}" for i in range(len(L2G3_VALS))]
    manifest = []
    for l2g3, uid in zip(L2G3_VALS, uids):
        run_dir, name = build_case(uid, l2g3, dry_run=dry)
        manifest.append({"uid": uid, "name": name, "run_dir": str(run_dir),
                         "k": K, "w_C4": W_C4, "w_C2": W_C2, "L2_g3185g": l2g3,
                         "L4_g3185g": 0.85})

    mp = MODEL_DIR / "runs" / "refine3_manifest.json"
    mp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nManifest: {mp}")
    print(f"Next: python scripts/run_185g_refine3.py")


if __name__ == "__main__":
    main()
