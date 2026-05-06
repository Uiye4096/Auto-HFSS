import json
from pathlib import Path

ROOT = Path(r"D:\Desktop\HFSS_real\12GHzdiplexer\derived\hpf_line_probe")

LPF_3P8 = {
    "w_L512g": "0.304000mm",
    "w_C412g": "1.254000mm",
    "w_L312g": "0.152000mm",
    "w_C212g": "1.254000mm",
    "w_L112g": "0.342000mm",
    "L4_g312g": "0.600000mm",
}

CASES = {
    "lpf3p8_lline412g_0p5x": {**LPF_3P8, "l_line412g": "0.500000mm"},
    "lpf3p8_lline412g_1p5x": {**LPF_3P8, "l_line412g": "1.500000mm"},
    "lpf3p8_lline412g_2p0x": {**LPF_3P8, "l_line412g": "2.000000mm"},
    "lpf3p8_lline112g_1p5x": {**LPF_3P8, "l_line112g": "3.000000mm"},
}


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for case, updates in CASES.items():
        case_dir = ROOT / case
        case_dir.mkdir(parents=True, exist_ok=True)
        updates_path = case_dir / "updates.json"
        updates_path.write_text(json.dumps(updates, indent=2), encoding="utf-8")
        manifest.append({
            "case": case,
            "updates_path": str(updates_path),
            "project_path": str(case_dir / f"{case}.aedt"),
            "output_dir":   str(case_dir / "sim"),
        })
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Built {len(manifest)} cases under {ROOT}")


if __name__ == "__main__":
    main()
