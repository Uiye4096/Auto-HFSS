import os
import sys
import traceback
from datetime import datetime

AEDT_ROOT = r"E:\HFFS\HFSS_2021\Program Files\AnsysEM\AnsysEM21.2\Win64"
PROJECT_PATH = r"D:\Desktop\HFSS_real\12GHzdiplexer\derived\18p5_from_12GHzdiplexer_v2b.aedt"
PROJECT_NAME = "18p5_from_12GHzdiplexer_v2b"
DESIGN_NAME = "HFSSDesign1"
OUTPUT_DIR = r"D:\Desktop\HFSS_real\12GHzdiplexer\derived\sim_18p5_v2b"
LOG_PATH = os.path.join(OUTPUT_DIR, "diagnose_v2b_failure.log")

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


def dump_messages(level):
    try:
        msgs = list(oDesktop.GetMessages(PROJECT_NAME, DESIGN_NAME, level))
        log("messages level {} count {}".format(level, len(msgs)))
        for msg in msgs:
            log(msg)
    except:
        log("failed to dump messages for level {}".format(level))


def main():
    log("starting")
    ScriptEnv.InitializeNew(NonGraphical=True)
    try:
        oDesktop.RestoreWindow()
        oProject = oDesktop.OpenProject(PROJECT_PATH)
        oProject.SetActiveDesign(DESIGN_NAME)
        oDesign = oProject.GetActiveDesign()
        try:
            oDesign.AnalyzeAll()
            log("analyze ok")
        except:
            log("analyze failed")
            log(traceback.format_exc())
            dump_messages(0)
            dump_messages(1)
            dump_messages(2)
            raise
    finally:
        try:
            ScriptEnv.Shutdown()
        except:
            pass


if __name__ == "__main__":
    main()
