"""
Refine10: w_sub12G = 1.7mm (wider substrate/channel).

Physics: HPF shunt inductor stubs span the full substrate width.
  L_stub ∝ w_sub12G → wider = more inductance → lower HPF cutoff.
  Estimated shift: f_hpf × sqrt(1.5/1.7) = f_hpf × 0.94
  Previous best crossing ~18.8 GHz → expected ~17.7 GHz with 1.7mm,
  so we need to slightly increase L4_g312g to push it back up to 18.5.

Start from w04-type params (best crossing 18.747 GHz) and vary
L4_g312g around a slightly larger value to compensate the extra inductance.
Also include u05-type base for dip comparison.
"""
import json
import subprocess
from pathlib import Path

ROOT         = Path(r"D:\Desktop\HFSS_real")
MODEL        = ROOT / "12GHzdiplexer2"
BASE_PROJECT = MODEL / "12GHzdiplexer.aedt"
OUT_ROOT     = MODEL / "derived" / "refine10"
INSPECT      = ROOT / "tools" / "aedt_inspect.py"

ALIGNMENT = {
    "compensation_y":   "L2_g212g + cover_HPF_out12g + l_line212g + 1.426mm - l_sub12g",
    "compensation_y_2": (
        "l_line312g + l_L512g + l_C412g + l_L312g + l_C212g + "
        "l_L112g + l_line412g - l_sub_LPF12g"
    ),
}

W_SUB = "1.700000mm"

CASES = {
    # Direct equivalent of w04 (best crossing 18.747) with wider substrate
    "ws17_w04eq": {
        "w_sub12G":  W_SUB,
        "w_C1_y":   "0.300000mm",
        "L4_g312g": "1.000000mm",
        "L2_g312g": "0.750000mm",
        "index1":   "0.400000m",
    },
    # Compensate extra inductance: increase L4_g312g slightly
    "ws17_l4_110": {
        "w_sub12G":  W_SUB,
        "w_C1_y":   "0.300000mm",
        "L4_g312g": "1.100000mm",
        "L2_g312g": "0.750000mm",
        "index1":   "0.400000m",
    },
    "ws17_l4_120": {
        "w_sub12G":  W_SUB,
        "w_C1_y":   "0.300000mm",
        "L4_g312g": "1.200000mm",
        "L2_g312g": "0.750000mm",
        "index1":   "0.400000m",
    },
    # u05-equivalent (better dip behavior) with wider substrate
    "ws17_u05eq": {
        "w_sub12G":  W_SUB,
        "w_C1_y":   "0.250000mm",
        "L4_g312g": "0.900000mm",
        "L2_g312g": "0.800000mm",
        "index1":   "0.400000m",
        "l_line312g": "0.100000mm",
    },
    # Wider substrate + larger index1 (less aggressive capacitor reduction)
    "ws17_l4_110_idx06": {
        "w_sub12G":  W_SUB,
        "w_C1_y":   "0.300000mm",
        "L4_g312g": "1.100000mm",
        "L2_g312g": "0.750000mm",
        "index1":   "0.600000m",
    },
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
