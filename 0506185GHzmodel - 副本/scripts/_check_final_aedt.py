import re
from pathlib import Path

f = Path(r"D:\Desktop\HFSS_real\0506185GHzmodel - 副本\final\diplexer_185g_087.aedt")
txt = f.read_text(encoding="utf-8", errors="ignore")
lines = txt.splitlines()

print(f"File size: {f.stat().st_size//1024} KB,  lines: {len(lines)}")

print("\n=== All VariableOrders lines ===")
for i, line in enumerate(lines):
    if "VariableOrders" in line:
        print(f"  L{i+1}: {line.strip()[:250]}")

print("\n=== All VariableProp lines ===")
for i, line in enumerate(lines):
    s = line.strip()
    if s.startswith("VariableProp("):
        print(f"  L{i+1}: {s[:120]}")

print("\n=== Lines with 'tapper', 'w_tapper', 'h_tapper' ===")
for i, line in enumerate(lines):
    if "tapper" in line.lower():
        print(f"  L{i+1}: {line.strip()[:120]}")
