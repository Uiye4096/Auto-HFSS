import json
from pathlib import Path


BASE = {
    "l_L512g": 0.77,
    "l_C412g": 0.616,
    "l_L312g": 0.792,
    "l_C212g": 0.506,
    "l_L112g": 0.616,
}

FACTORS = [0.99, 1.00]
ROOT = Path(r"D:\Desktop\HFSS_real\12GHzdiplexer\derived\safe_sweep")


def fmt_mm(value):
    return f"{value:.6f}mm"


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for factor in FACTORS:
        case = f"len_scale_{str(factor).replace('.', 'p')}"
        case_dir = ROOT / case
        case_dir.mkdir(parents=True, exist_ok=True)
        updates = {k: fmt_mm(v * factor) for k, v in BASE.items()}
        updates_path = case_dir / "updates.json"
        updates_path.write_text(json.dumps(updates, indent=2), encoding="utf-8")
        manifest.append(
            {
                "case": case,
                "factor": factor,
                "updates_path": str(updates_path),
                "project_path": str(case_dir / f"{case}.aedt"),
                "output_dir": str(case_dir / "sim"),
            }
        )
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
