"""
Refine16: 2D sweep idx1 x c1y on 1.7mm substrate.

Goal: find combination where crossing >= 18.5 GHz AND worst IL < -2 dB.

With c1y=0.45mm (best flatness), crossing=17.76 GHz → need +0.74 GHz.
Hypothesis: increasing index1 beyond 0.6 raises HPF cutoff while
c1y=0.40-0.45mm keeps flatness.

Fixed: w_sub=1.7mm, L4=1.10mm, L2=0.75mm
Vary:  index1 = {0.6, 0.7, 0.8, 1.0}, w_C1_y = {0.40, 0.45mm}
"""
import json
import subprocess
from pathlib import Path

ROOT         = Path(r"D:\Desktop\HFSS_real")
MODEL        = ROOT / "12GHzdiplexer2"
BASE_PROJECT = MODEL / "12GHzdiplexer.aedt"
OUT_ROOT     = MODEL / "derived" / "refine16"
INSPECT      = ROOT / "tools" / "aedt_inspect.py"

ALIGNMENT = {
    "compensation_y":   "L2_g212g + cover_HPF_out12g + l_line212g + 1.426mm - l_sub12g",
    "compensation_y_2": (
        "l_line312g + l_L512g + l_C412g + l_L312g + l_C212g + "
        "l_L112g + l_line412g - l_sub_LPF12g"
    ),
}

CASES = {}
for idx in [0.6, 0.7, 0.8, 1.0]:
    for c1y in [0.35, 0.40, 0.45]:
        name = f"r16_idx{int(idx*10):02d}_c1y{int(c1y*100):03d}"
        CASES[name] = {
            "w_sub12G":  "1.700000mm",
            "L4_g312g":  "1.100000mm",
            "L2_g312g":  "0.750000mm",
            "index1":    f"{idx:.6f}m",
            "w_C1_y":    f"{c1y:.6f}mm",
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
    (OUT_ROOT / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(f"\nBuilt {len(manifest)} cases -> {OUT_ROOT}")


if __name__ == "__main__":
    main()
