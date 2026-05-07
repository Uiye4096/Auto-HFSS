from pathlib import Path

txt = Path(r"D:\Desktop\HFSS_real\0506185GHzmodel - 副本\diplexer185GHzmodel.aedt").read_text(encoding="utf-8", errors="ignore")
lines = txt.splitlines()

# Look for VariableOrders sections to confirm variable list
print("=== All VariableOrders lines ===")
for i, line in enumerate(lines):
    if "VariableOrders" in line:
        print(f"  L{i+1}: {line.strip()[:200]}")

# Look for 'cx', 'w_tapper' as standalone strings (variable references in expressions)
print("\n=== Lines referencing 'w_tapper' or 'h_tapper' as literal string ===")
hits = [(i+1, line.strip()[:120]) for i, line in enumerate(lines)
        if "w_tapper" in line or "h_tapper" in line]
for ln, txt2 in hits[:20]:
    print(f"  L{ln}: {txt2}")

print("\n=== Lines referencing 'cx' or 'cy' as VariableProp-style ===")
hits2 = [(i+1, line.strip()[:120]) for i, line in enumerate(lines)
         if "'cx'" in line or "'cy'" in line or '"cx"' in line or '"cy"' in line]
for ln, txt2 in hits2[:20]:
    print(f"  L{ln}: {txt2}")
