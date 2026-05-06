"""
build_185g_refine17.py — Round 17: wC4 + l_line2 sweep on 087 base.

087 base: wC4=1.15, wC2=1.05, L4g3=0.85, L2g3=0.78, L7g3=0.83, L7g4=0.52
S11w=-9.3 dB (continuous 19-28 GHz), avg S21=-0.62 dB

Dir A: w_C4185g sweep 0.90-1.35mm (wC4 not tried on 087 base)
Dir B: l_line2185g sweep 0.30-1.00mm (base=0.60mm, HPF output line length)
→ 8 + 7 = 15 cases, UIDs 121-135
"""
import json, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _uid import next_uid

ROOT      = Path(__file__).parent.parent.parent
MODEL_DIR = Path(__file__).parent.parent
BASE_AEDT = MODEL_DIR / "diplexer185GHzmodel.aedt"
OUT_DIR   = MODEL_DIR / "runs"
INSPECT   = ROOT / "tools" / "aedt_inspect.py"

K=0.96; W_C4_BASE=1.15; W_C2=1.05; L4G3=0.85; L2G3=0.78; L7G3=0.83; L7G4=0.52
LPF_BASE = {"l_L5185g":0.7248,"l_C4185g":0.46508,"l_L3185g":0.9362,"l_C2185g":0.52548,"l_L1185g":0.6946}

# Dir A: wC4 sweep, l_line2 fixed at 0.6
WC4_VALS   = [0.90, 0.95, 1.00, 1.05, 1.10, 1.20, 1.25, 1.30]
# Dir B: l_line2 sweep, wC4 fixed at 1.15
LINE2_VALS = [0.30, 0.40, 0.50, 0.70, 0.80, 0.90, 1.00]

def build_case(uid, wc4, line2, label, dry_run=False):
    name = f"{uid}_{label}"
    rd   = OUT_DIR / name; rd.mkdir(parents=True, exist_ok=True)
    upd  = {"w_C4185g":f"{wc4}mm","w_C2185g":f"{W_C2}mm",
            "L4_g3185g":f"{L4G3}mm","L2_g3185g":f"{L2G3}mm",
            "L7_g3185g":f"{L7G3}mm","L7_g4185g":f"{L7G4}mm",
            "l_line2185g":f"{line2}mm"}
    for k,v in LPF_BASE.items(): upd[k]=f"{round(v*K,6)}mm"
    (rd/"updates.json").write_text(json.dumps(upd,indent=2),encoding="utf-8")
    if dry_run: print(f"  [dry] {name}"); return rd, name
    r = subprocess.run(["python",str(INSPECT),str(BASE_AEDT),
                        "--set",str(rd/"updates.json"),
                        "--write-to",str(rd/"result.aedt"),
                        "--out",str(rd/"update_result.json")],
                       capture_output=True,text=True)
    print(f"  {'Built' if r.returncode==0 else 'ERROR'}: {name}")
    return rd, name

def main():
    dry = "--dry-run" in sys.argv
    all_cases = (
        [(v, 0.60, f"wC4_{int(v*100):03d}", "A") for v in WC4_VALS] +
        [(W_C4_BASE, v, f"ll2_{int(v*100):03d}", "B") for v in LINE2_VALS]
    )
    print(f"Round 17: wC4 + l_line2 sweep on 087 base ({len(all_cases)} cases)")
    print(f"  Dir A: wC4 {WC4_VALS} (l_line2=0.60 fixed)")
    print(f"  Dir B: l_line2 {LINE2_VALS} (wC4=1.15 fixed)\n")
    uids = next_uid(count=len(all_cases)) if not dry else [f"DRY{i:03d}" for i in range(len(all_cases))]
    manifest = []
    for (wc4, ll2, lbl, dirn), uid in zip(all_cases, uids):
        rd, name = build_case(uid, wc4, ll2, lbl, dry)
        manifest.append({"uid":uid,"name":name,"run_dir":str(rd),
                         "dir":dirn,"w_C4":wc4,"l_line2":ll2,
                         "L4_g3185g":L4G3,"L2_g3185g":L2G3,
                         "L7_g3185g":L7G3,"L7_g4185g":L7G4})
    mp = MODEL_DIR/"runs"/"refine17_manifest.json"
    mp.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(f"\nManifest → {mp}")

if __name__ == "__main__": main()
