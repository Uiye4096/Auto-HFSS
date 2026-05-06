"""
Refine4: attack the S21=19.92 GHz floor by varying the HPF
shunt-inductor strip widths (w_L412g, w_L212g).

Per Rehner 2009: parallel inductances L2, L4 are realized by
short-circuit high-impedance stubs. Narrower strip = higher impedance
= more inductance per unit length = lower resonant frequency.

Model 2 baseline:
  w_L412g = (0.056 * 0.2) mm = 0.0112 mm
  w_L212g = (0.032 * 0.2) mm = 0.0064 mm

We override these expressions with fixed values at 0.5x and 0.25x.

Also try w_C1 (junction cap X-width, baseline 0.37mm) -- unexplored.

LPF base: s02 best (L4_g312g=0.90, L2_g312g=0.80, w_C1_y=0.20, idx=0.6)
"""
import json
import subprocess
from pathlib import Path

ROOT         = Path(r"D:\Desktop\HFSS_real")
MODEL        = ROOT / "12GHzdiplexer2"
BASE_PROJECT = MODEL / "12GHzdiplexer.aedt"
OUT_ROOT     = MODEL / "derived" / "refine4"
INSPECT      = ROOT / "tools" / "aedt_inspect.py"

ALIGNMENT = {
    "compensation_y":   "L2_g212g + cover_HPF_out12g + l_line212g + 1.426mm - l_sub12g",
    "compensation_y_2": (
        "l_line312g + l_L512g + l_C412g + l_L312g + l_C212g + "
        "l_L112g + l_line412g - l_sub_LPF12g"
    ),
}

# s02 best HPF/LPF anchor
BASE = {
    "w_C1_y":   "0.200000mm",
    "L4_g312g": "0.900000mm",
    "L2_g312g": "0.800000mm",
    "index1":   "0.600000m",
}

CASES = {
    # Thinner inductors: 0.5x current width
    "u01_wL_half": {
        **BASE,
        "w_L412g": "0.005600mm",   # 0.5 * 0.0112
        "w_L212g": "0.003200mm",   # 0.5 * 0.0064
    },
    # Thinner inductors: 0.25x current width
    "u02_wL_quarter": {
        **BASE,
        "w_L412g": "0.002800mm",   # 0.25 * 0.0112
        "w_L212g": "0.001600mm",   # 0.25 * 0.0064
    },
    # Thinner L4 only (keep L2 baseline)
    "u03_wL4_half": {
        **BASE,
        "w_L412g": "0.005600mm",
    },
    # Larger junction cap (w_C1): untested variable
    "u04_wC1_wide": {
        **BASE,
        "w_C1": "0.500000mm",      # baseline 0.37mm
    },
    # Larger w_C1_y beyond current max
    "u05_c1y_025": {
        **BASE,
        "w_C1_y": "0.250000mm",    # baseline sweep max was 0.20mm
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
        print(f"  {case}: wL412g={base_upd.get('w_L412g','expr')}  wL212g={base_upd.get('w_L212g','expr')}  wC1={base_upd.get('w_C1','0.37')}  c1y={base_upd.get('w_C1_y','')}")
    (OUT_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nBuilt {len(manifest)} cases -> {OUT_ROOT}")


if __name__ == "__main__":
    main()
