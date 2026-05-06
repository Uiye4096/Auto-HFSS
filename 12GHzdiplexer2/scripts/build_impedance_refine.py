import json
import subprocess
from pathlib import Path


ROOT = Path(r"D:\Desktop\HFSS_real")
MODEL = ROOT / "12GHzdiplexer2"
BASE_PROJECT = MODEL / "12GHzdiplexer.aedt"
OUT_ROOT = MODEL / "derived" / "impedance_sweep_refine"
INSPECT = ROOT / "tools" / "aedt_inspect.py"

ALIGNMENT = {
    "compensation_y": "L2_g212g + cover_HPF_out12g + l_line212g + 1.426mm - l_sub12g",
    "compensation_y_2": (
        "l_line312g + l_L512g + l_C412g + l_L312g + l_C212g + "
        "l_L112g + l_line412g - l_sub_LPF12g"
    ),
}

CASES = {
    "r01_case09_base": {
        "w_C1_y": "0.170000mm",
        "L4_g312g": "1.000000mm",
        "L2_g312g": "0.850000mm",
        "index1": "0.600000m",
    },
    "r02_l4_1p05": {
        "w_C1_y": "0.170000mm",
        "L4_g312g": "1.050000mm",
        "L2_g312g": "0.850000mm",
        "index1": "0.600000m",
    },
    "r03_l4_0p95": {
        "w_C1_y": "0.170000mm",
        "L4_g312g": "0.950000mm",
        "L2_g312g": "0.850000mm",
        "index1": "0.600000m",
    },
    "r04_l2_0p90": {
        "w_C1_y": "0.170000mm",
        "L4_g312g": "1.000000mm",
        "L2_g312g": "0.900000mm",
        "index1": "0.600000m",
    },
    "r05_l2_0p80": {
        "w_C1_y": "0.170000mm",
        "L4_g312g": "1.000000mm",
        "L2_g312g": "0.800000mm",
        "index1": "0.600000m",
    },
    "r06_idx_0p50": {
        "w_C1_y": "0.170000mm",
        "L4_g312g": "1.000000mm",
        "L2_g312g": "0.850000mm",
        "index1": "0.500000m",
    },
    "r07_idx_0p70": {
        "w_C1_y": "0.170000mm",
        "L4_g312g": "1.000000mm",
        "L2_g312g": "0.850000mm",
        "index1": "0.700000m",
    },
    "r08_c1y_0p20": {
        "w_C1_y": "0.200000mm",
        "L4_g312g": "1.000000mm",
        "L2_g312g": "0.850000mm",
        "index1": "0.600000m",
    },
}


def main():
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for case, base_updates in CASES.items():
        case_dir = OUT_ROOT / case
        case_dir.mkdir(parents=True, exist_ok=True)
        updates = dict(base_updates)
        updates.update(ALIGNMENT)
        updates_path = case_dir / "updates.json"
        updates_path.write_text(json.dumps(updates, indent=2), encoding="utf-8")
        project_path = case_dir / f"{case}.aedt"
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
                "case": case,
                "updates": updates,
                "project_path": str(project_path),
                "output_dir": str(case_dir / "sim"),
                "plot_path": str(case_dir / "sim" / f"{case}.svg"),
            }
        )
    (OUT_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(OUT_ROOT / "manifest.json")


if __name__ == "__main__":
    main()
