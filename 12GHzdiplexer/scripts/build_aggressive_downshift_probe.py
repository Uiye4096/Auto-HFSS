import json
from pathlib import Path

ROOT = Path(r"D:\Desktop\HFSS_real\12GHzdiplexer\derived\aggressive_downshift_probe")

CASES = {
    "L4_g312g_1p5": {"L4_g312g": "0.600000mm"},
    "L4_g312g_2p0": {"L4_g312g": "0.800000mm"}
}


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for case, updates in CASES.items():
        case_dir = ROOT / case
        case_dir.mkdir(parents=True, exist_ok=True)
        updates_path = case_dir / "updates.json"
        updates_path.write_text(json.dumps(updates, indent=2), encoding="utf-8")
        manifest.append(
            {
                "case": case,
                "updates_path": str(updates_path),
                "project_path": str(case_dir / f"{case}.aedt"),
                "output_dir": str(case_dir / "sim"),
            }
        )
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
