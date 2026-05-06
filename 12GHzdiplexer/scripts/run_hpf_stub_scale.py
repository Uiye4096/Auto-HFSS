"""
Materialize, run HFSS, and plot SVG for every hpf_stub_scale case.
Run with system Python (not IronPython).
"""
import json
import os
import subprocess
from pathlib import Path

ROOT         = Path(r"D:\Desktop\HFSS_real\12GHzdiplexer\derived\hpf_stub_scale")
BASE_PROJECT = Path(r"D:\Desktop\HFSS_real\12GHzdiplexer\derived\12GHzdiplexer_analysiscopy.aedt")
INSPECT      = Path(r"D:\Desktop\HFSS_real\tools\aedt_inspect.py")
RUNNER       = Path(r"D:\Desktop\HFSS_real\12GHzdiplexer\scripts\run_hfss_case.py")
PLOT         = Path(r"D:\Desktop\HFSS_real\tools\plot_s3p.py")
IPY          = r"E:\HFFS\HFSS_2021\Program Files\AnsysEM\AnsysEM21.2\Win64\common\IronPython\ipy64.exe"


def materialize(item):
    out_report = Path(item["project_path"]).with_name("update_result.json")
    subprocess.run([
        "python", str(INSPECT),
        str(BASE_PROJECT),
        "--set",      item["updates_path"],
        "--write-to", item["project_path"],
        "--out",      str(out_report),
    ], check=True)
    result = json.loads(out_report.read_text(encoding="utf-8"))
    print(f"    updated={result['updated']}  missing={result['missing']}")


def run_hfss(item):
    ret = subprocess.run([IPY, str(RUNNER), item["project_path"], item["output_dir"]])
    return ret.returncode == 0


def plot(item):
    name = Path(item["project_path"]).stem
    s3p  = Path(item["output_dir"]) / f"{name}.s3p"
    if s3p.exists():
        subprocess.run(["python", str(PLOT), str(s3p), "--open"])
    else:
        print(f"    WARNING: {s3p} not found, skipping plot")


def main():
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    for item in manifest:
        print(f"\n{'='*60}")
        print(f"Case: {item['case']}  (scale={item['scale']})")

        print("  [1/3] Materializing AEDT ...")
        materialize(item)

        print("  [2/3] Running HFSS ...")
        ok = run_hfss(item)
        if not ok:
            print("  HFSS FAILED — skipping plot, continuing to next case.")
            continue

        print("  [3/3] Plotting ...")
        plot(item)

    print("\nAll done.")


if __name__ == "__main__":
    main()
