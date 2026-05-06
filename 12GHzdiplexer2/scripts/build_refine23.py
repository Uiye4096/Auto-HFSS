"""
Refine23 — Phase C: w_C1_y sweep on top candidates.

Best candidates from Phase B (w_C=1.4mm, bump suppressed):
  A: L4=1.14mm, L2=0.65mm, idx=0.6  → cross=17.810, bump=-10.3✓, IL=-4.2 dB
  B: L4=1.14mm, L2=0.75mm, idx=0.6  → cross=17.650, bump=-11.2✓, IL=-3.0 dB (best IL)
  C: L4=1.10mm, L2=0.75mm, idx=0.6  → cross=17.721, bump=-10.4✓, IL=-3.4 dB

w_C1_y is the T-junction shunt compensation capacitor (Y-size).
It tunes the complementary admittance condition Im(Y_LPF)+Im(Y_HPF)=0 at fT.
A well-chosen w_C1_y should flatten the HPF passband and reduce S11.

Sweep: w_C1_y in {0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50} mm
       × 3 base configurations = 27 cases, 4-parallel
"""
import json
import subprocess
from pathlib import Path

ROOT         = Path(r"D:\Desktop\HFSS_real")
MODEL        = ROOT / "12GHzdiplexer2"
BASE_PROJECT = MODEL / "12GHzdiplexer.aedt"
OUT_ROOT     = MODEL / "derived" / "refine23"
INSPECT      = ROOT / "tools" / "aedt_inspect.py"

ALIGNMENT = {
    "compensation_y":
        "L2_g212g + cover_HPF_out12g + l_line212g + 1.426mm - l_sub12g",
    "compensation_y_2":
        "l_line312g + l_L512g + l_C412g + l_L312g + l_C212g + "
        "l_L112g + l_line412g - l_sub_LPF12g",
}

FIXED = {
    "w_sub12G":  "1.700000mm",
    "w_line12g": "0.395000mm",
    "w_C412g":   "1.400000mm",
    "w_C212g":   "1.400000mm",
    "index1":    "0.600000m",
}

BASES = {
    "A": {"L4_g312g": "1.140000mm", "L2_g312g": "0.650000mm"},
    "B": {"L4_g312g": "1.140000mm", "L2_g312g": "0.750000mm"},
    "C": {"L4_g312g": "1.100000mm", "L2_g312g": "0.750000mm"},
}

C1Y_VALUES = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]

CASES = {}
for base_name, base_params in BASES.items():
    for c1y in C1Y_VALUES:
        name = f"r23_{base_name}_c1y{int(c1y*100):03d}"
        CASES[name] = {**FIXED, **base_params,
                       "w_C1_y": f"{c1y:.6f}mm"}


def main():
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for case, upd in CASES.items():
        case_dir  = OUT_ROOT / case
        case_dir.mkdir(parents=True, exist_ok=True)
        updates   = dict(upd)
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
            "case": case, "updates": upd,
            "project_path": str(proj_path),
            "output_dir":   str(case_dir / "sim"),
        })
        print(f"  {case}")
    (OUT_ROOT / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(f"\nBuilt {len(manifest)} cases -> {OUT_ROOT}")


if __name__ == "__main__":
    main()
