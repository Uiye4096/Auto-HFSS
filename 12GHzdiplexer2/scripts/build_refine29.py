"""
Refine29 — Reference-guided exploration from diplexer185GHzmodel.aedt.

Key discoveries from 185g model:
  1. Non-uniform LPF element redistribution (NOT simple k-scaling):
       l_C4: 0.616 → 0.46508 mm (-24.5%)
       l_L1: 0.516 → 0.6946  mm (+34.6%)
       l_L5: 0.770 → 0.7248  mm (-5.9%)
       l_L3: 0.912 → 0.9362  mm (+2.6%)
       l_C2: 0.506 → 0.52548 mm (+3.8%)
       Total unchanged: 3.306 ≈ 3.320 mm (k ≈ 1.0)
  2. L4_g412g / L2_g412g = 0.501 mm (vs our 0.3 mm — NEVER explored!)
     These are the HPF stub widths/lengths that directly set stub resonances.
  3. Asymmetric cap widths: w_C4=1.0mm, w_C2=0.9mm
  4. L4_g312g = L2_g312g = 0.85mm (symmetric, vs our L2=0.75)
  5. l_sub_LPF12g for 185g lengths in 12g geometry ≈ 4.346mm (≈ base 4.34)

Sweeps:
  S1: 185g non-uniform LPF lengths in our 12g model
      a) with our best HPF + w_C=1.45mm (test if redistribution alone helps)
      b) with L2_g3=0.85 (symmetric, as in 185g)
      c) with 185g cap widths (w_C4=1.0, w_C2=0.9mm)
  S2: L4_g412g / L2_g412g sweep at our current best (CRITICAL - never tried!)
      {0.35, 0.40, 0.45, 0.50mm} × best config (k=0.90, wC=1.45, L4g3=0.85)
  S3: Combine g4=0.50 with best params + c1y variations
  Total: ~14 cases
"""
import json
import subprocess
from pathlib import Path

ROOT         = Path(r"D:\Desktop\HFSS_real")
MODEL        = ROOT / "12GHzdiplexer2"
BASE_PROJECT = MODEL / "12GHzdiplexer.aedt"
OUT_ROOT     = MODEL / "derived" / "refine29"
INSPECT      = ROOT / "tools" / "aedt_inspect.py"

ALIGNMENT = {
    "compensation_y":
        "L2_g212g + cover_HPF_out12g + l_line212g + 1.426mm - l_sub12g",
    "compensation_y_2":
        "l_line312g + l_L512g + l_C412g + l_L312g + l_C212g + "
        "l_L112g + l_line412g - l_sub_LPF12g",
}

# ── LPF element sets ──────────────────────────────────────────────────────────

# Our current best (k=0.90 uniform scaling)
LPF_K090 = {
    "l_L512g":      "0.693000mm",
    "l_C412g":      "0.554400mm",
    "l_L312g":      "0.820800mm",
    "l_C212g":      "0.455400mm",
    "l_L112g":      "0.464400mm",
    "l_sub_LPF12g": "4.008000mm",   # 1.02 + 3.320*0.90
}

# 185g-reference non-uniform redistribution (total ≈ base, k≈1.0)
# l_sub_LPF12g = 0.04 + 0.7248+0.46508+0.9362+0.52548+0.6946 + 1.0 = 4.34616
LPF_185 = {
    "l_L512g":      "0.724800mm",
    "l_C412g":      "0.465080mm",
    "l_L312g":      "0.936200mm",
    "l_C212g":      "0.525480mm",
    "l_L112g":      "0.694600mm",
    "l_sub_LPF12g": "4.346160mm",
}

# Partial redistribution: midpoint between k=0.90 and 185g
LPF_MID = {
    "l_L512g":      f"{(0.693+0.7248)/2:.6f}mm",   # 0.7089
    "l_C412g":      f"{(0.5544+0.46508)/2:.6f}mm",  # 0.5097
    "l_L312g":      f"{(0.8208+0.9362)/2:.6f}mm",   # 0.8785
    "l_C212g":      f"{(0.4554+0.52548)/2:.6f}mm",  # 0.4904
    "l_L112g":      f"{(0.4644+0.6946)/2:.6f}mm",   # 0.5795
    "l_sub_LPF12g": f"{(4.008+4.34616)/2:.6f}mm",   # 4.177
}

# ── Fixed HPF best ────────────────────────────────────────────────────────────
FIXED_BEST = {
    "w_sub12G":  "1.700000mm",
    "w_line12g": "0.395000mm",
    "L4_g312g":  "0.850000mm",
    "L2_g312g":  "0.750000mm",
    "index1":    "0.600000m",
    "w_C1_y":    "0.220000mm",
}

CASES = {}

# ── S1a: 185g LPF redistribution + our best HPF + wC=1.45mm ──────────────────
CASES["r29_185lpf_wC145_l2075"] = {
    **FIXED_BEST, **LPF_185,
    "w_C412g": "1.450000mm",
    "w_C212g": "1.450000mm",
}

# ── S1b: 185g LPF + L2_g3=0.85 (symmetric stubs like 185g) ──────────────────
CASES["r29_185lpf_wC145_l2085"] = {
    **FIXED_BEST, **LPF_185,
    "L2_g312g": "0.850000mm",
    "w_C412g":  "1.450000mm",
    "w_C212g":  "1.450000mm",
}

# ── S1c: 185g LPF + 185g cap widths (asymmetric) ─────────────────────────────
CASES["r29_185lpf_wC10_09_l2085"] = {
    **FIXED_BEST, **LPF_185,
    "L2_g312g": "0.850000mm",
    "w_C412g":  "1.000000mm",
    "w_C212g":  "0.900000mm",
}

# ── S1d: midpoint LPF + wC=1.45 ──────────────────────────────────────────────
CASES["r29_midlpf_wC145_l2075"] = {
    **FIXED_BEST, **LPF_MID,
    "w_C412g": "1.450000mm",
    "w_C212g": "1.450000mm",
}

# ── S2: L4_g412g / L2_g412g sweep (NEVER tried!) ─────────────────────────────
# Currently 0.3mm in base model — what does expanding HPF stubs do?
for g4 in [0.35, 0.40, 0.45, 0.50]:
    name = f"r29_g4{int(g4*100):03d}_k090_wC145"
    CASES[name] = {
        **FIXED_BEST, **LPF_K090,
        "w_C412g":   "1.450000mm",
        "w_C212g":   "1.450000mm",
        "L4_g412g":  f"{g4:.6f}mm",
        "L2_g412g":  f"{g4:.6f}mm",
    }

# ── S3: g4=0.50 + c1y variations + L2_g3 variants ───────────────────────────
for c1y in [0.18, 0.22, 0.26]:
    name = f"r29_g4050_wC145_c1y{int(c1y*100):03d}"
    CASES[name] = {
        **FIXED_BEST, **LPF_K090,
        "w_C412g":  "1.450000mm",
        "w_C212g":  "1.450000mm",
        "L4_g412g": "0.500000mm",
        "L2_g412g": "0.500000mm",
        "w_C1_y":   f"{c1y:.6f}mm",
    }

CASES["r29_g4050_wC145_l2085_c1y022"] = {
    **FIXED_BEST, **LPF_K090,
    "w_C412g":  "1.450000mm",
    "w_C212g":  "1.450000mm",
    "L4_g412g": "0.500000mm",
    "L2_g412g": "0.500000mm",
    "L2_g312g": "0.850000mm",
    "w_C1_y":   "0.220000mm",
}

# ── S4: 185g LPF + g4=0.50 + wC=1.45 (combine both new ideas) ───────────────
CASES["r29_185lpf_g4050_wC145_c1y022"] = {
    **FIXED_BEST, **LPF_185,
    "w_C412g":  "1.450000mm",
    "w_C212g":  "1.450000mm",
    "L4_g412g": "0.500000mm",
    "L2_g412g": "0.500000mm",
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
