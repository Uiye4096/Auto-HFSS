import re
from pathlib import Path
txt = Path(r"D:\Desktop\HFSS_real\0506185GHzmodel - 副本\diplexer185GHzmodel.aedt").read_text(encoding="utf-8", errors="ignore")
# Find all VariableProp lines
for line in txt.splitlines():
    s = line.strip()
    if s.startswith("VariableProp("):
        print(s[:120])
