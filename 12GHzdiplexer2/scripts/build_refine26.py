"""
Refine26 — Closing the gap: S31@19 GHz from -8.8 → -10 dB.

Best current: r25_k090_l4085_c1y020
  cross=18.649✓, S31@19=-8.8 dB (-1.2 dB short of target), IL=-3.8 dB (best)

Two approaches:
  S1: Increase w_C (more shunt cap → better stopband at 19 GHz)
      k=0.90, L4=0.85, c1y=0.20, w_C in {1.40,1.43,1.46,1.50,1.55,1.60} (6)
  S2: Fine-tune k around 0.90 (shift transmission zeros)
      k in {0.87,0.88,0.89,0.91}, L4=0.85, c1y=0.20, w_C=1.40 (4)
  S3: Fine-tune L4 in {0.83,0.87,0.88,0.91,0.92,0.93} at k=0.90, c1y=0.20 (6)
  S4: Combine best k and w_C: k=0.90, L4=0.85, w_C=1.45, c1y in {0.18,0.20,0.22} (3)
Total: 19 cases, 4-parallel
"""
import json
import subprocess
from pathlib import Path

ROOT         = Path(r"D:\Desktop\HFSS_real")
MODEL        = ROOT / "12GHzdiplexer2"
BASE_PROJECT = MODEL / "12GHzdiplexer.aedt"
OUT_ROOT     = MODEL / "derived" / "refine26"
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

def lpf_lengths(k):
    return {
        "l_L512g":      f"{L_L5_BASE * k:.6f}mm",
        "l_C412g":      f"{L_C4_BASE * k:.6f}mm",
        "l_L312g":      f"{L_L3_BASE * k:.6f}mm",
        "l_C212g":      f"{L_C2_BASE * k:.6f}mm",
        "l_L112g":      f"{L_L1_BASE * k:.6f}mm",
        "l_sub_LPF12g": f"{1.02 + SUM_LPF * k:.6f}mm",
    }

FIXED_HPF = {
    "w_sub12G":  "1.700000mm",
    "w_line12g": "0.395000mm",
    "L2_g312g":  "0.750000mm",
    "index1":    "0.600000m",
}

CASES = {}

# ── S1: sweep w_C at k=0.90, L4=0.85, c1y=0.20 ──────────────────────────────
for wc in [1.40, 1.43, 1.46, 1.50, 1.55, 1.60]:
    name = f"r26_wC{int(wc*100):03d}_k090_l4085_c1y020"
    CASES[name] = {**FIXED_HPF, **lpf_lengths(0.90),
                   "w_C412g": f"{wc:.6f}mm",
                   "w_C212g": f"{wc:.6f}mm",
                   "L4_g312g": "0.850000mm",
                   "w_C1_y":   "0.200000mm"}

# ── S2: fine k sweep at L4=0.85, c1y=0.20, w_C=1.40 ─────────────────────────
for k in [0.87, 0.88, 0.89, 0.91]:
    name = f"r26_k{int(k*100):03d}_l4085_c1y020"
    CASES[name] = {**FIXED_HPF, **lpf_lengths(k),
                   "w_C412g": "1.400000mm",
                   "w_C212g": "1.400000mm",
                   "L4_g312g": "0.850000mm",
                   "w_C1_y":   "0.200000mm"}

# ── S3: fine L4 sweep at k=0.90, c1y=0.20, w_C=1.40 ─────────────────────────
for l4 in [0.83, 0.87, 0.88, 0.91, 0.92, 0.93]:
    name = f"r26_l4{int(l4*100):03d}_k090_c1y020"
    CASES[name] = {**FIXED_HPF, **lpf_lengths(0.90),
                   "w_C412g": "1.400000mm",
                   "w_C212g": "1.400000mm",
                   "L4_g312g": f"{l4:.6f}mm",
                   "w_C1_y":   "0.200000mm"}

# ── S4: best k+w_C combination with c1y variation ────────────────────────────
for c1y in [0.18, 0.20, 0.22]:
    name = f"r26_wC145_k090_l4085_c1y{int(c1y*100):03d}"
    CASES[name] = {**FIXED_HPF, **lpf_lengths(0.90),
                   "w_C412g": "1.450000mm",
                   "w_C212g": "1.450000mm",
                   "L4_g312g": "0.850000mm",
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
