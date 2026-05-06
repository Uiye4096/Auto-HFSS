"""
Refine18: 2D sweep w_C412g/w_C212g × w_C1_y.

Key finding from refine17:
  w_C=1.10mm: cross=18.408, S31=18.16, IL=-3.2 dB (flat but below 18.5)
  w_C=0.85mm: cross=18.604✓, S31=18.32✓, IL=-5.9 dB (above 18.5! but big dip)
  -> w_C=0.85mm pushes crossing and S31 above target, need c1y to flatten passband.

Strategy: sweep w_C in [0.85, 0.87, 0.90]mm AND c1y in [0.20,0.25,0.30,0.35,0.40]mm.
Find (w_C, c1y) that achieves crossing>=18.5 AND flat passband.

Base: w_sub=1.7mm, L4=1.10mm, L2=0.75mm, idx=0.6m
"""
import json
import subprocess
from pathlib import Path

ROOT         = Path(r"D:\Desktop\HFSS_real")
MODEL        = ROOT / "12GHzdiplexer2"
BASE_PROJECT = MODEL / "12GHzdiplexer.aedt"
OUT_ROOT     = MODEL / "derived" / "refine18"
INSPECT      = ROOT / "tools" / "aedt_inspect.py"

ALIGNMENT = {
    "compensation_y":   "L2_g212g + cover_HPF_out12g + l_line212g + 1.426mm - l_sub12g",
    "compensation_y_2": (
        "l_line312g + l_L512g + l_C412g + l_L312g + l_C212g + "
        "l_L112g + l_line412g - l_sub_LPF12g"
    ),
}

WC_VALUES  = [0.85, 0.87, 0.90]
C1Y_VALUES = [0.20, 0.25, 0.30, 0.35, 0.40]

CASES = {}
for wc in WC_VALUES:
    for c1y in C1Y_VALUES:
        name = f"r18_wC{int(wc*100):03d}_c1y{int(c1y*100):03d}"
        CASES[name] = {
            "w_sub12G":  "1.700000mm",
            "L4_g312g":  "1.100000mm",
            "L2_g312g":  "0.750000mm",
            "index1":    "0.600000m",
            "w_C412g":   f"{wc:.6f}mm",
            "w_C212g":   f"{wc:.6f}mm",
            "w_C1_y":    f"{c1y:.6f}mm",
        }


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
