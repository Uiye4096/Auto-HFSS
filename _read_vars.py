import json
from pathlib import Path
data = json.loads(Path(r"D:\Desktop\HFSS_real\0506185GHzmodel - 副本\vars_185g.json").read_text(encoding="utf-8"))
for item in data:
    print("=== Variables ===")
    for v in item.get("variables", []):
        print(f"  {v['name']:<30} = {v['value']}")
