"""
Refine21 — Phase B: Re-tune HPF crossing frequency.

After Phase A:
  w_C=1.4mm: S31 bump eliminated (≤-10 dB), worst IL=-3.3 dB, crossing~18.0 GHz
  w_C=1.5mm: S31 bump deep (≤-14.6 dB), worst IL=-3.2 dB, crossing~17.6 GHz

Goal: push crossing to ≥18.5 GHz while keeping S31 suppressed.

Strategy: sweep L4_g312g and index1 to raise HPF passband edge.
Also include combined A1+A2 cases (w_C=1.4mm + l_C redistribution).

Sweep grid:
  Base wC=1.4mm: L4 in {1.10,1.15,1.20,1.25,1.30} x idx in {0.5,0.6,0.7} → 15 cases
  Base wC=1.5mm: L4 in {1.10,1.15,1.20,1.25}     x idx in {0.5,0.6}     → 8  cases
  A1+A2 combo : wC=1.4mm + l_C=0.580/0.542,  L4 in {1.10,1.15,1.20}     → 3  cases
Total: 26 cases, run 4-parallel
"""
import json
import subprocess
from pathlib import Path

ROOT         = Path(r"D:\Desktop\HFSS_real")
MODEL        = ROOT / "12GHzdiplexer2"
BASE_PROJECT = MODEL / "12GHzdiplexer.aedt"
OUT_ROOT     = MODEL / "derived" / "refine21"
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
    "L2_g312g":  "0.750000mm",
    "w_C1_y":    "0.300000mm",
}

CASES = {}

# ── B1: wC=1.4mm sweep L4 × index1 ─────────────────────────────────────────
for l4 in [1.10, 1.15, 1.20, 1.25, 1.30]:
    for idx in [0.5, 0.6, 0.7]:
        name = f"r21_wC14_l4{int(l4*100):03d}_idx{int(idx*10):02d}"
        CASES[name] = {**FIXED,
                       "w_C412g":  "1.400000mm",
                       "w_C212g":  "1.400000mm",
                       "L4_g312g": f"{l4:.6f}mm",
                       "index1":   f"{idx:.6f}m"}

# ── B2: wC=1.5mm sweep L4 × index1 ─────────────────────────────────────────
for l4 in [1.10, 1.15, 1.20, 1.25]:
    for idx in [0.5, 0.6]:
        name = f"r21_wC15_l4{int(l4*100):03d}_idx{int(idx*10):02d}"
        CASES[name] = {**FIXED,
                       "w_C412g":  "1.500000mm",
                       "w_C212g":  "1.500000mm",
                       "L4_g312g": f"{l4:.6f}mm",
                       "index1":   f"{idx:.6f}m"}

# ── B3: A1+A2 combo (wC=1.4mm + l_C redistribution) ────────────────────────
for l4 in [1.10, 1.15, 1.20]:
    name = f"r21_combo14_l4{int(l4*100):03d}"
    CASES[name] = {**FIXED,
                   "w_C412g":  "1.400000mm",
                   "w_C212g":  "1.400000mm",
                   "l_C412g":  "0.580000mm",
                   "l_C212g":  "0.542000mm",
                   "L4_g312g": f"{l4:.6f}mm",
                   "index1":   "0.600000m"}


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
