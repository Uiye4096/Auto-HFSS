import json
import os
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(r"D:\Desktop\HFSS_real")
MODEL = ROOT / "12GHzdiplexer2"
MANIFEST = MODEL / "derived" / "impedance_sweep_refine" / "manifest.json"
HFSS_RUNNER = ROOT / "12GHzdiplexer" / "scripts" / "run_hfss_case.py"
PLOTTER = MODEL / "scripts" / "plot_sparams_png.py"
IPY = Path(r"E:\HFFS\HFSS_2021\Program Files\AnsysEM\AnsysEM21.2\Win64\common\IronPython\ipy64.exe")


def main():
    only = set(sys.argv[1:])
    cases = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for item in cases:
        if only and item["case"] not in only:
            continue
        project_path = Path(item["project_path"])
        output_dir = Path(item["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        snp_path = output_dir / f"{project_path.stem}.s3p"
        plot_path = Path(item["plot_path"])
        if snp_path.exists():
            print(f"SKIP {item['case']} existing", flush=True)
        else:
            print(f"RUN {item['case']} {item['updates']}", flush=True)
            try:
                subprocess.run([str(IPY), str(HFSS_RUNNER), str(project_path), str(output_dir)], check=True)
            except subprocess.CalledProcessError as exc:
                print(f"FAIL {item['case']} exit={exc.returncode}", flush=True)
                continue
        subprocess.run(
            ["python", str(PLOTTER), str(snp_path), str(plot_path), "--title", f"{item['case']}  {item['updates']}"],
            check=True,
        )
        print(f"PLOT {plot_path}", flush=True)
        os.startfile(str(plot_path))
        time.sleep(1)


if __name__ == "__main__":
    main()
