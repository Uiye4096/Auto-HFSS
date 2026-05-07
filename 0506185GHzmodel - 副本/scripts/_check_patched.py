import re
from pathlib import Path

# Compare original vs patched AEDT for taper variables
orig = Path(r"D:\Desktop\HFSS_real\0506185GHzmodel - 副本\diplexer185GHzmodel.aedt").read_text(encoding="utf-8", errors="ignore")
patched = Path(r"D:\Desktop\HFSS_real\0506185GHzmodel - 副本\runs\026_w100_h025\result.aedt").read_text(encoding="utf-8", errors="ignore")

keywords = ["tapper", "w_tapper", "h_tapper", "cx", "cy"]

print("=== ORIGINAL: all lines containing tapper/cx/cy ===")
for i, line in enumerate(orig.splitlines()):
    if any(k in line for k in keywords):
        print(f"  L{i+1}: {line.strip()[:120]}")

print("\n=== PATCHED: all lines containing tapper/cx/cy ===")
for i, line in enumerate(patched.splitlines()):
    if any(k in line for k in keywords):
        print(f"  L{i+1}: {line.strip()[:120]}")
