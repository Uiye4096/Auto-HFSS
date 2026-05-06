"""
Refine22 — Phase B-2: Tune L2_g312g to raise crossing.

Best from Phase B: r21_wC14_l4114_idx06
  w_C=1.4mm, L4=1.14mm, idx=0.6 → cross=17.650, bump=-11.2✓, IL=-3.0 dB (best so far)

L2_g312g (HPF shunt inductor gap) has NOT been varied in any Phase B sweep.
In complementary-filter theory, L2 tunes the HPF high-frequency matching, which
can shift where S21 and S31 intersect.

Sweep 1: w_C=1.4mm, L4=1.14mm, idx=0.6, L2 from 0.50 to 1.00mm  (11 cases)
Sweep 2: w_C=1.4mm, L4=1.10mm, idx=0.6, L2 from 0.60 to 0.90mm  (7 cases)
Sweep 3: w_C=1.4mm, best L2 found above, sweep L4 × idx fine grid (6 cases)
         → added after first sweep results are inspected
Total first batch: 18 cases, 4-parallel
"""
import json
import subprocess
from pathlib import Path

ROOT         = Path(r"D:\Desktop\HFSS_real")
MODEL        = ROOT / "12GHzdiplexer2"
BASE_PROJECT = MODEL / "12GHzdiplexer.aedt"
OUT_ROOT     = MODEL / "derived" / "refine22"
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
    "w_C1_y":    "0.300000mm",
}

CASES = {}

# ── Sweep 1: L4=1.14mm, idx=0.6, L2 wide range ─────────────────────────────
for l2 in [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00]:
    name = f"r22_l4114_l2{int(l2*100):03d}"
    CASES[name] = {**FIXED,
                   "L4_g312g": "1.140000mm",
                   "L2_g312g": f"{l2:.6f}mm",
                   "index1":   "0.600000m"}

# ── Sweep 2: L4=1.10mm, idx=0.6, L2 mid range ──────────────────────────────
for l2 in [0.60, 0.65, 0.70, 0.80, 0.85, 0.90, 0.95]:
    name = f"r22_l4110_l2{int(l2*100):03d}"
    CASES[name] = {**FIXED,
                   "L4_g312g": "1.100000mm",
                   "L2_g312g": f"{l2:.6f}mm",
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
