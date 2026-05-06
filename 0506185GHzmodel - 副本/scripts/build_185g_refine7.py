"""
build_185g_refine7.py — Round 7B: k=0.95 + L2_g3 fine sweep.

k=0.95 gives ~50 MHz more crossing headroom than k=0.96.
At 034's wC4/wC2 (1.15/1.08), find the L2_g3 sweet spot.

Base: k=0.95, wC4=1.15, wC2=1.08, L4_g3=0.85
Sweep L2_g3185g: [0.78, 0.79, 0.80, 0.81, 0.82] → UIDs 042-046
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

K    = 0.95
W_C4 = 1.15
W_C2 = 1.08
L4G3 = 0.85

LPF_BASE = {
    "l_L5185g": 0.7248,
    "l_C4185g": 0.46508,
    "l_L3185g": 0.9362,
    "l_C2185g": 0.52548,
    "l_L1185g": 0.6946,
}

L2G3_VALS = [0.78, 0.79, 0.80, 0.81, 0.82]


def build_case(uid, l2g3, dry_run=False):
    name    = f"{uid}_k095_L2g3_{int(round(l2g3*100)):03d}"
    run_dir = OUT_DIR / name
    run_dir.mkdir(parents=True, exist_ok=True)
    updates = {
        "w_C4185g":  f"{W_C4}mm", "w_C2185g":  f"{W_C2}mm",
        "L4_g3185g": f"{L4G3}mm", "L2_g3185g": f"{l2g3}mm",
        "L7_g3185g": "0.9mm",
    }
    for var, base in LPF_BASE.items():
        updates[var] = f"{round(base * K, 6)}mm"
    (run_dir / "updates.json").write_text(json.dumps(updates, indent=2), encoding="utf-8")
    if dry_run:
        print(f"  [dry] {name}"); return run_dir, name
    ret = subprocess.run(
        ["python", str(INSPECT), str(BASE_AEDT),
         "--set", str(run_dir / "updates.json"),
         "--write-to", str(run_dir / "result.aedt"),
         "--out",      str(run_dir / "update_result.json")],
        capture_output=True, text=True)
    print(f"  {'Built' if ret.returncode==0 else 'ERROR'}: {name}")
    return run_dir, name


def main():
    dry = "--dry-run" in sys.argv
    print(f"Building {len(L2G3_VALS)} cases (k=0.95 L2_g3 fine sweep)")
    print(f"  Base: wC4={W_C4}, wC2={W_C2}, L4_g3={L4G3}")
    print(f"  L2_g3185g: {L2G3_VALS}\n")
    uids = next_uid(count=len(L2G3_VALS)) if not dry else [f"DRY{i:03d}" for i in range(len(L2G3_VALS))]
    manifest = []
    for l2g3, uid in zip(L2G3_VALS, uids):
        run_dir, name = build_case(uid, l2g3, dry_run=dry)
        manifest.append({"uid": uid, "name": name, "run_dir": str(run_dir),
                         "k": K, "w_C4": W_C4, "w_C2": W_C2,
                         "L4_g3185g": L4G3, "L2_g3185g": l2g3, "L7_g3185g": 0.90})
    mp = MODEL_DIR / "runs" / "refine7_manifest.json"
    mp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nManifest: {mp}")


if __name__ == "__main__":
    main()
