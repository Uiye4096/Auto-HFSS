"""
Refine8: fix the HPF passband dip by tuning l_line312g (LPF junction feed line).

Root cause of dip: Im(Yin,LP) + Im(Yin,HP) != 0 at 20-22 GHz -> poor S11 -> HPF dip.
Per Rehner 2009: add short feed lines (+4deg at fT for LPF, +7deg for HPF) to improve
complementary admittance condition.
  At fT=18.5GHz in SSL: lambda ~ 6.4mm, 4deg ~ 0.071mm, 7deg ~ 0.124mm.

l_line312g baseline = 0.04mm (essentially no LPF feed line).
l_line212g baseline = 1mm  (HPF feed line already long).

Strategy:
  - Sweep l_line312g from 0.04 to 0.30mm (add LPF phase compensation)
  - Start from u05 base (L4_g312g=0.90, best dip) + idx=0.4 (best crossing)
  - Also test modified l_line212g on the HPF side

compensation_y   covers l_line212g changes (HPF geometry auto-adjusts)
compensation_y_2 covers l_line312g changes (LPF geometry auto-adjusts)
"""
import json
import subprocess
from pathlib import Path

ROOT         = Path(r"D:\Desktop\HFSS_real")
MODEL        = ROOT / "12GHzdiplexer2"
BASE_PROJECT = MODEL / "12GHzdiplexer.aedt"
OUT_ROOT     = MODEL / "derived" / "refine8"
INSPECT      = ROOT / "tools" / "aedt_inspect.py"

ALIGNMENT = {
    "compensation_y":   "L2_g212g + cover_HPF_out12g + l_line212g + 1.426mm - l_sub12g",
    "compensation_y_2": (
        "l_line312g + l_L512g + l_C412g + l_L312g + l_C212g + "
        "l_L112g + l_line412g - l_sub_LPF12g"
    ),
}

# u05-like base (L4=0.90 gives shallowest dip) + idx=0.4 (best crossing direction)
BASE_U05_IDX04 = {
    "w_C1_y":   "0.250000mm",
    "L4_g312g": "0.900000mm",
    "L2_g312g": "0.800000mm",
    "index1":   "0.400000m",
}

# w04-like base (best crossing so far: 18.747 GHz)
BASE_W04 = {
    "w_C1_y":   "0.300000mm",
    "L4_g312g": "1.000000mm",
    "L2_g312g": "0.750000mm",
    "index1":   "0.400000m",
}

CASES = {
    # Sweep l_line312g on u05+idx04 base: how does LPF phase stub affect dip?
    "y01_u05base_l312_010": {**BASE_U05_IDX04, "l_line312g": "0.100000mm"},
    "y02_u05base_l312_020": {**BASE_U05_IDX04, "l_line312g": "0.200000mm"},
    "y03_u05base_l312_030": {**BASE_U05_IDX04, "l_line312g": "0.300000mm"},
    # Sweep l_line312g on w04 base (best crossing)
    "y04_w04base_l312_010": {**BASE_W04, "l_line312g": "0.100000mm"},
    "y05_w04base_l312_020": {**BASE_W04, "l_line312g": "0.200000mm"},
}


def main():
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for case, base_upd in CASES.items():
        case_dir = OUT_ROOT / case
        case_dir.mkdir(parents=True, exist_ok=True)
        updates = dict(base_upd)
        updates.update(ALIGNMENT)
        up_path   = case_dir / "updates.json"
        proj_path = case_dir / f"{case}.aedt"
        up_path.write_text(json.dumps(updates, indent=2), encoding="utf-8")
        subprocess.run(
            ["python", str(INSPECT), str(BASE_PROJECT),
             "--set", str(up_path),
             "--write-to", str(proj_path),
             "--out", str(case_dir / "update_result.json")],
            check=True,
        )
        manifest.append({
            "case":         case,
            "updates":      base_upd,
            "project_path": str(proj_path),
            "output_dir":   str(case_dir / "sim"),
        })
        print(f"  {case}  l312={base_upd.get('l_line312g','0.04(base)')}")
    (OUT_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nBuilt {len(manifest)} cases -> {OUT_ROOT}")


if __name__ == "__main__":
    main()
