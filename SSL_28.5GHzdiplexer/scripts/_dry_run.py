"""Dry-run: build all 7 AEDT cases without running HFSS."""
import json, subprocess, sys
from pathlib import Path

ROOT      = Path(__file__).parent.parent.parent
MODEL_DIR = Path(__file__).parent.parent
INSPECT   = ROOT / "tools" / "aedt_inspect.py"
BASE_AEDT = MODEL_DIR / "final" / "diplexer_285g_baseline.aedt"
RUNS      = MODEL_DIR / "runs"

sys.path.insert(0, str(Path(__file__).parent))
from _uid import next_uid

PARAMS_BASE = {
    "w_C4185g": "1.15mm", "w_C2185g": "1.05mm",
    "l_line2185g": "0.389474mm", "L4_g3185g": "0.551754mm",
    "L7_g3185g": "0.538772mm", "L7_g4185g": "0.337544mm",
    "l_L5185g": "0.451665mm", "l_C4185g": "0.289818mm",
    "l_L3185g": "0.583400mm", "l_C2185g": "0.327457mm",
    "l_L1185g": "0.432845mm", "cx": "0.129825mm",
    "cy": "-0.129825mm", "w_tapper": "0.064912mm", "h_tapper": "0.064912mm",
}
L2_VALS = [0.45, 0.47, 0.49, 0.51, 0.53, 0.55, 0.57]

uids = next_uid(count=len(L2_VALS))
print(f"UIDs assigned: {uids}")
manifest = []
for L2, uid in zip(L2_VALS, uids):
    name = f"{uid}_L2g3_{int(round(L2*100)):03d}"
    rd = RUNS / name
    rd.mkdir(parents=True, exist_ok=True)
    upd = dict(PARAMS_BASE)
    upd["L2_g3185g"] = f"{L2:.5f}mm"
    (rd / "updates.json").write_text(json.dumps(upd, indent=2), encoding="utf-8")
    r = subprocess.run(
        ["python", str(INSPECT), str(BASE_AEDT),
         "--set", str(rd / "updates.json"),
         "--write-to", str(rd / "result.aedt")],
        capture_output=True, text=True
    )
    ok = r.returncode == 0 and (rd / "result.aedt").exists()
    sz = (rd / "result.aedt").stat().st_size if ok else 0
    print(f"  {'OK' if ok else 'ERR'}: {name}  ({sz} bytes)")
    if not ok:
        print("   STDERR:", r.stderr[:200])
    manifest.append({"uid": uid, "name": name, "run_dir": str(rd), "L2_g3": L2})

(RUNS / "sweep1_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(f"\nManifest written: {RUNS}/sweep1_manifest.json")
print("All cases built. Ready to run HFSS.")
