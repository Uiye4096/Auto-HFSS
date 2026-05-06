"""
Build HPF stub-position scaling cases combined with 3.8x LPF widths.

The HPF lower cutoff is controlled by the Y-positions of the shunt inductors:
  d_L412g (baseline 0.6mm) and d_L212g (baseline 1.41mm).
Scaling both by the same factor shifts the HPF passband inversely.

Alignment constraint (HPF output port must reach l_sub12g):
  l_sub12g = d_L212g + w_L212g/2 + L2_g212g + cover_HPF_out12g + l_line212g
           = d_L212g + 0.016 + 0.05 + 0.1 + 1.0
           = d_L212g + 1.166

Baseline check: 1.41 + 1.166 = 2.576mm = l_sub12g  OK.
"""
import json
from pathlib import Path

ROOT = Path(r"D:\Desktop\HFSS_real\12GHzdiplexer\derived\hpf_stub_scale")

LPF_3P8 = {
    "w_L512g": "0.304000mm",
    "w_C412g": "1.254000mm",
    "w_L312g": "0.152000mm",
    "w_C212g": "1.254000mm",
    "w_L112g": "0.342000mm",
}

D_L412G_BASE  = 0.6
D_L212G_BASE  = 1.41
L_LINESUB_CONST = 1.166   # w_L212g/2 + L2_g212g + cover_HPF_out12g + l_line212g

SCALES = {
    "hpf_1p2x": 1.2,
    "hpf_1p3x": 1.3,
    "hpf_1p54x": 1.54,
}

def build_case(scale):
    d412 = D_L412G_BASE * scale
    d212 = D_L212G_BASE * scale
    lsub = d212 + L_LINESUB_CONST
    return {
        **LPF_3P8,
        "L4_g312g":  "0.600000mm",
        "d_L412g":   f"{d412:.6f}mm",
        "d_L212g":   f"{d212:.6f}mm",
        "l_sub12g":  f"{lsub:.6f}mm",
    }


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name, scale in SCALES.items():
        case_dir = ROOT / name
        case_dir.mkdir(parents=True, exist_ok=True)
        updates = build_case(scale)
        up_path = case_dir / "updates.json"
        up_path.write_text(json.dumps(updates, indent=2), encoding="utf-8")
        manifest.append({
            "case":         name,
            "scale":        scale,
            "updates_path": str(up_path),
            "project_path": str(case_dir / f"{name}.aedt"),
            "output_dir":   str(case_dir / "sim"),
        })
        print(f"  {name}: d_L412g={updates['d_L412g']}  d_L212g={updates['d_L212g']}"
              f"  l_sub12g={updates['l_sub12g']}")
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nBuilt {len(manifest)} cases → {ROOT}")


if __name__ == "__main__":
    main()
