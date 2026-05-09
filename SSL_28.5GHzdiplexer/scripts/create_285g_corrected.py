"""
create_285g_corrected.py
Scales the 18.5 GHz diplexer (087) to 28.5 GHz using FRINGING-CORRECTED lengths
for the inline stepped-impedance LPF capacitive sections (l_C4, l_C2).

Correction formula for each capacitive patch (both ends have step discontinuity):
  l_C_new = (l_C_orig + 2*dl) * (f_old/f_new) - 2*dl
where dl = 0.412 * H * (eps_eff+0.3)/(eps_eff-0.258) * (W/H+0.264)/(W/H+0.8)

Inductive sections (l_L*) have no open-end correction: simple scale × (f_old/f_new).
HPF stubs (L2_g3, L4_g3, L7_g3, L7_g4) keep naive scaling (step 1 correction only
for LPF; HPF stubs will be swept in sweep2).

Output: SSL_28.5GHzdiplexer/final/diplexer_285g_corrected.aedt
"""
import json, math, subprocess, sys
from pathlib import Path

ROOT      = Path(__file__).parent.parent.parent
MODEL_DIR = Path(__file__).parent.parent
INSPECT   = ROOT / "tools" / "aedt_inspect.py"
SRC_AEDT  = ROOT / "0506185GHzmodel - 副本" / "final" / "260507_diplexer_185g_087.aedt"
DST_AEDT  = MODEL_DIR / "final" / "diplexer_285g_corrected.aedt"

F_LO = 18.5
F_HI = 28.5
S    = F_LO / F_HI   # 0.6491

# Substrate: H=0.254mm, eps_r=9.9
H = 0.254

def eps_eff(W):
    """Quasi-static effective permittivity for microstrip, eps_r=9.9."""
    eps_r = 9.9
    WH = W / H
    return (eps_r + 1) / 2 + (eps_r - 1) / 2 / math.sqrt(1 + 12 / WH)

def delta_l(W):
    """Open-end fringing extension for microstrip (Hammerstad & Jensen)."""
    ee = eps_eff(W)
    WH = W / H
    return 0.412 * H * (ee + 0.3) / (ee - 0.258) * (WH + 0.264) / (WH + 0.8)

def correct_cap_length(l_orig, W):
    """Scale capacitive patch length with fringing correction."""
    dl = delta_l(W)
    return (l_orig + 2 * dl) * S - 2 * dl

def simple_scale(l_orig):
    return l_orig * S

# Original 087 parameter values (18.5 GHz)
ORIG = {
    # LPF capacitive sections — FRINGING CORRECTED
    "l_C4185g":  0.446477,   # w_C4185g = 1.15 mm
    "l_C2185g":  0.504461,   # w_C2185g = 1.05 mm
    # LPF inductive sections — simple scale
    "l_L5185g":  0.695808,
    "l_L3185g":  0.898752,
    "l_L1185g":  0.666816,
    # HPF stubs — simple scale (swept in sweep2)
    "l_line2185g": 0.60,
    "L4_g3185g":   0.85,
    "L2_g3185g":   0.78,
    "L7_g3185g":   0.83,
    "L7_g4185g":   0.52,
    # Position / taper — simple scale
    "cx":       0.20,
    "cy":      -0.20,
    "w_tapper": 0.10,
    "h_tapper": 0.10,
    # Widths — UNCHANGED
    "w_C4185g": 1.15,
    "w_C2185g": 1.05,
}

W_C4 = ORIG["w_C4185g"]
W_C2 = ORIG["w_C2185g"]

dl_C4 = delta_l(W_C4)
dl_C2 = delta_l(W_C2)

SCALED = {
    # fringing-corrected
    "l_C4185g":  correct_cap_length(ORIG["l_C4185g"], W_C4),
    "l_C2185g":  correct_cap_length(ORIG["l_C2185g"], W_C2),
    # simple scale
    "l_L5185g":  simple_scale(ORIG["l_L5185g"]),
    "l_L3185g":  simple_scale(ORIG["l_L3185g"]),
    "l_L1185g":  simple_scale(ORIG["l_L1185g"]),
    "l_line2185g": simple_scale(ORIG["l_line2185g"]),
    "L4_g3185g": simple_scale(ORIG["L4_g3185g"]),
    "L2_g3185g": simple_scale(ORIG["L2_g3185g"]),
    "L7_g3185g": simple_scale(ORIG["L7_g3185g"]),
    "L7_g4185g": simple_scale(ORIG["L7_g4185g"]),
    "cx":        simple_scale(ORIG["cx"]),
    "cy":        simple_scale(ORIG["cy"]),
    "w_tapper":  simple_scale(ORIG["w_tapper"]),
    "h_tapper":  simple_scale(ORIG["h_tapper"]),
    # widths unchanged
    "w_C4185g":  ORIG["w_C4185g"],
    "w_C2185g":  ORIG["w_C2185g"],
}

if __name__ == "__main__":
    DST_AEDT.parent.mkdir(parents=True, exist_ok=True)

    print(f"Fringing corrections:")
    print(f"  w_C4={W_C4}mm: eps_eff={eps_eff(W_C4):.3f}, dl={dl_C4:.4f}mm")
    print(f"  w_C2={W_C2}mm: eps_eff={eps_eff(W_C2):.3f}, dl={dl_C2:.4f}mm")
    print()
    print(f"{'Parameter':20s}  {'Original':>10}  {'NaiveScale':>10}  {'Corrected':>10}")
    print("-" * 56)
    for k, v_orig in ORIG.items():
        if k.startswith("w_"): continue
        v_naive = v_orig * S
        v_corr  = SCALED[k]
        flag = " ← corrected" if k in ("l_C4185g","l_C2185g") else ""
        print(f"  {k:20s}  {v_orig:10.5f}  {v_naive:10.5f}  {v_corr:10.5f}{flag}")

    # Build updates.json
    updates = {k: (f"{v:.6f}mm" if k != "w_tapper" and not k.startswith("w_C") else f"{v}mm")
               for k, v in SCALED.items()}
    # fix widths and special cases
    for k in ("w_C4185g", "w_C2185g"):
        updates[k] = f"{ORIG[k]}mm"
    for k in ("cx", "cy", "w_tapper", "h_tapper", "l_line2185g",
              "L4_g3185g", "L2_g3185g", "L7_g3185g", "L7_g4185g",
              "l_L5185g", "l_L3185g", "l_L1185g", "l_C4185g", "l_C2185g"):
        updates[k] = f"{SCALED[k]:.6f}mm"

    upd_path = MODEL_DIR / "final" / "_corrected_updates.json"
    upd_path.write_text(json.dumps(updates, indent=2), encoding="utf-8")

    r = subprocess.run(
        ["python", str(INSPECT), str(SRC_AEDT),
         "--set", str(upd_path),
         "--write-to", str(DST_AEDT)],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print("STDERR:", r.stderr[:400]); sys.exit(1)

    # Patch Setup1: adaptive=28.5GHz, sweep 10-60 GHz
    txt = DST_AEDT.read_text(encoding="utf-8", errors="ignore")
    txt = txt.replace("Frequency='18.5GHz'", "Frequency='28.5GHz'")
    txt = txt.replace("RangeStart='5GHz'",   "RangeStart='10GHz'")
    txt = txt.replace("RangeEnd='30GHz'",     "RangeEnd='60GHz'")
    DST_AEDT.write_text(txt, encoding="utf-8")

    print(f"\n✓ Created: {DST_AEDT.name}")
    print(f"  l_C4185g: {ORIG['l_C4185g']:.5f} → naive {ORIG['l_C4185g']*S:.5f} → corrected {SCALED['l_C4185g']:.5f} mm")
    print(f"  l_C2185g: {ORIG['l_C2185g']:.5f} → naive {ORIG['l_C2185g']*S:.5f} → corrected {SCALED['l_C2185g']:.5f} mm")
