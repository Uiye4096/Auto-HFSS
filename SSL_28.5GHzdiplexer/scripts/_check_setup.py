"""Check HFSS setup frequency and sweep range in the baseline AEDT."""
import re
from pathlib import Path

aedt = Path(r"D:\Desktop\HFSS_real\SSL_28.5GHzdiplexer\runs\008_L2g3_045\result.aedt").read_text(errors="ignore")

# Find Sweep section
idx = aedt.find("Sweep")
while idx >= 0:
    block = aedt[idx:idx+500]
    if "StartValue" in block or "StopValue" in block or "SweepType" in block:
        print("Found at offset", idx)
        print(block[:400])
        print("---")
    idx = aedt.find("Sweep", idx+1)
    if idx > 50000: break

print("\nAll frequency-like values:")
for m in re.finditer(r"(Frequency|StartValue|StopValue)\s*=\s*'[^']*'", aedt):
    print(" ", m.group())
