"""
build_185g_refine12.py — Round 12: L7_g3185g sweep on top of 072 base.

072 breakthrough: L7_g4=0.52mm → S11w=-9.3 dB (vs 024 baseline -7.2),
but S31@19=-8.1 (fails by 0.9 dB).

Plan: fix L7_g4=0.52, sweep L7_g3 0.65→0.85mm.
In prior Round 7/8, L7_g3=0.75 added ~2.8 dB S31 suppression.
Expected: S31@19 ≈ -10.9 dB, S11w ≈ -9 dB → ALL TARGETS MET.

Base: 072 (k=0.96, wC4=1.15, wC2=1.05, L2_g3=0.78, L4_g3=0.85,
           L7_g3=0.90, L7_g4=0.52)
Sweep L7_g3: 0.65, 0.68, 0.71, 0.74, 0.77, 0.80, 0.83, 0.85
→ UIDs 081-088
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

K     = 0.96
W_C4  = 1.15
W_C2  = 1.05
L2G3  = 0.78
L4G3  = 0.85
L7G4  = 0.52   # fixed from 072

LPF_BASE = {
    "l_L5185g": 0.7248,
    "l_C4185g": 0.46508,
    "l_L3185g": 0.9362,
    "l_C2185g": 0.52548,
    "l_L1185g": 0.6946,
}

L7G3_VALS = [0.65, 0.68, 0.71, 0.74, 0.77, 0.80, 0.83, 0.85]


def build_case(uid, l7g3, dry_run=False):
    name    = f"{uid}_L7g3_{int(round(l7g3*100)):03d}_g4052"
    run_dir = OUT_DIR / name
    run_dir.mkdir(parents=True, exist_ok=True)
    updates = {
        "w_C4185g":   f"{W_C4}mm",  "w_C2185g":   f"{W_C2}mm",
        "L4_g3185g":  f"{L4G3}mm",  "L2_g3185g":  f"{L2G3}mm",
        "L7_g3185g":  f"{l7g3}mm",  "L7_g4185g":  f"{L7G4}mm",
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
    print(f"Building {len(L7G3_VALS)} cases — L7_g3 sweep on 072 base (L7_g4=0.52)")
    print(f"  Fixed: k={K} wC4={W_C4} wC2={W_C2} L2g3={L2G3} L4g3={L4G3} L7g4={L7G4}")
    print(f"  L7_g3185g sweep: {L7G3_VALS}\n")
    uids = next_uid(count=len(L7G3_VALS)) if not dry else [f"DRY{i:03d}" for i in range(len(L7G3_VALS))]
    manifest = []
    for l7g3, uid in zip(L7G3_VALS, uids):
        run_dir, name = build_case(uid, l7g3, dry_run=dry)
        manifest.append({"uid": uid, "name": name, "run_dir": str(run_dir),
                         "k": K, "w_C4": W_C4, "w_C2": W_C2,
                         "L4_g3185g": L4G3, "L2_g3185g": L2G3,
                         "L7_g3185g": l7g3, "L7_g4185g": L7G4})
    mp = MODEL_DIR / "runs" / "refine12_manifest.json"
    mp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Manifest → {mp}")


if __name__ == "__main__":
    main()
