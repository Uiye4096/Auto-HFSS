"""
Refine30 — Raise crossing of 185g-LPF design from 18.347 → 18.5+ GHz.

r29_185lpf_wC145_l2075 (185g non-uniform LPF, wC=1.45, L4=0.85, L2=0.75, c1y=0.22):
  cross=18.347 (153 MHz short), S31@19=-13.5✓, S31@20=-16.6✓, rip25=1.2 dB

185g base lengths: l_L5=0.7248, l_C4=0.46508, l_L3=0.9362, l_C2=0.52548, l_L1=0.6946
                   sum=3.30616mm  l_sub=1.04+3.30616=4.34616mm

Strategy: apply additional k-factor to 185g lengths (k < 1.0 → shorter → higher crossing)

Sweeps:
  S1: k in {0.92,0.93,0.94,0.95,0.96,0.97,0.98} on 185g LPF, c1y=0.22 (7 cases)
  S2: best k from S1 × c1y in {0.18,0.20,0.22,0.24,0.26} (4 new)
  S3: best k × L4_g3 in {0.80,0.83,0.85,0.87} (2 new, 0.85 exists)
  S4: best k × L2_g3 in {0.70,0.75,0.80,0.85} (2 new, 0.75 exists)
Total: ~15 cases
"""
import json
import subprocess
from pathlib import Path

ROOT         = Path(r"D:\Desktop\HFSS_real")
MODEL        = ROOT / "12GHzdiplexer2"
BASE_PROJECT = MODEL / "12GHzdiplexer.aedt"
OUT_ROOT     = MODEL / "derived" / "refine30"
INSPECT      = ROOT / "tools" / "aedt_inspect.py"

ALIGNMENT = {
    "compensation_y":
        "L2_g212g + cover_HPF_out12g + l_line212g + 1.426mm - l_sub12g",
    "compensation_y_2":
        "l_line312g + l_L512g + l_C412g + l_L312g + l_C212g + "
        "l_L112g + l_line412g - l_sub_LPF12g",
}

# 185g base LPF lengths (non-uniform reference)
L5_185 = 0.7248
L_C4_185 = 0.46508
L3_185 = 0.9362
L_C2_185 = 0.52548
L1_185 = 0.6946
SUM_185 = L5_185 + L_C4_185 + L3_185 + L_C2_185 + L1_185  # 3.30616

def lpf_185_scaled(k):
    s = SUM_185 * k
    return {
        "l_L512g":      f"{L5_185   * k:.6f}mm",
        "l_C412g":      f"{L_C4_185 * k:.6f}mm",
        "l_L312g":      f"{L3_185   * k:.6f}mm",
        "l_C212g":      f"{L_C2_185 * k:.6f}mm",
        "l_L112g":      f"{L1_185   * k:.6f}mm",
        "l_sub_LPF12g": f"{1.04 + s:.6f}mm",
    }

FIXED = {
    "w_sub12G":  "1.700000mm",
    "w_line12g": "0.395000mm",
    "w_C412g":   "1.450000mm",
    "w_C212g":   "1.450000mm",
    "L4_g312g":  "0.850000mm",
    "L2_g312g":  "0.750000mm",
    "index1":    "0.600000m",
    "w_C1_y":    "0.220000mm",
}

CASES = {}

# ── S1: k sweep on 185g LPF lengths ──────────────────────────────────────────
for k in [0.92, 0.93, 0.94, 0.95, 0.96, 0.97, 0.98]:
    name = f"r30_185k{int(k*100):03d}_wC145_c1y022"
    CASES[name] = {**FIXED, **lpf_185_scaled(k)}

# ── S2: c1y sweep at the crossing-optimal k (expect ~0.95 from S1) ───────────
for c1y in [0.18, 0.20, 0.24, 0.26]:
    name = f"r30_185k095_wC145_c1y{int(c1y*100):03d}"
    CASES[name] = {**FIXED, **lpf_185_scaled(0.95),
                   "w_C1_y": f"{c1y:.6f}mm"}

# ── S3: L4_g3 variation at k=0.95 (0.85 already computed in S1) ──────────────
for l4 in [0.80, 0.83, 0.87]:
    name = f"r30_185k095_l4{int(l4*100):03d}_c1y022"
    CASES[name] = {**FIXED, **lpf_185_scaled(0.95),
                   "L4_g312g": f"{l4:.6f}mm"}

# ── S4: L2_g3 variation at k=0.95 ────────────────────────────────────────────
for l2 in [0.70, 0.80, 0.85]:
    name = f"r30_185k095_l2{int(l2*100):03d}_c1y022"
    CASES[name] = {**FIXED, **lpf_185_scaled(0.95),
                   "L2_g312g": f"{l2:.6f}mm"}


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
