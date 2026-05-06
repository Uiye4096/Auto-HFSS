"""
Refine14: scale LPF element lengths to push S31 from 18.16 -> 18.5 GHz.

LPF cutoff ∝ 1/sqrt(L*C) ∝ 1/element_length (in SSL quasi-lumped design).
Current: S31 -3dB = 18.16 GHz, need 18.5 GHz.
Scale factor: 18.16/18.5 = 0.9816  (reduce elements by 1.84%)

Baseline LPF elements (from inspect.json):
  l_L512g = 0.77mm   → scaled = 0.756mm
  l_C412g = 0.616mm  → scaled = 0.605mm
  l_L312g = 0.912mm  → scaled = 0.895mm
  l_C212g = 0.506mm  → scaled = 0.497mm
  l_L112g = 0.516mm  → scaled = 0.507mm
  l_sub_LPF12g = 4.34mm → 4.28mm (to keep compensation_y_2 positive)

HPF base: ws17_l4_110_idx06 (best crossing+no dip)
  w_sub=1.7, L4=1.10, L2=0.75, idx=0.6, c1y=0.30
"""
import json
import subprocess
from pathlib import Path

ROOT         = Path(r"D:\Desktop\HFSS_real")
MODEL        = ROOT / "12GHzdiplexer2"
BASE_PROJECT = MODEL / "12GHzdiplexer.aedt"
OUT_ROOT     = MODEL / "derived" / "refine14"
INSPECT      = ROOT / "tools" / "aedt_inspect.py"

ALIGNMENT = {
    "compensation_y":   "L2_g212g + cover_HPF_out12g + l_line212g + 1.426mm - l_sub12g",
    "compensation_y_2": (
        "l_line312g + l_L512g + l_C412g + l_L312g + l_C212g + "
        "l_L112g + l_line412g - l_sub_LPF12g"
    ),
}

HPF_BASE = {
    "w_sub12G":  "1.700000mm",
    "w_C1_y":    "0.300000mm",
    "L4_g312g":  "1.100000mm",
    "L2_g312g":  "0.750000mm",
    "index1":    "0.600000m",
}

# LPF element sets: scale %, (l_L512g, l_C412g, l_L312g, l_C212g, l_L112g, l_sub_LPF12g)
def lpf_set(scale):
    return {
        "l_L512g":      f"{0.770 * scale:.4f}mm",
        "l_C412g":      f"{0.616 * scale:.4f}mm",
        "l_L312g":      f"{0.912 * scale:.4f}mm",
        "l_C212g":      f"{0.506 * scale:.4f}mm",
        "l_L112g":      f"{0.516 * scale:.4f}mm",
        # Sum of variable LPF elements at this scale:
        # 0.04 + L512 + C412 + L312 + C212 + L112 + 1.0 (fixed l_line312g + l_line412g)
        # = 0.04 + 4.36*scale_of_non_fixed + 1.0
        # compensation_y_2 = sum - l_sub_LPF12g = small positive
        # Set l_sub_LPF12g = sum - 0.020mm
        "l_sub_LPF12g": f"{0.04 + (0.770+0.616+0.912+0.506+0.516)*scale + 1.0 - 0.020:.4f}mm",
    }

CASES = {
    "r14_lpf_s098":  {**HPF_BASE, **lpf_set(0.9816)},  # exact target
    "r14_lpf_s096":  {**HPF_BASE, **lpf_set(0.960)},   # slightly more aggressive
    "r14_lpf_s094":  {**HPF_BASE, **lpf_set(0.940)},   # more aggressive
    "r14_lpf_s100":  {**HPF_BASE, **lpf_set(1.000)},   # baseline LPF (no change), reference
    "r14_lpf_s099":  {**HPF_BASE, **lpf_set(0.990)},   # gentle 1%
}


def main():
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for case, base_upd in CASES.items():
        case_dir = OUT_ROOT / case
        case_dir.mkdir(parents=True, exist_ok=True)
        updates = dict(base_upd)
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
            "case":         case,
            "updates":      base_upd,
            "project_path": str(proj_path),
            "output_dir":   str(case_dir / "sim"),
        })
        print(f"  {case}  L512={base_upd['l_L512g']}  sub_LPF={base_upd['l_sub_LPF12g']}")
    (OUT_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nBuilt {len(manifest)} cases -> {OUT_ROOT}")


if __name__ == "__main__":
    main()
