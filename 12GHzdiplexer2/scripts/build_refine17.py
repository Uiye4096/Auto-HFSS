"""
Refine17: push LPF cutoff UP by reducing shunt capacitor widths.

Paper method: LPF cutoff ∝ 1/sqrt(LC). Reducing shunt cap width (w_C)
  → less C → higher f_LPF → raises S31 -3dB and crossing frequency.

w_C412g and w_C212g are INDEPENDENT of compensation_y constraints
(those only depend on l_ length variables), so this is safe to change.

Base: ws17_l4_110_idx06 (w_sub=1.7mm, L4=1.10, L2=0.75, idx=0.6, c1y=0.30)
  S31=18.16 GHz, crossing=18.41 GHz, HPF worst IL=-3.2 dB (no dip)

Sweep w_C412g = w_C212g from 1.10mm down to 0.80mm.
Target: S31 reaches 18.5 GHz with crossing also near 18.5 GHz.
"""
import json
import subprocess
from pathlib import Path

ROOT         = Path(r"D:\Desktop\HFSS_real")
MODEL        = ROOT / "12GHzdiplexer2"
BASE_PROJECT = MODEL / "12GHzdiplexer.aedt"
OUT_ROOT     = MODEL / "derived" / "refine17"
INSPECT      = ROOT / "tools" / "aedt_inspect.py"

ALIGNMENT = {
    "compensation_y":   "L2_g212g + cover_HPF_out12g + l_line212g + 1.426mm - l_sub12g",
    "compensation_y_2": (
        "l_line312g + l_L512g + l_C412g + l_L312g + l_C212g + "
        "l_L112g + l_line412g - l_sub_LPF12g"
    ),
}

HPF_BASE = {
    "w_sub12G":  "1.700000mm",
    "L4_g312g":  "1.100000mm",
    "L2_g312g":  "0.750000mm",
    "index1":    "0.600000m",
    "w_C1_y":    "0.300000mm",
}

# w_C412g = w_C212g values to test
WC_VALUES = [1.10, 1.05, 1.00, 0.95, 0.90, 0.85, 0.80]

CASES = {
    f"r17_wC_{int(v*100):03d}": {
        **HPF_BASE,
        "w_C412g": f"{v:.6f}mm",
        "w_C212g": f"{v:.6f}mm",
    }
    for v in WC_VALUES
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
        print(f"  {case}  w_C={base_upd['w_C412g']}")
    (OUT_ROOT / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(f"\nBuilt {len(manifest)} cases -> {OUT_ROOT}")


if __name__ == "__main__":
    main()
