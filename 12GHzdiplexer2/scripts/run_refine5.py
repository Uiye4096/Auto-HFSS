"""Run refine5: solve + SVG plot + open per case."""
import json
import subprocess
from pathlib import Path

ROOT     = Path(r"D:\Desktop\HFSS_real")
OUT_ROOT = ROOT / "12GHzdiplexer2" / "derived" / "refine5"
RUNNER   = ROOT / "12GHzdiplexer" / "scripts" / "run_hfss_case.py"
PLOT     = ROOT / "tools" / "plot_s3p.py"
IPY      = r"E:\HFFS\HFSS_2021\Program Files\AnsysEM\AnsysEM21.2\Win64\common\IronPython\ipy64.exe"


def main():
    manifest = json.loads((OUT_ROOT / "manifest.json").read_text(encoding="utf-8"))
    for item in manifest:
        print(f"\n{'='*60}\nCase: {item['case']}")
        ret = subprocess.run([IPY, str(RUNNER), item["project_path"], item["output_dir"]])
        if ret.returncode != 0:
            print("  HFSS FAILED — skipping plot.")
            continue
        name = Path(item["project_path"]).stem
        s3p  = Path(item["output_dir"]) / f"{name}.s3p"
        if s3p.exists():
            subprocess.run(["python", str(PLOT), str(s3p), "--open"])
        else:
            print(f"  WARNING: {s3p} not found")
    print("\nAll done.")


if __name__ == "__main__":
    main()
