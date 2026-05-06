"""
Refine13: fix S31 in 1.7mm substrate design by restoring Z0.

Root cause: w_sub12G 1.5->1.7mm changes the SSL main-line impedance.
  Old Z0 ratio: w_line12g/w_sub12G = 0.37/1.5 = 0.247
  New (broken):  0.37/1.7 = 0.218  → higher Z0 → LPF sees higher reference
  Fix: w_line12g = 0.247 * 1.7 = 0.420mm to restore ratio.

Best base: ws17_l4_110_idx06
  w_sub=1.7, L4=1.10, L2=0.75, idx=0.6, c1y=0.30
  crossing=18.408, S31=18.16, HPF worst IL=-2.9 dB (no dip!)

Also scale w_C1 (junction cap) by same factor: 0.37 -> 0.42mm.
"""
import json
import subprocess
from pathlib import Path

ROOT         = Path(r"D:\Desktop\HFSS_real")
MODEL        = ROOT / "12GHzdiplexer2"
BASE_PROJECT = MODEL / "12GHzdiplexer.aedt"
OUT_ROOT     = MODEL / "derived" / "refine13"
INSPECT      = ROOT / "tools" / "aedt_inspect.py"

ALIGNMENT = {
    "compensation_y":   "L2_g212g + cover_HPF_out12g + l_line212g + 1.426mm - l_sub12g",
    "compensation_y_2": (
        "l_line312g + l_L512g + l_C412g + l_L312g + l_C212g + "
        "l_L112g + l_line412g - l_sub_LPF12g"
    ),
}

BASE = {
    "w_sub12G":  "1.700000mm",
    "w_C1_y":    "0.300000mm",
    "L4_g312g":  "1.100000mm",
    "L2_g312g":  "0.750000mm",
    "index1":    "0.600000m",
}

CASES = {
    # Restore Z0 ratio by scaling main line width
    "r13_wl_042": {**BASE, "w_line12g": "0.420000mm"},
    "r13_wl_045": {**BASE, "w_line12g": "0.450000mm"},
    "r13_wl_042_wc1_042": {
        **BASE,
        "w_line12g": "0.420000mm",
        "w_C1":      "0.420000mm",  # also scale junction cap width
    },
    # Slightly reduce LPF capacitor length to push S31 up
    "r13_wl_042_lC412_058": {
        **BASE,
        "w_line12g": "0.420000mm",
        "l_C412g":   "0.580000mm",   # baseline 0.616mm, -5.8%
    },
    # Keep original w_line but try w_C1 scaling alone
    "r13_wC1_042": {**BASE, "w_C1": "0.420000mm"},
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
        print(f"  {case}")
    (OUT_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nBuilt {len(manifest)} cases -> {OUT_ROOT}")


if __name__ == "__main__":
    main()
