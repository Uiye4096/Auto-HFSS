"""
Refine3: push S21 from ~19.84 GHz toward 18.5 GHz.

Best base from refine2: s02 (L4_g312g=0.90, L2_g312g=0.80, w_C1_y=0.20, idx=0.6)
  S21=19.84 GHz, S31=18.56 GHz

Sensitivity directions confirmed:
  - smaller L4_g312g -> lower S21 (primary HPF capacitor tuning)
  - smaller index1   -> lower S21 (secondary)
  - smaller L2_g312g -> higher S31, but slight S21 increase
  - keep L2_g312g=0.75 to lock S31 >= 18.5 GHz (from s05 result)

Per Rehner 2009: HPF cutoff scales inversely with sqrt(L*C).
Reducing L4_g312g (end-coupled cap gap) reduces capacitance -> raises fT.
But empirically L4_g312g=0.90 lowered S21 vs 0.95. Suggests complex mode coupling.
Target: find L4_g312g level that puts S21 near 18.5 GHz.
"""
import json
import subprocess
from pathlib import Path

ROOT         = Path(r"D:\Desktop\HFSS_real")
MODEL        = ROOT / "12GHzdiplexer2"
BASE_PROJECT = MODEL / "12GHzdiplexer.aedt"
OUT_ROOT     = MODEL / "derived" / "refine3"
INSPECT      = ROOT / "tools" / "aedt_inspect.py"

ALIGNMENT = {
    "compensation_y":   "L2_g212g + cover_HPF_out12g + l_line212g + 1.426mm - l_sub12g",
    "compensation_y_2": (
        "l_line312g + l_L512g + l_C412g + l_L312g + l_C212g + "
        "l_L112g + l_line412g - l_sub_LPF12g"
    ),
}

CASES = {
    # Sweep L4_g312g downward with best base (L2=0.75 keeps S31 high)
    "t01_l4_085_l2_075": {
        "w_C1_y":   "0.200000mm",
        "L4_g312g": "0.850000mm",
        "L2_g312g": "0.750000mm",
        "index1":   "0.600000m",
    },
    "t02_l4_080_l2_075": {
        "w_C1_y":   "0.200000mm",
        "L4_g312g": "0.800000mm",
        "L2_g312g": "0.750000mm",
        "index1":   "0.600000m",
    },
    "t03_l4_075_l2_075": {
        "w_C1_y":   "0.200000mm",
        "L4_g312g": "0.750000mm",
        "L2_g312g": "0.750000mm",
        "index1":   "0.600000m",
    },
    # Combine low L4 + low index1 for extra HPF push
    "t04_l4_085_l2_075_idx05": {
        "w_C1_y":   "0.200000mm",
        "L4_g312g": "0.850000mm",
        "L2_g312g": "0.750000mm",
        "index1":   "0.500000m",
    },
    "t05_l4_080_l2_075_idx05": {
        "w_C1_y":   "0.200000mm",
        "L4_g312g": "0.800000mm",
        "L2_g312g": "0.750000mm",
        "index1":   "0.500000m",
    },
}


def main():
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for case, base_upd in CASES.items():
        case_dir = OUT_ROOT / case
        case_dir.mkdir(parents=True, exist_ok=True)
        updates = dict(base_upd)
        updates.update(ALIGNMENT)
        up_path   = case_dir / "updates.json"
        proj_path = case_dir / f"{case}.aedt"
        up_path.write_text(json.dumps(updates, indent=2), encoding="utf-8")
        subprocess.run(
            ["python", str(INSPECT), str(BASE_PROJECT),
             "--set", str(up_path),
             "--write-to", str(proj_path),
             "--out", str(case_dir / "update_result.json")],
            check=True,
        )
        manifest.append({
            "case":         case,
            "updates":      base_upd,
            "project_path": str(proj_path),
            "output_dir":   str(case_dir / "sim"),
        })
        print(f"  {case}: {base_upd}")
    (OUT_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nBuilt {len(manifest)} cases -> {OUT_ROOT}")


if __name__ == "__main__":
    main()
