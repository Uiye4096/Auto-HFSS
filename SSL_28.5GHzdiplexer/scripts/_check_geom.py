"""Print all Box/Polyline geometry that uses l_C4185g or l_C2185g to find their direction."""
from pathlib import Path
import re

aedt = Path(r"D:\Desktop\HFSS_real\0506185GHzmodel - 副本\diplexer185GHzmodel.aedt").read_text(errors="ignore")

# Find sections that reference l_C4185g or l_C2185g
for var in ["l_C4185g", "l_C2185g", "l_L5185g", "l_L3185g"]:
    # Find the pattern in geometry
    for m in re.finditer(re.escape(var), aedt):
        idx = m.start()
        # Get surrounding context (500 chars before and after)
        start = max(0, idx - 300)
        end = min(len(aedt), idx + 200)
        snippet = aedt[start:end]
        # Only show if it's in a geometry block (has XSize/YSize/ZSize nearby)
        if any(k in snippet for k in ["XSize", "YSize", "ZSize", "SizeVector"]):
            print(f"\n{'='*50}")
            print(f"Variable: {var}")
            print(snippet)
            break  # Just show first hit per variable
