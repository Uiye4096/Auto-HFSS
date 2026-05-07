from pathlib import Path

txt = Path(r"D:\Desktop\HFSS_real\0506185GHzmodel - 副本\final\diplexer_185g_087.aedt").read_text(encoding="utf-8", errors="ignore")
lines = txt.splitlines()

# Find the tapper polygon / body block and show surrounding context
print("=== Lines around w_tapper/h_tapper geometry ===")
for i, line in enumerate(lines):
    if "w_tapper" in line or "h_tapper" in line or "cx" in line.lower() and "VariableProp" not in line and "Variable=" not in line:
        start = max(0, i-3)
        end   = min(len(lines), i+4)
        print(f"  --- L{i+1} ---")
        for j in range(start, end):
            print(f"  L{j+1}: {lines[j].strip()[:120]}")

# Also find feedline origin/size to understand coordinate frame
print("\n=== Feedline l_line2185g geometry (OriginY, YSize) ===")
in_block = False
for i, line in enumerate(lines):
    s = line.strip()
    if "l_line2185g" in s and "YSize" in s:
        for j in range(max(0,i-5), min(len(lines),i+6)):
            print(f"  L{j+1}: {lines[j].strip()[:120]}")
        break

print("\n=== All OriginX/OriginY/XSize/YSize near tapper body ===")
for i, line in enumerate(lines):
    if any(k in line for k in ["w_tapper", "h_tapper"]):
        for j in range(max(0,i-15), min(len(lines),i+15)):
            s = lines[j].strip()
            if any(k in s for k in ["Origin", "XSize", "YSize", "ZSize", "X=", "Y=", "Z="]):
                print(f"  L{j+1}: {s[:120]}")
        break
