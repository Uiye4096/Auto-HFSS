"""
build_185g_refine4.py — Round 5: sweep L4_g3185g at base 025.

Hypothesis: L4_g3185g (currently fixed at 0.85) independently controls
crossing frequency. Reducing it may raise crossing ~117 MHz needed to
meet target, while L2_g3=0.81 maintains S31 transmission zero at 19 GHz.

Base: k=0.96, wC4=1.15, wC2=1.05, L2_g3=0.81 (case 025)
Sweep L4_g3185g: [0.70, 0.73, 0.76, 0.79, 0.82]  → UIDs 027-031
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
W_C2 = 1.05
L2G3 = 0.81

LPF_BASE = {
    "l_L5185g": 0.7248,
    "l_C4185g": 0.46508,
    "l_L3185g": 0.9362,
    "l_C2185g": 0.52548,
    "l_L1185g": 0.6946,
}

L4G3_VALS = [0.70, 0.73, 0.76, 0.79, 0.82]


def build_case(uid, l4g3, dry_run=False):
    name    = f"{uid}_L4g3_{int(round(l4g3*100)):03d}"
    run_dir = OUT_DIR / name
    run_dir.mkdir(parents=True, exist_ok=True)

    updates = {
        "w_C4185g":  f"{W_C4}mm",
        "w_C2185g":  f"{W_C2}mm",
        "L4_g3185g": f"{l4g3}mm",
        "L2_g3185g": f"{L2G3}mm",
        "L7_g3185g": "0.9mm",
    }
    for var, base in LPF_BASE.items():
        updates[var] = f"{round(base * K, 6)}mm"

    (run_dir / "updates.json").write_text(json.dumps(updates, indent=2), encoding="utf-8")

    if dry_run:
        print(f"  [dry] {name}  L4_g3={l4g3}")
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
    print(f"Building {len(L4G3_VALS)} cases (L4_g3 sweep)")
    print(f"  Base: k={K}, wC4={W_C4}, wC2={W_C2}, L2_g3={L2G3}")
    print(f"  L4_g3185g: {L4G3_VALS}  (baseline 0.85)\n")

    uids = next_uid(count=len(L4G3_VALS)) if not dry else [f"DRY{i:03d}" for i in range(len(L4G3_VALS))]
    manifest = []
    for l4g3, uid in zip(L4G3_VALS, uids):
        run_dir, name = build_case(uid, l4g3, dry_run=dry)
        manifest.append({"uid": uid, "name": name, "run_dir": str(run_dir),
                         "k": K, "w_C4": W_C4, "w_C2": W_C2,
                         "L4_g3185g": l4g3, "L2_g3185g": L2G3})

    mp = MODEL_DIR / "runs" / "refine4_manifest.json"
    mp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nManifest: {mp}")
    print(f"Next: python scripts/run_185g_refine4.py")


if __name__ == "__main__":
    main()
