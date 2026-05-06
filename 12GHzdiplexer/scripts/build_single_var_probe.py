import json
from pathlib import Path

ROOT = Path(r"D:\Desktop\HFSS_real\12GHzdiplexer\derived\single_var_probe")
CASES = {
    "l_L512g_0p99": {"l_L512g": "0.762300mm"},
    "l_C412g_0p99": {"l_C412g": "0.609840mm"},
    "l_L312g_0p99": {"l_L312g": "0.784080mm"},
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
