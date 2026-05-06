import json
import subprocess
from pathlib import Path


ROOT = Path(r"D:\Desktop\HFSS_real")
MODEL = ROOT / "12GHzdiplexer2"
BASE_PROJECT = MODEL / "12GHzdiplexer.aedt"
OUT_ROOT = MODEL / "derived" / "impedance_sweep"
INSPECT = ROOT / "tools" / "aedt_inspect.py"


LEVELS = {
    "w_C1_y": ["0.070000mm", "0.120000mm", "0.170000mm"],
    "L4_g312g": ["0.700000mm", "0.850000mm", "1.000000mm"],
    "L2_g312g": ["0.700000mm", "0.850000mm", "1.000000mm"],
    "index1": ["0.600000m", "0.800000m", "1.000000m"],
}

ALIGNMENT_UPDATES = {
    "compensation_y": "L2_g212g + cover_HPF_out12g + l_line212g + 1.426mm - l_sub12g",
    "compensation_y_2": (
        "l_line312g + l_L512g + l_C412g + l_L312g + l_C212g + "
        "l_L112g + l_line412g - l_sub_LPF12g"
    ),
}

# L9 orthogonal array for four 3-level factors.
L9 = [
    (0, 0, 0, 0),
    (0, 1, 1, 1),
    (0, 2, 2, 2),
    (1, 0, 1, 2),
    (1, 1, 2, 0),
    (1, 2, 0, 1),
    (2, 0, 2, 1),
    (2, 1, 0, 2),
    (2, 2, 1, 0),
]


def main():
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    manifest = []
    names = list(LEVELS)
    for i, row in enumerate(L9, start=1):
        updates = {name: LEVELS[name][level] for name, level in zip(names, row)}
        updates.update(ALIGNMENT_UPDATES)
        label = (
            f"case_{i:02d}_"
            f"c1y{row[0] + 1}_l4{row[1] + 1}_l2{row[2] + 1}_idx{row[3] + 1}"
        )
        case_dir = OUT_ROOT / label
        case_dir.mkdir(parents=True, exist_ok=True)
        updates_path = case_dir / "updates.json"
        updates_path.write_text(json.dumps(updates, indent=2), encoding="utf-8")
        project_path = case_dir / f"{label}.aedt"
        subprocess.run(
            [
                "python",
                str(INSPECT),
                str(BASE_PROJECT),
                "--set",
                str(updates_path),
                "--write-to",
                str(project_path),
                "--out",
                str(case_dir / "update_result.json"),
            ],
            check=True,
        )
        manifest.append(
            {
                "case": label,
                "updates": updates,
                "project_path": str(project_path),
                "output_dir": str(case_dir / "sim"),
                "plot_path": str(case_dir / "sim" / f"{label}.svg"),
            }
        )
    (OUT_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(OUT_ROOT / "manifest.json")


if __name__ == "__main__":
    main()
