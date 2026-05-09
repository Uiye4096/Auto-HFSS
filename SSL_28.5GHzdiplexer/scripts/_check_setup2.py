"""Print full sweep block from AEDT."""
from pathlib import Path

aedt = Path(r"D:\Desktop\HFSS_real\SSL_28.5GHzdiplexer\runs\008_L2g3_045\result.aedt").read_text(errors="ignore")

# Find AnalysisSetup block
idx = aedt.find("AnalysisSetup")
if idx >= 0:
    print(aedt[idx:idx+2000])
