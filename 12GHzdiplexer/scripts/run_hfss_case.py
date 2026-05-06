import os
import sys
import traceback
from datetime import datetime
import time

AEDT_ROOT = r"E:\HFFS\HFSS_2021\Program Files\AnsysEM\AnsysEM21.2\Win64"
DESIGN_NAME = "HFSSDesign1"
SETUP_NAME = "Setup1"
SWEEP_NAME = "Sweep"

if len(sys.argv) < 3:
    raise SystemExit("usage: run_hfss_case.py <project_path> <output_dir>")

PROJECT_PATH = sys.argv[1]
OUTPUT_DIR = sys.argv[2]
PROJECT_NAME = os.path.splitext(os.path.basename(PROJECT_PATH))[0]
LOG_PATH = os.path.join(OUTPUT_DIR, "run.log")
SNP_PATH = os.path.join(OUTPUT_DIR, PROJECT_NAME + ".s3p")
PROFILE_PATH = os.path.join(OUTPUT_DIR, PROJECT_NAME + ".prof")
CONV_PATH = os.path.join(OUTPUT_DIR, PROJECT_NAME + ".conv")

if not os.path.isdir(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
os.chdir(AEDT_ROOT)
sys.path.append(AEDT_ROOT)
sys.path.append(os.path.join(AEDT_ROOT, "PythonFiles", "DesktopPlugin"))

import clr
clr.AddReferenceToFileAndPath(os.path.join(AEDT_ROOT, "Ansys.Ansoft.CoreCOMScripting.dll"))
import ScriptEnv


def log(message):
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_PATH, "a") as f:
        f.write("[{}] {}\n".format(stamp, message))


def open_project_with_retry(project_path, attempts=3, sleep_s=8):
    last_exc = None
    for i in range(1, attempts + 1):
        try:
            if i > 1:
                log("retrying OpenProject attempt {}/{}".format(i, attempts))
            return oDesktop.OpenProject(project_path)
        except Exception as exc:
            last_exc = exc
            log("OpenProject failed attempt {}/{}: {}".format(i, attempts, exc))
            if i < attempts:
                time.sleep(sleep_s)
    raise last_exc


def main():
    log("starting {}".format(PROJECT_NAME))
    ScriptEnv.InitializeNew(NonGraphical=True)
    try:
        oDesktop.RestoreWindow()
        oProject = open_project_with_retry(PROJECT_PATH)
        oProject.SetActiveDesign(DESIGN_NAME)
        oDesign = oProject.GetActiveDesign()
        log("analyzing")
        oDesign.AnalyzeAll()
        log("exporting")
        oDesign.ExportProfile(SETUP_NAME, "", PROFILE_PATH)
        oDesign.ExportConvergence(SETUP_NAME, "", CONV_PATH)
        oModuleSolve = oDesign.GetModule("Solutions")
        variations = oModuleSolve.ListVariations("{}:{}".format(SETUP_NAME, SWEEP_NAME))
        variation = variations[0] if len(variations) else ""
        oModuleSolve.ExportNetworkData(
            variation,
            ["{}:{}".format(SETUP_NAME, SWEEP_NAME)],
            3,
            SNP_PATH,
            ["All"],
            True,
            50,
            "S",
            -1,
            0,
            15,
            True,
            False,
            False,
        )
        oProject.Save()
        log("done")
    except:
        log("exception")
        log(traceback.format_exc())
        raise
    finally:
        try:
            ScriptEnv.Shutdown()
        except:
            pass


if __name__ == "__main__":
    main()
