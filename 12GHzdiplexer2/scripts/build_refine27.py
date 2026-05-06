"""
Refine27 — Phase D: Fine polish of winning configuration.

Winner (r26_wC145_k090_l4085_c1y022):
  cross=18.552✓, S31@19=-10.8✓, S31@20=-15.8✓
  S21: @19=-3.5  @20=-2.5  @21=-3.0  @22=-3.1  @25=-2.9  @28=-2.0  @32=-0.7
  S11: @18=-3.3  @19=-7.8  @20=-6.3  @21=-4.5  @22=-3.9  → poor matching 18-22 GHz
  IL variation 20-28 GHz: 1.1 dB (close to 1dB target!)

Goals:
  1. Improve S11 matching in 18-22 GHz → reduce dip at @19=-3.5 dB
  2. Push 20-28 GHz ripple toward ≤ 1 dB
  3. Keep crossing ≥ 18.5 GHz, S31@19 ≤ -10 dB

Base: k=0.90, w_C=1.45mm, L4=0.85mm, L2=0.75mm, idx=0.6

Sweeps:
  S1: c1y in {0.20,0.21,0.22,0.23,0.24,0.25,0.26,0.28,0.30} (9 cases)
      → fine-tune T-junction admittance matching
  S2: L2_g312g in {0.60,0.65,0.70,0.75,0.80,0.85,0.90} at c1y=0.22 (6 new)
      → adjust HPF shunt inductor gap for mid-band flatness
  S3: index1 in {0.50,0.55,0.60,0.65,0.70} at c1y=0.22, L2=0.75 (4 new)
      → fine HPF characteristic admittance
  S4: L4 fine {0.84,0.86,0.88} at c1y=0.22 (3 cases)
      → check sensitivity around L4=0.85mm
Total: 22 cases, 4-parallel
"""
import json
import subprocess
from pathlib import Path

ROOT         = Path(r"D:\Desktop\HFSS_real")
MODEL        = ROOT / "12GHzdiplexer2"
BASE_PROJECT = MODEL / "12GHzdiplexer.aedt"
OUT_ROOT     = MODEL / "derived" / "refine27"
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

# ── S1: fine c1y sweep ────────────────────────────────────────────────────────
for c1y in [0.20, 0.21, 0.22, 0.23, 0.24, 0.25, 0.26, 0.28, 0.30]:
    name = f"r27_c1y{int(c1y*100):03d}"
    CASES[name] = {**FIXED, **LPF_SCALE,
                   "L2_g312g": "0.750000mm",
                   "index1":   "0.600000m",
                   "w_C1_y":   f"{c1y:.6f}mm"}

# ── S2: L2 sweep at c1y=0.22 ─────────────────────────────────────────────────
for l2 in [0.60, 0.65, 0.70, 0.80, 0.85, 0.90]:
    name = f"r27_l2{int(l2*100):03d}_c1y022"
    CASES[name] = {**FIXED, **LPF_SCALE,
                   "L2_g312g": f"{l2:.6f}mm",
                   "index1":   "0.600000m",
                   "w_C1_y":   "0.220000mm"}

# ── S3: index1 sweep at c1y=0.22 ─────────────────────────────────────────────
for idx in [0.50, 0.55, 0.65, 0.70]:
    name = f"r27_idx{int(idx*100):03d}_c1y022"
    CASES[name] = {**FIXED, **LPF_SCALE,
                   "L2_g312g": "0.750000mm",
                   "index1":   f"{idx:.6f}m",
                   "w_C1_y":   "0.220000mm"}

# ── S4: fine L4 variation at c1y=0.22 ────────────────────────────────────────
for l4 in [0.84, 0.86, 0.88]:
    name = f"r27_l4{int(l4*100):03d}_c1y022"
    CASES[name] = {**FIXED, **LPF_SCALE,
                   "L4_g312g": f"{l4:.6f}mm",
                   "L2_g312g": "0.750000mm",
                   "index1":   "0.600000m",
                   "w_C1_y":   "0.220000mm"}


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
