"""
Refine5: targeted combinations to push S21 < 19 GHz and S31 >= 18.5 GHz.

Key findings so far:
  - Lowest S21: r08 (c1y=0.20, L4=1.00, L2=0.85, idx=0.6) -> S21=19.12
  - Highest S31: u05 (c1y=0.25, L4=0.90, L2=0.80, idx=0.6) -> S31=18.64
  - L2_g312g=0.75 raises S31 (s02, s05)

Untested: L4_g312g=1.00mm (r08 best) combined with:
  - smaller L2_g312g (for S31 >= 18.5)
  - smaller index1   (for lower S21)
  - larger c1y       (u05 showed benefit for S31)
"""
import json
import subprocess
from pathlib import Path

ROOT         = Path(r"D:\Desktop\HFSS_real")
MODEL        = ROOT / "12GHzdiplexer2"
BASE_PROJECT = MODEL / "12GHzdiplexer.aedt"
OUT_ROOT     = MODEL / "derived" / "refine5"
INSPECT      = ROOT / "tools" / "aedt_inspect.py"

ALIGNMENT = {
    "compensation_y":   "L2_g212g + cover_HPF_out12g + l_line212g + 1.426mm - l_sub12g",
    "compensation_y_2": (
        "l_line312g + l_L512g + l_C412g + l_L312g + l_C212g + "
        "l_L112g + l_line412g - l_sub_LPF12g"
    ),
}

CASES = {
    # r08 anchor + smaller L2 to push S31 above 18.5
    "v01_c1y020_l4_100_l2_075": {
        "w_C1_y":   "0.200000mm",
        "L4_g312g": "1.000000mm",
        "L2_g312g": "0.750000mm",
        "index1":   "0.600000m",
    },
    # r08 anchor + idx=0.5 for lower S21
    "v02_c1y020_l4_100_l2_085_idx05": {
        "w_C1_y":   "0.200000mm",
        "L4_g312g": "1.000000mm",
        "L2_g312g": "0.850000mm",
        "index1":   "0.500000m",
    },
    # Full combo: best S21 knobs + best S31 knob
    "v03_c1y020_l4_100_l2_075_idx05": {
        "w_C1_y":   "0.200000mm",
        "L4_g312g": "1.000000mm",
        "L2_g312g": "0.750000mm",
        "index1":   "0.500000m",
    },
    # c1y=0.25 (best S31) + L4=1.00 (best S21 L4) + small L2 + idx=0.5
    "v04_c1y025_l4_100_l2_075_idx05": {
        "w_C1_y":   "0.250000mm",
        "L4_g312g": "1.000000mm",
        "L2_g312g": "0.750000mm",
        "index1":   "0.500000m",
    },
    # c1y=0.25 + L4=1.00 + smaller L2=0.70
    "v05_c1y025_l4_100_l2_070": {
        "w_C1_y":   "0.250000mm",
        "L4_g312g": "1.000000mm",
        "L2_g312g": "0.700000mm",
        "index1":   "0.600000m",
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
        print(f"  {case}")
    (OUT_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nBuilt {len(manifest)} cases -> {OUT_ROOT}")


if __name__ == "__main__":
    main()
