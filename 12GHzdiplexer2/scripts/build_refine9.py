"""
Refine9: push L4_g312g smaller to improve S11@20-22GHz (reduce dip)
while keeping crossing near 18.5 GHz.

Finding: L4_g312g=0.90 (u05) gives S11@21=-4.4dB, shallower dip than 1.00mm.
Hypothesis: even smaller L4_g312g improves complementary matching further.

Combine with:
  idx=0.4 (best crossing direction)
  c1y=0.25-0.30 (helps S31 and junction cap compensation)
  l_line312g=0.10mm (small benefit from refine8)
"""
import json
import subprocess
from pathlib import Path

ROOT         = Path(r"D:\Desktop\HFSS_real")
MODEL        = ROOT / "12GHzdiplexer2"
BASE_PROJECT = MODEL / "12GHzdiplexer.aedt"
OUT_ROOT     = MODEL / "derived" / "refine9"
INSPECT      = ROOT / "tools" / "aedt_inspect.py"

ALIGNMENT = {
    "compensation_y":   "L2_g212g + cover_HPF_out12g + l_line212g + 1.426mm - l_sub12g",
    "compensation_y_2": (
        "l_line312g + l_L512g + l_C412g + l_L312g + l_C212g + "
        "l_L112g + l_line412g - l_sub_LPF12g"
    ),
}

CASES = {
    # Smaller L4_g312g sweep (u05 base + idx=0.4)
    "z01_l4_085_idx04": {
        "w_C1_y":    "0.250000mm",
        "L4_g312g":  "0.850000mm",
        "L2_g312g":  "0.800000mm",
        "index1":    "0.400000m",
        "l_line312g":"0.100000mm",
    },
    "z02_l4_080_idx04": {
        "w_C1_y":    "0.250000mm",
        "L4_g312g":  "0.800000mm",
        "L2_g312g":  "0.800000mm",
        "index1":    "0.400000m",
        "l_line312g":"0.100000mm",
    },
    "z03_l4_075_idx04": {
        "w_C1_y":    "0.250000mm",
        "L4_g312g":  "0.750000mm",
        "L2_g312g":  "0.800000mm",
        "index1":    "0.400000m",
        "l_line312g":"0.100000mm",
    },
    # Best dip + c1y=0.30 for S31
    "z04_l4_085_c1y030_idx04": {
        "w_C1_y":    "0.300000mm",
        "L4_g312g":  "0.850000mm",
        "L2_g312g":  "0.800000mm",
        "index1":    "0.400000m",
        "l_line312g":"0.100000mm",
    },
    # Combine smallest L4 with c1y=0.30
    "z05_l4_080_c1y030_l2_075_idx04": {
        "w_C1_y":    "0.300000mm",
        "L4_g312g":  "0.800000mm",
        "L2_g312g":  "0.750000mm",
        "index1":    "0.400000m",
        "l_line312g":"0.100000mm",
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
