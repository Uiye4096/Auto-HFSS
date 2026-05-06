"""
build_185g_refine10.py — Round 10: l_line185g sweep for S11 phase tuning.

Base: 024 (k=0.96, wC4=1.15, wC2=1.05, L4_g3=0.85, L2_g3=0.78, L7_g3=0.90)
Current S11w = -7.2 dB. l_line185g = 2.0 mm currently.

Changing line length rotates S11 on Smith chart — may improve S11w.
Also sweep l_line2185g simultaneously (currently 0.6mm, both together).

Sweep l_line185g: 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4, 2.6, 2.8 mm
→ 9 cases (2.0 is reference = 024)
→ UIDs 059-067
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

LINE_VALS = [1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4, 2.6, 2.8]


def build_case(uid, lline, dry_run=False):
    name    = f"{uid}_line_{int(round(lline*10)):03d}"
    run_dir = OUT_DIR / name
    run_dir.mkdir(parents=True, exist_ok=True)
    updates = {
        "w_C4185g":   f"{W_C4}mm", "w_C2185g":  f"{W_C2}mm",
        "L4_g3185g":  f"{L4G3}mm", "L2_g3185g": f"{L2G3}mm",
        "L7_g3185g":  f"{L7G3}mm",
        "l_line185g": f"{lline}mm",
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
    print(f"Building {len(LINE_VALS)} cases — l_line185g sweep")
    print(f"  Base: 024  k={K} wC4={W_C4} wC2={W_C2} L2g3={L2G3} L4g3={L4G3}")
    print(f"  l_line185g: {LINE_VALS}  (current=2.0mm)\n")
    uids = next_uid(count=len(LINE_VALS)) if not dry else [f"DRY{i:03d}" for i in range(len(LINE_VALS))]
    manifest = []
    for lline, uid in zip(LINE_VALS, uids):
        run_dir, name = build_case(uid, lline, dry_run=dry)
        manifest.append({"uid": uid, "name": name, "run_dir": str(run_dir),
                         "k": K, "w_C4": W_C4, "w_C2": W_C2,
                         "L4_g3185g": L4G3, "L2_g3185g": L2G3, "L7_g3185g": L7G3,
                         "l_line185g": lline})
    mp = MODEL_DIR / "runs" / "refine10_manifest.json"
    mp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nManifest → {mp}")


if __name__ == "__main__":
    main()
