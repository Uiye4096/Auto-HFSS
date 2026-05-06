"""
Refine24 — BOLD MOVE: uniform scaling of ALL LPF element lengths.

Core insight: w_C=1.4mm suppresses S31 bump but drops LPF cutoff from
17.7→16 GHz, pulling crossing down to 17.7 GHz.

Solution: scale ALL LPF filter lengths (l_L5, l_C4, l_L3, l_C2, l_L1)
by factor k < 1.0. LPF cutoff rises proportionally: 16 × (1/k).
Also scale l_sub_LPF12g to keep compensation_y_2 ≈ 0.020mm positive.

At k=0.89: LPF cutoff ≈ 16/0.89 = 18.0 GHz  ← target!
At k=0.85: LPF cutoff ≈ 16/0.85 = 18.8 GHz  ← slightly above target

Baseline LPF lengths (w_C=1.4mm gives 16 GHz cutoff):
  l_L512g = 0.770mm
  l_C412g = 0.616mm
  l_L312g = 0.912mm
  l_C212g = 0.506mm
  l_L112g = 0.516mm
  Sum_LPF = 3.320mm
  l_sub_LPF12g = 4.340mm  (= l_line312g[0.04] + Sum_LPF + l_line412g[1.0] - slack[0.02])

Scaled l_sub_LPF12g = 1.02 + 3.320 * k  (keeps slack ≈ 0.02mm)

Sweep:
  k in {0.82, 0.85, 0.88, 0.90, 0.92, 0.95} × w_C in {1.1, 1.4} mm
  + HPF variant (L4=1.10 or 1.15) for key k values
  Total: 12 base + 6 HPF variants = 18 cases, 4-parallel
"""
import json
import subprocess
from pathlib import Path

ROOT         = Path(r"D:\Desktop\HFSS_real")
MODEL        = ROOT / "12GHzdiplexer2"
BASE_PROJECT = MODEL / "12GHzdiplexer.aedt"
OUT_ROOT     = MODEL / "derived" / "refine24"
INSPECT      = ROOT / "tools" / "aedt_inspect.py"

# Baseline LPF lengths (from inspect.json)
L_L5_BASE = 0.770
L_C4_BASE = 0.616
L_L3_BASE = 0.912
L_C2_BASE = 0.506
L_L1_BASE = 0.516
SUM_LPF   = L_L5_BASE + L_C4_BASE + L_L3_BASE + L_C2_BASE + L_L1_BASE  # 3.320mm

ALIGNMENT_TEMPLATE = {
    "compensation_y":
        "L2_g212g + cover_HPF_out12g + l_line212g + 1.426mm - l_sub12g",
    "compensation_y_2":
        "l_line312g + l_L512g + l_C412g + l_L312g + l_C212g + "
        "l_L112g + l_line412g - l_sub_LPF12g",
}

FIXED_HPF = {
    "w_sub12G":  "1.700000mm",
    "w_line12g": "0.395000mm",
    "L4_g312g":  "1.100000mm",
    "L2_g312g":  "0.750000mm",
    "index1":    "0.600000m",
    "w_C1_y":    "0.300000mm",
}

CASES = {}

def add_case(name, k, wc, l4="1.100000mm", l2="0.750000mm", idx="0.600000m"):
    l_sub_lpf = 1.02 + SUM_LPF * k   # = 1.02 + 3.320*k
    CASES[name] = {
        **FIXED_HPF,
        "L4_g312g":      l4,
        "L2_g312g":      l2,
        "index1":        idx,
        # LPF element widths
        "w_C412g":       f"{wc:.6f}mm",
        "w_C212g":       f"{wc:.6f}mm",
        # LPF element lengths (scaled)
        "l_L512g":       f"{L_L5_BASE * k:.6f}mm",
        "l_C412g":       f"{L_C4_BASE * k:.6f}mm",
        "l_L312g":       f"{L_L3_BASE * k:.6f}mm",
        "l_C212g":       f"{L_C2_BASE * k:.6f}mm",
        "l_L112g":       f"{L_L1_BASE * k:.6f}mm",
        # LPF substrate (scaled to keep slack ≈ 0.02mm)
        "l_sub_LPF12g":  f"{l_sub_lpf:.6f}mm",
    }

# ── Base sweep: 6 scale factors × 2 wC values ──────────────────────────────
for k in [0.82, 0.85, 0.88, 0.90, 0.92, 0.95]:
    for wc in [1.1, 1.4]:
        name = f"r24_k{int(k*100):03d}_wC{int(wc*10):02d}"
        add_case(name, k, wc)

# ── HPF variants for k=0.88 and k=0.90 (most likely sweet spots) ────────────
for k, l4 in [(0.88, "1.100000mm"), (0.88, "1.150000mm"),
              (0.90, "1.100000mm"), (0.90, "1.150000mm")]:
    wc = 1.4
    name = f"r24_k{int(k*100):03d}_wC14_l4{int(float(l4[:-2])*100):03d}"
    add_case(name, k, wc, l4=l4)

# ── w_C1_y variant for best expected case ───────────────────────────────────
for c1y in [0.20, 0.25]:
    name = f"r24_k090_wC14_c1y{int(c1y*100):03d}"
    c_dict = {
        **FIXED_HPF,
        "w_C1_y":       f"{c1y:.6f}mm",
        "w_C412g":      "1.400000mm",
        "w_C212g":      "1.400000mm",
        "l_L512g":      f"{L_L5_BASE * 0.90:.6f}mm",
        "l_C412g":      f"{L_C4_BASE * 0.90:.6f}mm",
        "l_L312g":      f"{L_L3_BASE * 0.90:.6f}mm",
        "l_C212g":      f"{L_C2_BASE * 0.90:.6f}mm",
        "l_L112g":      f"{L_L1_BASE * 0.90:.6f}mm",
        "l_sub_LPF12g": f"{1.02 + SUM_LPF * 0.90:.6f}mm",
    }
    CASES[name] = c_dict


def main():
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for case, upd in CASES.items():
        case_dir  = OUT_ROOT / case
        case_dir.mkdir(parents=True, exist_ok=True)
        updates   = dict(upd)
        updates.update(ALIGNMENT_TEMPLATE)
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
        print(f"  {case}  (k={upd.get('l_L512g','?')}→scale)")
    (OUT_ROOT / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(f"\nBuilt {len(manifest)} cases -> {OUT_ROOT}")


if __name__ == "__main__":
    main()
