"""
build_185g_refine11.py — Round 11: L7_g4185g + l_line2185g sweep for S11.

Direction A: L7_g4185g sweep (HPF-side stub, 0.396mm baseline) → 0.20, 0.28, 0.36, 0.396, 0.44, 0.52, 0.60
Direction B: l_line2185g sweep (internal connection, 0.6mm baseline) → 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0

Base: 024 (k=0.96, wC4=1.15, wC2=1.05, L2_g3=0.78, L4_g3=0.85, L7_g3=0.90)
→ UIDs 068-081 (14 cases total)
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

# Direction A: L7_g4185g sweep (baseline 0.396)
L7G4_VALS = [0.20, 0.28, 0.36, 0.44, 0.52, 0.60]

# Direction B: l_line2185g sweep (baseline 0.6)
LINE2_VALS = [0.3, 0.4, 0.5, 0.7, 0.8, 1.0, 1.2]


def build_case(uid, extra_updates, tag, dry_run=False):
    name    = f"{uid}_{tag}"
    run_dir = OUT_DIR / name
    run_dir.mkdir(parents=True, exist_ok=True)
    updates = {
        "w_C4185g":  f"{W_C4}mm", "w_C2185g":  f"{W_C2}mm",
        "L4_g3185g": f"{L4G3}mm", "L2_g3185g": f"{L2G3}mm",
        "L7_g3185g": f"{L7G3}mm",
    }
    for var, base in LPF_BASE.items():
        updates[var] = f"{round(base * K, 6)}mm"
    updates.update(extra_updates)
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
    total = len(L7G4_VALS) + len(LINE2_VALS)
    print(f"Building {total} cases — Round 11 S11 sweep")
    print(f"  Dir A: L7_g4185g {L7G4_VALS}  (base=0.396)")
    print(f"  Dir B: l_line2185g {LINE2_VALS}  (base=0.6)\n")
    uids = next_uid(count=total) if not dry else [f"DRY{i:03d}" for i in range(total)]
    manifest = []
    idx = 0
    for v in L7G4_VALS:
        uid = uids[idx]; idx += 1
        tag = f"L7g4_{int(round(v*100)):03d}"
        run_dir, name = build_case(uid, {"L7_g4185g": f"{v}mm"}, tag, dry)
        manifest.append({"uid": uid, "name": name, "run_dir": str(run_dir),
                         "direction": "A", "param": "L7_g4185g", "value": v,
                         "L7_g4185g": v, "l_line2185g": 0.6})
    for v in LINE2_VALS:
        uid = uids[idx]; idx += 1
        tag = f"line2_{int(round(v*10)):03d}"
        run_dir, name = build_case(uid, {"l_line2185g": f"{v}mm"}, tag, dry)
        manifest.append({"uid": uid, "name": name, "run_dir": str(run_dir),
                         "direction": "B", "param": "l_line2185g", "value": v,
                         "L7_g4185g": 0.396, "l_line2185g": v})
    mp = MODEL_DIR / "runs" / "refine11_manifest.json"
    mp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nManifest → {mp}")


if __name__ == "__main__":
    main()
