import json
from pathlib import Path

ROOT = Path(r"D:\Desktop\HFSS_real\12GHzdiplexer\derived\l4_gap_probe")
CASES = {
    "L4_g212g_1p05": {"L4_g212g": "0.063000mm"},
    "L4_g212g_0p95": {"L4_g212g": "0.057000mm"},
    "L4_g112g_1p05": {"L4_g112g": "0.073500mm"},
    "L4_g112g_0p95": {"L4_g112g": "0.066500mm"},
    "L4_g412g_1p05": {"L4_g412g": "0.315000mm"},
    "L4_g412g_0p95": {"L4_g412g": "0.285000mm"},
    "L4_g312g_1p05": {"L4_g312g": "0.420000mm"},
    "L4_g312g_0p95": {"L4_g312g": "0.380000mm"}
}


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name, updates in CASES.items():
        case_dir = ROOT / name
        case_dir.mkdir(parents=True, exist_ok=True)
        updates_path = case_dir / "updates.json"
        updates_path.write_text(json.dumps(updates, indent=2), encoding="utf-8")
        manifest.append(
            {
                "case": name,
                "updates_path": str(updates_path),
                "project_path": str(case_dir / f"{name}.aedt"),
                "output_dir": str(case_dir / "sim"),
            }
        )
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
