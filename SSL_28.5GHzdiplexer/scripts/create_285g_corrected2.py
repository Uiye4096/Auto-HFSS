"""
create_285g_corrected2.py
Takes the fringing-corrected baseline (corrected.aedt targeting 23 GHz observed) and
applies an ADDITIONAL ×0.80 to ALL lengths PLUS another round of fringing correction
to the LPF capacitive stubs (l_C4, l_C2).

Goal: push crossing from ~24.7 GHz → ~28.5 GHz.

Strategy:
  l_C_new = (l_C_corrected + 2*dl) * EXTRA - 2*dl
  l_L_new = l_L_corrected * EXTRA
  l_HPF_new = l_HPF_corrected * EXTRA

Output: final/diplexer_285g_corrected2.aedt
"""
import json, math, subprocess, sys
from pathlib import Path

ROOT      = Path(__file__).parent.parent.parent
MODEL_DIR = Path(__file__).parent.parent
INSPECT   = ROOT / "tools" / "aedt_inspect.py"
SRC_AEDT  = ROOT / "0506185GHzmodel - 副本" / "final" / "260507_diplexer_185g_087.aedt"
DST_AEDT  = MODEL_DIR / "final" / "diplexer_285g_corrected2.aedt"

# Overall target: 18.5 → 28.5 GHz
F_LO = 18.5; F_HI = 28.5
SCALE_TOTAL = F_LO / F_HI  # 0.6491

# Observed result after corrected.aedt: ~24.7 GHz
# Extra push factor to get from ~24.7 to ~28.5 GHz  (×0.80 is aggressive overshoot)
EXTRA = 24.7 / 28.5  # 0.8667 — use slightly more aggressive
EXTRA = 0.80         # 暴力

# Substrate H=0.254mm, eps_r=9.9
H = 0.254

def eps_eff(W):
    eps_r = 9.9
    return (eps_r+1)/2 + (eps_r-1)/2 / math.sqrt(1 + 12/(W/H))

def delta_l(W):
    ee = eps_eff(W)
    WH = W / H
    return 0.412 * H * (ee+0.3)/(ee-0.258) * (WH+0.264)/(WH+0.8)

# Fringing-corrected values from step 1 (create_285g_corrected.py)
CORR1 = {
    "l_C4185g":    0.218870,  # already fringing-corrected
    "l_C2185g":    0.257090,  # already fringing-corrected
    "l_L5185g":    0.451665,
    "l_L3185g":    0.583400,
    "l_L1185g":    0.432845,
    "l_line2185g": 0.389474,
    "L4_g3185g":   0.551754,
    "L7_g3185g":   0.538772,
    "L7_g4185g":   0.337544,
    "cx":          0.129825,
    "cy":         -0.129825,
    "w_tapper":    0.064912,
    "h_tapper":    0.064912,
    "w_C4185g":    1.15,  # widths unchanged
    "w_C2185g":    1.05,
}

W_C4 = CORR1["w_C4185g"]; W_C2 = CORR1["w_C2185g"]
dl_C4 = delta_l(W_C4); dl_C2 = delta_l(W_C2)

def correct_cap(l_corr, dl):
    """Apply additional fringing correction for the extra scale step."""
    return (l_corr + 2*dl) * EXTRA - 2*dl

CORR2 = {}
for k, v in CORR1.items():
    if k == "l_C4185g":
        CORR2[k] = correct_cap(v, dl_C4)
    elif k == "l_C2185g":
        CORR2[k] = correct_cap(v, dl_C2)
    elif k.startswith("w_"):
        CORR2[k] = v            # widths unchanged
    else:
        CORR2[k] = v * EXTRA    # simple scale for all others

if __name__ == "__main__":
    DST_AEDT.parent.mkdir(parents=True, exist_ok=True)

    print(f"Additional scale factor EXTRA = {EXTRA:.4f}")
    print(f"dl_C4={dl_C4:.4f}mm  dl_C2={dl_C2:.4f}mm")
    print()
    print(f"{'Parameter':20s}  {'Corr1 (23GHz)':>14}  {'Corr2 (target)':>14}")
    print("-" * 54)
    for k in CORR1:
        if k.startswith("w_"): continue
        flag = " ← cap corrected" if k in ("l_C4185g","l_C2185g") else ""
        print(f"  {k:20s}  {CORR1[k]:14.6f}  {CORR2[k]:14.6f}{flag}")

    updates = {}
    for k, v in CORR2.items():
        updates[k] = f"{v:.6f}mm"

    # Default L2 for baseline (will be swept)
    updates["L2_g3185g"] = f"{CORR1.get('L2_g3185g', 0.506316) * EXTRA:.6f}mm"

    upd_path = MODEL_DIR / "final" / "_corrected2_updates.json"
    upd_path.write_text(json.dumps(updates, indent=2), encoding="utf-8")

    r = subprocess.run(
        ["python", str(INSPECT), str(SRC_AEDT),
         "--set", str(upd_path),
         "--write-to", str(DST_AEDT)],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print("STDERR:", r.stderr[:400]); sys.exit(1)

    txt = DST_AEDT.read_text(encoding="utf-8", errors="ignore")
    txt = txt.replace("Frequency='18.5GHz'", "Frequency='28.5GHz'")
    txt = txt.replace("RangeStart='5GHz'",   "RangeStart='10GHz'")
    txt = txt.replace("RangeEnd='30GHz'",     "RangeEnd='60GHz'")
    DST_AEDT.write_text(txt, encoding="utf-8")

    print(f"\n✓ Created: {DST_AEDT.name}")
    print(f"  l_C4: {CORR1['l_C4185g']:.5f} → {CORR2['l_C4185g']:.5f} mm")
    print(f"  l_C2: {CORR1['l_C2185g']:.5f} → {CORR2['l_C2185g']:.5f} mm")
    print(f"  l_L5: {CORR1['l_L5185g']:.5f} → {CORR2['l_L5185g']:.5f} mm")
    print(f"  L7_g3: {CORR1['L7_g3185g']:.5f} → {CORR2['L7_g3185g']:.5f} mm")
