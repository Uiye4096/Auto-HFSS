"""
build_185g_refine9.py — Round 9: L4_g4185g / L2_g4185g coupled sweep for S11 improvement.

Base: 024 (k=0.96, wC4=1.15, wC2=1.05, L4_g3=0.85, L2_g3=0.78, L7_g3=0.90)
Current S11w = -7.2 dB. Goal: push below -10 dB.

Strategy: sweep L4_g4185g = L2_g4185g together (symmetric) over 0.35–0.65mm.
Both are currently 0.501mm. These are HPF matching stubs.
→ 7 cases (0.501 is the reference, included for continuity)
→ UIDs 052-058
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
L2G3 = 0.78
L4G3 = 0.85
L7G3 = 0.90

LPF_BASE = {
    "l_L5185g": 0.7248,
    "l_C4185g": 0.46508,
    "l_L3185g": 0.9362,
    "l_C2185g": 0.52548,
    "l_L1185g": 0.6946,
}

G4_VALS = [0.35, 0.40, 0.45, 0.501, 0.55, 0.60, 0.65]


def build_case(uid, g4, dry_run=False):
    name    = f"{uid}_g4_{int(round(g4*1000)):04d}"
    run_dir = OUT_DIR / name
    run_dir.mkdir(parents=True, exist_ok=True)
    updates = {
        "w_C4185g":   f"{W_C4}mm", "w_C2185g":   f"{W_C2}mm",
        "L4_g3185g":  f"{L4G3}mm", "L2_g3185g":  f"{L2G3}mm",
        "L7_g3185g":  f"{L7G3}mm",
        "L4_g4185g":  f"{g4}mm",   "L2_g4185g":  f"{g4}mm",
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
    print(f"Building {len(G4_VALS)} cases — L4_g4=L2_g4 sweep (S11 matching)")
    print(f"  Base: 024  k={K} wC4={W_C4} wC2={W_C2} L2g3={L2G3} L4g3={L4G3} L7g3={L7G3}")
    print(f"  L4_g4185g = L2_g4185g: {G4_VALS}\n")
    uids = next_uid(count=len(G4_VALS)) if not dry else [f"DRY{i:03d}" for i in range(len(G4_VALS))]
    manifest = []
    for g4, uid in zip(G4_VALS, uids):
        run_dir, name = build_case(uid, g4, dry_run=dry)
        manifest.append({"uid": uid, "name": name, "run_dir": str(run_dir),
                         "k": K, "w_C4": W_C4, "w_C2": W_C2,
                         "L4_g3185g": L4G3, "L2_g3185g": L2G3, "L7_g3185g": L7G3,
                         "L4_g4185g": g4, "L2_g4185g": g4})
    mp = MODEL_DIR / "runs" / "refine9_manifest.json"
    mp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nManifest → {mp}")


if __name__ == "__main__":
    main()
