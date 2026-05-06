import os
import sys
import traceback
from datetime import datetime

AEDT_ROOT = r"E:\HFFS\HFSS_2021\Program Files\AnsysEM\AnsysEM21.2\Win64"
PROJECT_PATH = r"D:\Desktop\HFSS_real\12GHzdiplexer\derived\18p5_from_12GHzdiplexer_v3_lengths_only.aedt"
PROJECT_NAME = "18p5_from_12GHzdiplexer_v3_lengths_only"
DESIGN_NAME = "HFSSDesign1"
SETUP_NAME = "Setup1"
SWEEP_NAME = "Sweep"
OUTPUT_DIR = r"D:\Desktop\HFSS_real\12GHzdiplexer\derived\sim_18p5_v3_lengths_only"
LOG_PATH = os.path.join(OUTPUT_DIR, "run_18p5_analysis_v3_lengths_only.log")
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


def main():
    log("starting")
    ScriptEnv.InitializeNew(NonGraphical=True)
    try:
        oDesktop.RestoreWindow()
        log("opening project")
        oProject = oDesktop.OpenProject(PROJECT_PATH)
        oProject.SetActiveDesign(DESIGN_NAME)
        oDesign = oProject.GetActiveDesign()
        log("analyzing design")
        oDesign.AnalyzeAll()

        log("exporting convergence/profile")
        oDesign.ExportProfile(SETUP_NAME, "", PROFILE_PATH)
        oDesign.ExportConvergence(SETUP_NAME, "", CONV_PATH)

        log("listing solved variations")
        oModuleSolve = oDesign.GetModule("Solutions")
        variations = oModuleSolve.ListVariations("{}:{}".format(SETUP_NAME, SWEEP_NAME))
        log("variations={}".format(list(variations)))
        variation = variations[0] if len(variations) else ""

        log("exporting s-parameters")
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
