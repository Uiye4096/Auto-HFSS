"""
Refine12: w_sub=1.7mm, idx=0.6, fine-tune L4_g312g > 1.10mm and L2_g312g.

Key finding from refine11: with 1.7mm substrate + idx=0.6,
L4_g312g=1.10mm gives best crossing (18.408 GHz). Sensitivity direction
shows crossing increases when L4 goes from 1.00→1.10mm (unlike 1.5mm case).
Testing L4=1.15 and 1.20mm to see if crossing keeps rising toward 18.5 GHz.

Also: S31 -3dB stuck at 17.92-18.16. Try larger L2_g312g (0.80, 0.85mm)
to see if LPF edge moves up.
"""
import json
import subprocess
from pathlib import Path

ROOT         = Path(r"D:\Desktop\HFSS_real")
MODEL        = ROOT / "12GHzdiplexer2"
BASE_PROJECT = MODEL / "12GHzdiplexer.aedt"
OUT_ROOT     = MODEL / "derived" / "refine12"
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
    # Push crossing up: L4 > 1.10mm
    "r12_l4_115": {
        "w_sub12G": W_SUB, "w_C1_y": C1Y,
        "L4_g312g": "1.150000mm", "L2_g312g": "0.750000mm", "index1": IDX,
    },
    "r12_l4_120": {
        "w_sub12G": W_SUB, "w_C1_y": C1Y,
        "L4_g312g": "1.200000mm", "L2_g312g": "0.750000mm", "index1": IDX,
    },
    # Push S31 up: larger L2_g312g
    "r12_l4_110_l2_080": {
        "w_sub12G": W_SUB, "w_C1_y": C1Y,
        "L4_g312g": "1.100000mm", "L2_g312g": "0.800000mm", "index1": IDX,
    },
    "r12_l4_110_l2_085": {
        "w_sub12G": W_SUB, "w_C1_y": C1Y,
        "L4_g312g": "1.100000mm", "L2_g312g": "0.850000mm", "index1": IDX,
    },
    # Combined: slightly larger L4 + larger L2
    "r12_l4_115_l2_080": {
        "w_sub12G": W_SUB, "w_C1_y": C1Y,
        "L4_g312g": "1.150000mm", "L2_g312g": "0.800000mm", "index1": IDX,
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
