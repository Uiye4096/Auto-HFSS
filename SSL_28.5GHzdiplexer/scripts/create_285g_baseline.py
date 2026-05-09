"""
create_285g_baseline.py
Scales the 18.5 GHz diplexer (case 087) to 28.5 GHz by multiplying all
LENGTH parameters by f_lo/f_hi = 18.5/28.5 = 0.64912.
WIDTH parameters (w_*) and the unitless k_LPF are kept unchanged.

Output: SSL_28.5GHzdiplexer/final/diplexer_285g_baseline.aedt
"""
import json, subprocess, sys
from pathlib import Path

ROOT      = Path(__file__).parent.parent.parent
MODEL_DIR = Path(__file__).parent.parent
INSPECT   = ROOT / "tools" / "aedt_inspect.py"
SRC_AEDT  = ROOT / "0506185GHzmodel - 副本" / "final" / "260507_diplexer_185g_087.aedt"
DST_AEDT  = MODEL_DIR / "final" / "diplexer_285g_baseline.aedt"

F_LO = 18.5   # original design frequency (GHz)
F_HI = 28.5   # target design frequency (GHz)
SCALE = F_LO / F_HI   # 0.64912

# --- 087 base parameter values (18.5 GHz) ---
BASE_185 = {
    # LENGTH parameters (scale by SCALE)
    "l_line2185g":  0.60,
    "L4_g3185g":    0.85,
    "L2_g3185g":    0.78,
    "L7_g3185g":    0.83,
    "L7_g4185g":    0.52,
    "l_L5185g":     0.695808,
    "l_C4185g":     0.446477,
    "l_L3185g":     0.898752,
    "l_C2185g":     0.504461,
    "l_L1185g":     0.666816,
    "cx":           0.20,
    "cy":          -0.20,
    "w_tapper":     0.10,
    "h_tapper":     0.10,
    # WIDTH / unitless (keep unchanged)
    "w_C4185g":     1.15,
    "w_C2185g":     1.05,
    "k_LPF":        0.96,
}

LENGTH_PARAMS = {
    "l_line2185g", "L4_g3185g", "L2_g3185g", "L7_g3185g", "L7_g4185g",
    "l_L5185g", "l_C4185g", "l_L3185g", "l_C2185g", "l_L1185g",
    "cx", "cy", "w_tapper", "h_tapper",
}

def scale_params():
    out = {}
    for k, v in BASE_185.items():
        if k in LENGTH_PARAMS:
            out[k] = f"{v * SCALE:.6f}mm"
        elif k == "k_LPF":
            out[k] = str(v)
        else:
            out[k] = f"{v}mm"
    return out

if __name__ == "__main__":
    DST_AEDT.parent.mkdir(parents=True, exist_ok=True)
    updates = scale_params()

    print(f"Scale factor: {SCALE:.6f}  ({F_LO} → {F_HI} GHz)")
    print(f"Source: {SRC_AEDT.name}")
    print(f"Dest:   {DST_AEDT.name}")
    print()
    print("Scaled LENGTH parameters:")
    for k in sorted(LENGTH_PARAMS):
        if k in updates:
            print(f"  {k:20s}: {BASE_185[k]:.6f} mm  →  {updates[k]}")

    upd_path = MODEL_DIR / "final" / "_scale_updates.json"
    upd_path.write_text(json.dumps(updates, indent=2), encoding="utf-8")

    r = subprocess.run(
        ["python", str(INSPECT), str(SRC_AEDT),
         "--set", str(upd_path),
         "--write-to", str(DST_AEDT)],
        capture_output=True, text=True
    )
    print("\naedt_inspect output:", r.stdout.strip() or "(none)")
    if r.returncode != 0:
        print("STDERR:", r.stderr[:400])
        sys.exit(1)

    print(f"\n✓ Created: {DST_AEDT}")

    # Save parameters.json for this baseline
    params_out = {
        "uid": "baseline",
        "source": "diplexer_185g_087 scaled × 18.5/28.5",
        "scale_factor": round(SCALE, 6),
        "parameters": {k: (v * SCALE if k in LENGTH_PARAMS else v)
                       for k, v in BASE_185.items()},
        "targets": {
            "crossing_GHz":        "≥ 28.5",
            "S31_at_29GHz_dB":     "≤ -10",
            "S31_at_30GHz_dB":     "≤ -10",
            "ripple_30_38GHz_dB":  "≤ 1",
            "S11_worst_29_43GHz_dB": "≤ -10",
        }
    }
    (MODEL_DIR / "final" / "parameters.json").write_text(
        json.dumps(params_out, indent=2), encoding="utf-8"
    )
    print("✓ Wrote parameters.json")

    # Patch Setup1: adaptive frequency 18.5 → 28.5 GHz, sweep 5-30 → 10-60 GHz
    txt = DST_AEDT.read_text(encoding="utf-8", errors="ignore")
    txt = txt.replace("Frequency='18.5GHz'", "Frequency='28.5GHz'")
    txt = txt.replace("RangeStart='5GHz'",   "RangeStart='10GHz'")
    txt = txt.replace("RangeEnd='30GHz'",     "RangeEnd='60GHz'")
    DST_AEDT.write_text(txt, encoding="utf-8")
    print("✓ Patched Setup1: adaptive=28.5GHz, sweep 10-60GHz")
