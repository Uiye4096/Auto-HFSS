"""
Refine20 — Phase A: Suppress S31 stopband bump.

Baseline: w_sub=1.7mm, w_line=0.395mm, L4=1.10, L2=0.75, idx=0.6, c1y=0.30

Problem: S31 stopband bump at 18.3-20.8 GHz (peak -8.1 dB at 19.2 GHz).
Goal   : S31 <= -10 dB throughout 18-20 GHz.

Three sub-sweeps:

A1 (5 cases) — Increase w_C412g=w_C212g from 1.1→1.6 mm.
  Higher fill ratio (w_C/w_sub) → lower Z_C → higher impedance ratio Z_L/Z_C
  → deeper stopband suppression. DIRECTION NEVER TESTED BEFORE.

A2 (3 cases) — Redistribute l_C412g / l_C212g (total kept at 1.122 mm).
  Current: 0.616/0.506 (ratio=1.22). Two transmission zeros are spaced apart
  → gap between zeros = bump. Equalizing merges zeros into one deeper null.
  total l_C stays at 1.122mm → compensation_y_2 unchanged.

A3 (2 cases) — Narrow w_L312g (0.030→0.020 mm).
  Higher Z_L → larger impedance ratio → deeper stopband attenuation.
  Also try w_L512g reduced from 0.080 to 0.050 mm.
"""
import json
import subprocess
from pathlib import Path

ROOT         = Path(r"D:\Desktop\HFSS_real")
MODEL        = ROOT / "12GHzdiplexer2"
BASE_PROJECT = MODEL / "12GHzdiplexer.aedt"
OUT_ROOT     = MODEL / "derived" / "refine20"
INSPECT      = ROOT / "tools" / "aedt_inspect.py"

ALIGNMENT = {
    "compensation_y":
        "L2_g212g + cover_HPF_out12g + l_line212g + 1.426mm - l_sub12g",
    "compensation_y_2":
        "l_line312g + l_L512g + l_C412g + l_L312g + l_C212g + "
        "l_L112g + l_line412g - l_sub_LPF12g",
}

BASE = {
    "w_sub12G":  "1.700000mm",
    "w_line12g": "0.395000mm",
    "L4_g312g":  "1.100000mm",
    "L2_g312g":  "0.750000mm",
    "index1":    "0.600000m",
    "w_C1_y":    "0.300000mm",
}

CASES = {}

# ── A1: increase capacitor widths (fill ratio sweep) ────────────────────────
for wc in [1.2, 1.3, 1.4, 1.5, 1.6]:
    name = f"r20_A1_wC{int(wc*10):02d}"
    CASES[name] = {**BASE,
                   "w_C412g": f"{wc:.6f}mm",
                   "w_C212g": f"{wc:.6f}mm"}

# ── A2: redistribute capacitor lengths (total unchanged = 1.122 mm) ─────────
for lc4, lc2 in [(0.561, 0.561),   # equal (merged zeros)
                  (0.580, 0.542),   # slight lean to C4
                  (0.650, 0.472)]:  # large lean to C4 (move zeros apart)
    tag = f"{int(lc4*1000):03d}_{int(lc2*1000):03d}"
    name = f"r20_A2_lC{tag}"
    CASES[name] = {**BASE,
                   "l_C412g": f"{lc4:.6f}mm",
                   "l_C212g": f"{lc2:.6f}mm"}

# ── A3: narrow series inductor widths (higher Z_L) ──────────────────────────
for wl3 in [0.020, 0.025]:
    name = f"r20_A3_wL3_{int(wl3*1000):03d}"
    CASES[name] = {**BASE, "w_L312g": f"{wl3:.6f}mm"}

# A3b: also narrow w_L512g
CASES["r20_A3b_wL5_050"] = {**BASE, "w_L512g": "0.050000mm"}
CASES["r20_A3b_wL5_040"] = {**BASE, "w_L512g": "0.040000mm"}


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
