import os
import sys

AEDT_ROOT = r"E:\HFFS\HFSS_2021\Program Files\AnsysEM\AnsysEM21.2\Win64"
os.chdir(AEDT_ROOT)
sys.path.append(AEDT_ROOT)
sys.path.append(os.path.join(AEDT_ROOT, "PythonFiles", "DesktopPlugin"))

import clr
clr.AddReferenceToFileAndPath(os.path.join(AEDT_ROOT, "Ansys.Ansoft.CoreCOMScripting.dll"))

import ScriptEnv

out_path = r"D:\Desktop\HFSS_real\tools\aedt_ipy_ping.txt"

ScriptEnv.InitializeNew(NonGraphical=True)
with open(out_path, "w") as f:
    f.write("initialized\n")
ScriptEnv.Shutdown()
