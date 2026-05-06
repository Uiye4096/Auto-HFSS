"""
Refine15: w_C1_y sweep on the ws17_l4_110_idx06 base.

w_C1_y = junction compensation capacitor Y-dimension.
Larger w_C1_y => more shunt capacitance at T-junction =>
  better satisfaction of Im(Yin,LP) + Im(Yin,HP) = 0 =>
  flatter HPF passband, fewer reflections (better S11) in transition.

Base: w_sub=1.7mm, L4=1.10mm, L2=0.75mm, idx=0.6m (crossing=18.408, S31=18.16, IL=-2.9dB)
Sweep w_C1_y from 0.15 to 0.50mm to find the flattest passband.
"""
import json
import subprocess
from pathlib import Path

ROOT         = Path(r"D:\Desktop\HFSS_real")
MODEL        = ROOT / "12GHzdiplexer2"
BASE_PROJECT = MODEL / "12GHzdiplexer.aedt"
OUT_ROOT     = MODEL / "derived" / "refine15"
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
}

C1Y_VALUES = [0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]

CASES = {
    f"r15_c1y_{int(v*100):03d}": {**HPF_BASE, "w_C1_y": f"{v:.6f}mm"}
    for v in C1Y_VALUES
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
        print(f"  {case}  w_C1_y={base_upd['w_C1_y']}")
    (OUT_ROOT / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(f"\nBuilt {len(manifest)} cases -> {OUT_ROOT}")


if __name__ == "__main__":
    main()
