import re
from pathlib import Path
txt = Path(r"D:\Desktop\HFSS_real\0506185GHzmodel - 副本\diplexer185GHzmodel.aedt").read_text(encoding="utf-8", errors="ignore")
keywords = ["tapper", "cx", "cy", "VariableOrders"]
for line in txt.splitlines():
    stripped = line.strip()
    if any(k in stripped for k in keywords) and "VariableProp" in stripped or "VariableOrders" in stripped:
        print(stripped[:120])
