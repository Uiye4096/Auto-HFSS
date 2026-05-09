import re
from pathlib import Path
aedt = Path(r"D:\Desktop\HFSS_real\SSL_28.5GHzdiplexer\final\diplexer_285g_baseline.aedt").read_text(errors="ignore")
for m in re.finditer(r"(Frequency|RangeStart|RangeEnd)='[^']*'", aedt):
    print(m.group())
