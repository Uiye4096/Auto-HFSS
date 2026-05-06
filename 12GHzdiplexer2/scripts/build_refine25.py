"""
Refine25 — Fine-tune around best: k=0.90, w_C=1.4mm, c1y=0.20 (cross=18.304 GHz).

Issue: S21 dip at 20-21 GHz (S21=-4.7 dB), S11=-3 dB there → poor HPF matching.
Goal:  Fix the S21 dip while keeping crossing ≥ 18.3 GHz.

LPF scale: k=0.90 → l_sub_LPF12g = 1.02 + 3.320*0.90 = 4.008mm
  l_L512g=0.693mm, l_C412g=0.554mm, l_L312g=0.821mm, l_C212g=0.455mm, l_L112g=0.464mm

Sweeps:
  S1: c1y=0.20, L4 in {0.85,0.90,0.95,1.00,1.05,1.10,1.15,1.20} (8 cases)
      → find L4 that flattens S21 and keeps crossing ≥ 18.3 GHz
  S2: c1y=0.20, L2 in {0.55,0.60,0.65,0.70,0.75,0.80,0.85} (7 cases)
      → find L2 that flattens S21
  S3: L4=1.10, L2=0.75, c1y in {0.12,0.15,0.18,0.20,0.22,0.25} (6 cases)
      → fine c1y resolution around best
  S4: k=0.91 and k=0.92, c1y=0.20, L4=1.10 (2 cases)
      → intermediate k to find bump crossover point
Total: 23 cases, 4-parallel
"""
import json
import subprocess
from pathlib import Path

ROOT         = Path(r"D:\Desktop\HFSS_real")
MODEL        = ROOT / "12GHzdiplexer2"
BASE_PROJECT = MODEL / "12GHzdiplexer.aedt"
OUT_ROOT     = MODEL / "derived" / "refine25"
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
SUM_LPF   = L_L5_BASE + L_C4_BASE + L_L3_BASE + L_C2_BASE + L_L1_BASE  # 3.320

def lpf_lengths(k):
    return {
        "l_L512g":      f"{L_L5_BASE * k:.6f}mm",
        "l_C412g":      f"{L_C4_BASE * k:.6f}mm",
        "l_L312g":      f"{L_L3_BASE * k:.6f}mm",
        "l_C212g":      f"{L_C2_BASE * k:.6f}mm",
        "l_L112g":      f"{L_L1_BASE * k:.6f}mm",
        "l_sub_LPF12g": f"{1.02 + SUM_LPF * k:.6f}mm",
    }

FIXED = {
    "w_sub12G":  "1.700000mm",
    "w_line12g": "0.395000mm",
    "w_C412g":   "1.400000mm",
    "w_C212g":   "1.400000mm",
}

CASES = {}

# ── S1: sweep L4_g312g at k=0.90, c1y=0.20 ──────────────────────────────────
for l4 in [0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15, 1.20]:
    name = f"r25_k090_l4{int(l4*100):03d}_c1y020"
    CASES[name] = {**FIXED, **lpf_lengths(0.90),
                   "L4_g312g": f"{l4:.6f}mm",
                   "L2_g312g": "0.750000mm",
                   "index1":   "0.600000m",
                   "w_C1_y":   "0.200000mm"}

# ── S2: sweep L2_g312g at k=0.90, c1y=0.20, L4=1.10 ─────────────────────────
for l2 in [0.55, 0.60, 0.65, 0.70, 0.80, 0.85, 0.90]:
    name = f"r25_k090_l4110_l2{int(l2*100):03d}_c1y020"
    CASES[name] = {**FIXED, **lpf_lengths(0.90),
                   "L4_g312g": "1.100000mm",
                   "L2_g312g": f"{l2:.6f}mm",
                   "index1":   "0.600000m",
                   "w_C1_y":   "0.200000mm"}

# ── S3: fine c1y sweep at k=0.90, L4=1.10, L2=0.75 ──────────────────────────
for c1y in [0.12, 0.15, 0.18, 0.22, 0.25, 0.28]:
    name = f"r25_k090_l4110_c1y{int(c1y*100):03d}"
    CASES[name] = {**FIXED, **lpf_lengths(0.90),
                   "L4_g312g": "1.100000mm",
                   "L2_g312g": "0.750000mm",
                   "index1":   "0.600000m",
                   "w_C1_y":   f"{c1y:.6f}mm"}

# ── S4: intermediate k values at c1y=0.20 ────────────────────────────────────
for k in [0.91, 0.92]:
    name = f"r25_k{int(k*100):03d}_c1y020"
    CASES[name] = {**FIXED, **lpf_lengths(k),
                   "L4_g312g": "1.100000mm",
                   "L2_g312g": "0.750000mm",
                   "index1":   "0.600000m",
                   "w_C1_y":   "0.200000mm"}


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
