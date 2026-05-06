import json
from pathlib import Path

ROOT = Path(r"D:\Desktop\HFSS_real\12GHzdiplexer\derived\hpf_width_probe")
CASES = {
    "w_L412g_1p05": {"w_L412g": "0.058800mm"},
    "w_L412g_0p95": {"w_L412g": "0.053200mm"},
    "w_L212g_1p05": {"w_L212g": "0.033600mm"},
    "w_L212g_0p95": {"w_L212g": "0.030400mm"}
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
