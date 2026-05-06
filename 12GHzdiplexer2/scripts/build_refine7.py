"""
Refine7: close-in interpolation around the 18.5 GHz target.

Best crossings so far:
  w04: c1y=0.30, idx=0.4  -> crossing=18.747 GHz, S31=18.40 (below target)
  w01: c1y=0.25, idx=0.4  -> crossing=18.919 GHz, S31=18.56 (above target)

Goal: crossing ~18.5 GHz AND S31 >= 18.5 GHz simultaneously.
Strategy: interpolate c1y between 0.25-0.30 with idx=0.4, also try
smaller L2_g312g to push S31 up for the w04-type cases.
"""
import json
import subprocess
from pathlib import Path

ROOT         = Path(r"D:\Desktop\HFSS_real")
MODEL        = ROOT / "12GHzdiplexer2"
BASE_PROJECT = MODEL / "12GHzdiplexer.aedt"
OUT_ROOT     = MODEL / "derived" / "refine7"
INSPECT      = ROOT / "tools" / "aedt_inspect.py"

ALIGNMENT = {
    "compensation_y":   "L2_g212g + cover_HPF_out12g + l_line212g + 1.426mm - l_sub12g",
    "compensation_y_2": (
        "l_line312g + l_L512g + l_C412g + l_L312g + l_C212g + "
        "l_L112g + l_line412g - l_sub_LPF12g"
    ),
}

CASES = {
    # Interpolate c1y between 0.25 and 0.30 (idx=0.4 fixed)
    "x01_c1y027_idx04": {
        "w_C1_y":   "0.270000mm",
        "L4_g312g": "1.000000mm",
        "L2_g312g": "0.750000mm",
        "index1":   "0.400000m",
    },
    "x02_c1y028_idx04": {
        "w_C1_y":   "0.280000mm",
        "L4_g312g": "1.000000mm",
        "L2_g312g": "0.750000mm",
        "index1":   "0.400000m",
    },
    # w04 base + smaller L2 to raise S31
    "x03_c1y030_l2_073_idx04": {
        "w_C1_y":   "0.300000mm",
        "L4_g312g": "1.000000mm",
        "L2_g312g": "0.730000mm",
        "index1":   "0.400000m",
    },
    # w04 base + even smaller L2
    "x04_c1y030_l2_070_idx04": {
        "w_C1_y":   "0.300000mm",
        "L4_g312g": "1.000000mm",
        "L2_g312g": "0.700000mm",
        "index1":   "0.400000m",
    },
    # c1y=0.27 + smaller L2 for S31 boost
    "x05_c1y027_l2_073_idx04": {
        "w_C1_y":   "0.270000mm",
        "L4_g312g": "1.000000mm",
        "L2_g312g": "0.730000mm",
        "index1":   "0.400000m",
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
