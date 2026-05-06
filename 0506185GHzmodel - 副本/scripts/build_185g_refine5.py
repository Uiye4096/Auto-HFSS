"""
build_185g_refine5.py — Round 6: micro-sweep wC2 from case 024 base.

024 status: cross=18.535 (+35 MHz margin), S31@19=-10.3 (only 0.3 dB margin — thin).
Strategy: increase wC2 slightly to add S31 headroom while staying within crossing budget.

From sweep1 sensitivity (at k=1.0): +0.10mm wC2 → ~+1.0 dB S31, ~-80 MHz crossing.
At k=0.96 the effect may differ, but a 0.04mm increase should give ~+0.4 dB S31
with only ~30 MHz crossing cost, keeping crossing well above 18.5 GHz.

Base: 024 (k=0.96, wC4=1.15, L4_g3=0.85, L2_g3=0.78, wC2=1.05)
Sweep wC2: [1.06, 1.07, 1.08, 1.09]  → UIDs 032-035
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

K    = 0.96
W_C4 = 1.15
L2G3 = 0.78
L4G3 = 0.85

LPF_BASE = {
    "l_L5185g": 0.7248,
    "l_C4185g": 0.46508,
    "l_L3185g": 0.9362,
    "l_C2185g": 0.52548,
    "l_L1185g": 0.6946,
}

WC2_VALS = [1.06, 1.07, 1.08, 1.09]


def build_case(uid, wc2, dry_run=False):
    name    = f"{uid}_wC2_{int(round(wc2*100)):03d}"
    run_dir = OUT_DIR / name
    run_dir.mkdir(parents=True, exist_ok=True)

    updates = {
        "w_C4185g":  f"{W_C4}mm",
        "w_C2185g":  f"{wc2}mm",
        "L4_g3185g": f"{L4G3}mm",
        "L2_g3185g": f"{L2G3}mm",
        "L7_g3185g": "0.9mm",
    }
    for var, base in LPF_BASE.items():
        updates[var] = f"{round(base * K, 6)}mm"

    (run_dir / "updates.json").write_text(json.dumps(updates, indent=2), encoding="utf-8")

    if dry_run:
        print(f"  [dry] {name}  wC2={wc2}")
        return run_dir, name

    proj_path   = run_dir / "result.aedt"
    result_path = run_dir / "update_result.json"
    ret = subprocess.run(
        ["python", str(INSPECT), str(BASE_AEDT),
         "--set", str(run_dir / "updates.json"),
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
    print(f"Building {len(WC2_VALS)} cases (wC2 micro-sweep)")
    print(f"  Base: k={K}, wC4={W_C4}, L2_g3={L2G3}, L4_g3={L4G3}")
    print(f"  wC2: {WC2_VALS}  (024 baseline 1.05)\n")

    uids = next_uid(count=len(WC2_VALS)) if not dry else [f"DRY{i:03d}" for i in range(len(WC2_VALS))]
    manifest = []
    for wc2, uid in zip(WC2_VALS, uids):
        run_dir, name = build_case(uid, wc2, dry_run=dry)
        manifest.append({"uid": uid, "name": name, "run_dir": str(run_dir),
                         "k": K, "w_C4": W_C4, "w_C2": wc2,
                         "L4_g3185g": L4G3, "L2_g3185g": L2G3})

    mp = MODEL_DIR / "runs" / "refine5_manifest.json"
    mp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nManifest: {mp}")
    print(f"Next: python scripts/run_185g_refine5.py")


if __name__ == "__main__":
    main()
