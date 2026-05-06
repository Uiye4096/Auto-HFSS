import json
import subprocess
from pathlib import Path

ROOT = Path(r"D:\Desktop\HFSS_real\12GHzdiplexer\derived\l4g312_sweep")
BASE_PROJECT = Path(r"D:\Desktop\HFSS_real\12GHzdiplexer\derived\12GHzdiplexer_analysiscopy.aedt")
INSPECT = Path(r"D:\Desktop\HFSS_real\tools\aedt_inspect.py")


def main():
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    for item in manifest:
        out_report = Path(item["project_path"]).with_name("update_result.json")
        cmd = [
            "python",
            str(INSPECT),
            str(BASE_PROJECT),
            "--set",
            item["updates_path"],
            "--write-to",
            item["project_path"],
            "--out",
            str(out_report),
        ]
        subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
