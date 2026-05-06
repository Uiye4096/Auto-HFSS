"""
Second refinement round for 12GHzdiplexer2.
Best directions found from refine round 1:
  - smaller L4_g312g lowers S21 (r03: 0.95mm -> 19.36 GHz)
  - larger  w_C1_y   lowers S21 (r08: 0.20mm -> 19.12 GHz)
  - smaller L2_g312g raises S31 (r05: 0.80mm -> 18.40 GHz)
  - smaller index1   lowers S21 (r06: 0.50m  -> 19.36 GHz)

New cases combine these directions to push both edges toward 18.5 GHz.
"""
import json
import subprocess
from pathlib import Path

ROOT         = Path(r"D:\Desktop\HFSS_real")
MODEL        = ROOT / "12GHzdiplexer2"
BASE_PROJECT = MODEL / "12GHzdiplexer.aedt"
OUT_ROOT     = MODEL / "derived" / "refine2"
INSPECT      = ROOT / "tools" / "aedt_inspect.py"

ALIGNMENT = {
    "compensation_y":   "L2_g212g + cover_HPF_out12g + l_line212g + 1.426mm - l_sub12g",
    "compensation_y_2": (
        "l_line312g + l_L512g + l_C412g + l_L312g + l_C212g + "
        "l_L112g + l_line412g - l_sub_LPF12g"
    ),
}

CASES = {
    # Combine HPF best (w_C1_y=0.20, L4_g312g=0.95) with LPF push (L2_g312g=0.80)
    "s01_c1y02_l4_095_l2_080": {
        "w_C1_y":    "0.200000mm",
        "L4_g312g":  "0.950000mm",
        "L2_g312g":  "0.800000mm",
        "index1":    "0.600000m",
    },
    # Push L4 even lower
    "s02_c1y02_l4_090_l2_080": {
        "w_C1_y":    "0.200000mm",
        "L4_g312g":  "0.900000mm",
        "L2_g312g":  "0.800000mm",
        "index1":    "0.600000m",
    },
    # Combine low index1 with low L4 and high w_C1_y
    "s03_c1y02_l4_095_l2_080_idx05": {
        "w_C1_y":    "0.200000mm",
        "L4_g312g":  "0.950000mm",
        "L2_g312g":  "0.800000mm",
        "index1":    "0.500000m",
    },
    # Very aggressive: lowest L4, high C1y, low index
    "s04_c1y02_l4_085_l2_080_idx05": {
        "w_C1_y":    "0.200000mm",
        "L4_g312g":  "0.850000mm",
        "L2_g312g":  "0.800000mm",
        "index1":    "0.500000m",
    },
    # Keep L2 even smaller to see if S31 can reach 18.5
    "s05_c1y02_l4_095_l2_075": {
        "w_C1_y":    "0.200000mm",
        "L4_g312g":  "0.950000mm",
        "L2_g312g":  "0.750000mm",
        "index1":    "0.600000m",
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
        up_path = case_dir / "updates.json"
        up_path.write_text(json.dumps(updates, indent=2), encoding="utf-8")
        proj_path = case_dir / f"{case}.aedt"
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
