"""
Refine28 — Improve S11 matching and reduce 20-32 GHz tilt.

Two new bases from refine27:
  A) r27_c1y022   : cross=18.552✓, S31@19=-10.8✓, rip20-25=0.6dB, S11@20=-6.3dB
  B) r27_l2070_c1y022: cross=18.519✓, S31@19=-10.6✓, rip20-25=0.9dB, S11@19=-10.5dB

Best S11 candidate:
  r27_idx050_c1y022: cross=18.588✓, S31@19=-9.9 (barely missing -10), S11min=-9.2dB

Fixed base: k=0.90, w_C=1.45mm, L4=0.85mm

Sweeps:
  S1: L2=0.70mm + index1 in {0.50,0.55,0.65,0.70} (4 cases) — combine best L2 + idx
  S2: index1=0.50, L2=0.75mm + c1y in {0.23,0.24,0.25,0.26} (4 cases)
      — push S31@19 to ≤-10 for best-S11 idx=0.50 branch
  S3: L2 fine in {0.68,0.70,0.72,0.74,0.76} + idx=0.60, c1y=0.22 (3 new)
      — find L2 optimum between 0.70 and 0.75
  S4: L2=0.70, idx=0.60, c1y in {0.20,0.21,0.23,0.24} (3 new)
      — fine c1y around l2070 base
Total: ~14 cases (excluding already-computed from r27)
"""
import json
import subprocess
from pathlib import Path

ROOT         = Path(r"D:\Desktop\HFSS_real")
MODEL        = ROOT / "12GHzdiplexer2"
BASE_PROJECT = MODEL / "12GHzdiplexer.aedt"
OUT_ROOT     = MODEL / "derived" / "refine28"
INSPECT      = ROOT / "tools" / "aedt_inspect.py"

ALIGNMENT = {
    "compensation_y":
        "L2_g212g + cover_HPF_out12g + l_line212g + 1.426mm - l_sub12g",
    "compensation_y_2":
        "l_line312g + l_L512g + l_C412g + l_L312g + l_C212g + "
        "l_L112g + l_line412g - l_sub_LPF12g",
}

L_L5_BASE = 0.770; L_C4_BASE = 0.616; L_L3_BASE = 0.912
L_C2_BASE = 0.506; L_L1_BASE = 0.516
SUM_LPF   = L_L5_BASE + L_C4_BASE + L_L3_BASE + L_C2_BASE + L_L1_BASE

K = 0.90
LPF_SCALE = {
    "l_L512g":      f"{L_L5_BASE * K:.6f}mm",
    "l_C412g":      f"{L_C4_BASE * K:.6f}mm",
    "l_L312g":      f"{L_L3_BASE * K:.6f}mm",
    "l_C212g":      f"{L_C2_BASE * K:.6f}mm",
    "l_L112g":      f"{L_L1_BASE * K:.6f}mm",
    "l_sub_LPF12g": f"{1.02 + SUM_LPF * K:.6f}mm",
}

FIXED = {
    "w_sub12G":  "1.700000mm",
    "w_line12g": "0.395000mm",
    "w_C412g":   "1.450000mm",
    "w_C212g":   "1.450000mm",
    "L4_g312g":  "0.850000mm",
}

CASES = {}

# ── S1: L2=0.70 + index1 sweep ───────────────────────────────────────────────
for idx in [0.50, 0.55, 0.65, 0.70]:
    name = f"r28_l2070_idx{int(idx*100):03d}_c1y022"
    CASES[name] = {**FIXED, **LPF_SCALE,
                   "L2_g312g": "0.700000mm",
                   "index1":   f"{idx:.6f}m",
                   "w_C1_y":   "0.220000mm"}

# ── S2: idx=0.50, L2=0.75 + c1y sweep (fix S31@19 for best-S11 branch) ──────
for c1y in [0.23, 0.24, 0.25, 0.26]:
    name = f"r28_idx050_l2075_c1y{int(c1y*100):03d}"
    CASES[name] = {**FIXED, **LPF_SCALE,
                   "L2_g312g": "0.750000mm",
                   "index1":   "0.500000m",
                   "w_C1_y":   f"{c1y:.6f}mm"}

# ── S3: fine L2 between 0.70-0.76, idx=0.60, c1y=0.22 ───────────────────────
for l2 in [0.68, 0.72, 0.74, 0.76]:
    name = f"r28_l2{int(l2*100):03d}_idx060_c1y022"
    CASES[name] = {**FIXED, **LPF_SCALE,
                   "L2_g312g": f"{l2:.6f}mm",
                   "index1":   "0.600000m",
                   "w_C1_y":   "0.220000mm"}

# ── S4: L2=0.70, idx=0.60, fine c1y ─────────────────────────────────────────
for c1y in [0.20, 0.21, 0.23, 0.24]:
    name = f"r28_l2070_idx060_c1y{int(c1y*100):03d}"
    CASES[name] = {**FIXED, **LPF_SCALE,
                   "L2_g312g": "0.700000mm",
                   "index1":   "0.600000m",
                   "w_C1_y":   f"{c1y:.6f}mm"}


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
