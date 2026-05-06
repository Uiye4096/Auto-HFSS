import json
from pathlib import Path

ROOT = Path(r"D:\Desktop\HFSS_real\12GHzdiplexer\derived\l4g312_sweep")
BASE = 0.4
FACTORS = [0.90, 1.10]


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for factor in FACTORS:
        case = "L4_g312g_" + str(factor).replace(".", "p")
        case_dir = ROOT / case
        case_dir.mkdir(parents=True, exist_ok=True)
        value = f"{BASE * factor:.6f}mm"
        updates = {"L4_g312g": value}
        updates_path = case_dir / "updates.json"
        updates_path.write_text(json.dumps(updates, indent=2), encoding="utf-8")
        manifest.append(
            {
                "case": case,
                "factor": factor,
                "value": value,
                "updates_path": str(updates_path),
                "project_path": str(case_dir / f"{case}.aedt"),
                "output_dir": str(case_dir / "sim"),
            }
        )
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
