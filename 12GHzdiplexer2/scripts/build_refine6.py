"""
Refine6: fine-tune around v04 (crossing=18.80 GHz, target=18.50 GHz).

v04 best params: c1y=0.25, L4_g312g=1.00, L2_g312g=0.75, index1=0.5m
Need crossing to drop 0.3 GHz more.

Sensitivity observed: smaller index1 -> lower crossing (v04 idx=0.5 beat v05 idx=0.6).
Also try: larger c1y (0.30mm), slightly different L2_g312g, L4_g312g.
"""
import json
import subprocess
from pathlib import Path

ROOT         = Path(r"D:\Desktop\HFSS_real")
MODEL        = ROOT / "12GHzdiplexer2"
BASE_PROJECT = MODEL / "12GHzdiplexer.aedt"
OUT_ROOT     = MODEL / "derived" / "refine6"
INSPECT      = ROOT / "tools" / "aedt_inspect.py"

ALIGNMENT = {
    "compensation_y":   "L2_g212g + cover_HPF_out12g + l_line212g + 1.426mm - l_sub12g",
    "compensation_y_2": (
        "l_line312g + l_L512g + l_C412g + l_L312g + l_C212g + "
        "l_L112g + l_line412g - l_sub_LPF12g"
    ),
}

CASES = {
    # Push index1 lower
    "w01_idx04": {
        "w_C1_y":   "0.250000mm",
        "L4_g312g": "1.000000mm",
        "L2_g312g": "0.750000mm",
        "index1":   "0.400000m",
    },
    "w02_idx03": {
        "w_C1_y":   "0.250000mm",
        "L4_g312g": "1.000000mm",
        "L2_g312g": "0.750000mm",
        "index1":   "0.300000m",
    },
    # Larger c1y
    "w03_c1y030": {
        "w_C1_y":   "0.300000mm",
        "L4_g312g": "1.000000mm",
        "L2_g312g": "0.750000mm",
        "index1":   "0.500000m",
    },
    # Larger c1y + lower index1
    "w04_c1y030_idx04": {
        "w_C1_y":   "0.300000mm",
        "L4_g312g": "1.000000mm",
        "L2_g312g": "0.750000mm",
        "index1":   "0.400000m",
    },
    # Slightly smaller L2 with best other params
    "w05_l2_072_idx05": {
        "w_C1_y":   "0.250000mm",
        "L4_g312g": "1.000000mm",
        "L2_g312g": "0.720000mm",
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
        print(f"  {case}")
    (OUT_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nBuilt {len(manifest)} cases -> {OUT_ROOT}")


if __name__ == "__main__":
    main()
