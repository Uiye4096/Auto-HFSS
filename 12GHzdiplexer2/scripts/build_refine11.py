"""
Refine11: fine-tune ws17_l4_110_idx06 (crossing=18.408, S31=18.16).

Target: crossing >= 18.5 GHz AND S31 -3dB >= 18.5 GHz AND no dip.

Knobs:
  - Smaller L4_g312g -> higher crossing (L4=1.05 or 0.95 to push from 18.41 to 18.5)
  - Smaller L2_g312g -> higher S31 (try 0.70 vs 0.75)
  - Larger c1y       -> higher S31 (try 0.35)
"""
import json
import subprocess
from pathlib import Path

ROOT         = Path(r"D:\Desktop\HFSS_real")
MODEL        = ROOT / "12GHzdiplexer2"
BASE_PROJECT = MODEL / "12GHzdiplexer.aedt"
OUT_ROOT     = MODEL / "derived" / "refine11"
INSPECT      = ROOT / "tools" / "aedt_inspect.py"

ALIGNMENT = {
    "compensation_y":   "L2_g212g + cover_HPF_out12g + l_line212g + 1.426mm - l_sub12g",
    "compensation_y_2": (
        "l_line312g + l_L512g + l_C412g + l_L312g + l_C212g + "
        "l_L112g + l_line412g - l_sub_LPF12g"
    ),
}

W_SUB = "1.700000mm"
IDX   = "0.600000m"
C1Y   = "0.300000mm"

CASES = {
    # Push crossing up: smaller L4_g312g (baseline best: 1.10mm -> 18.408 GHz)
    "r11_l4_105": {
        "w_sub12G": W_SUB, "w_C1_y": C1Y,
        "L4_g312g": "1.050000mm", "L2_g312g": "0.750000mm", "index1": IDX,
    },
    "r11_l4_095": {
        "w_sub12G": W_SUB, "w_C1_y": C1Y,
        "L4_g312g": "0.950000mm", "L2_g312g": "0.750000mm", "index1": IDX,
    },
    # Push S31 up: smaller L2_g312g
    "r11_l4_110_l2_070": {
        "w_sub12G": W_SUB, "w_C1_y": C1Y,
        "L4_g312g": "1.100000mm", "L2_g312g": "0.700000mm", "index1": IDX,
    },
    # Larger c1y to push S31 up
    "r11_l4_110_c1y035": {
        "w_sub12G": W_SUB, "w_C1_y": "0.350000mm",
        "L4_g312g": "1.100000mm", "L2_g312g": "0.750000mm", "index1": IDX,
    },
    # Combine: slightly smaller L4 + smaller L2 for both crossing and S31
    "r11_l4_105_l2_070": {
        "w_sub12G": W_SUB, "w_C1_y": C1Y,
        "L4_g312g": "1.050000mm", "L2_g312g": "0.700000mm", "index1": IDX,
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
