"""
build_185g_refine15.py — Round 15: L4_g3185g sweep on 090 base.

090 base: wC4=1.15, wC2=1.05, L4g3=0.85, L2g3=0.78, L7g3=0.83, L7g4=0.50
S11w=-9.4 dB. L4_g3 is the HPF mid-section coupling stub — unexplored with 090 base.

Dir A: L4_g3 sweep 0.70–1.00mm (fixed L2_g3=0.78)
Dir B: L2_g3 sweep 0.65–0.90mm (fixed L4_g3=0.85)
→ 7 + 6 = 13 cases, UIDs 101-113
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

K=0.96; W_C4=1.15; W_C2=1.05; L7G3=0.83; L7G4=0.50

LPF_BASE = {"l_L5185g":0.7248,"l_C4185g":0.46508,"l_L3185g":0.9362,"l_C2185g":0.52548,"l_L1185g":0.6946}

# Dir A: sweep L4_g3, fix L2_g3=0.78
L4G3_VALS = [0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00]
L2G3_BASE = 0.78

# Dir B: sweep L2_g3, fix L4_g3=0.85
L4G3_BASE = 0.85
L2G3_VALS = [0.65, 0.70, 0.74, 0.82, 0.86, 0.90]

def build_case(uid, l4g3, l2g3, label, dry_run=False):
    name = f"{uid}_{label}"
    rd   = OUT_DIR / name; rd.mkdir(parents=True, exist_ok=True)
    upd  = {"w_C4185g":f"{W_C4}mm","w_C2185g":f"{W_C2}mm",
            "L4_g3185g":f"{l4g3}mm","L2_g3185g":f"{l2g3}mm",
            "L7_g3185g":f"{L7G3}mm","L7_g4185g":f"{L7G4}mm"}
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
        [(v, L2G3_BASE, f"L4g3_{int(v*100):03d}", "A") for v in L4G3_VALS] +
        [(L4G3_BASE, v, f"L2g3_{int(v*100):03d}", "B") for v in L2G3_VALS]
    )
    print(f"Round 15: L4_g3 + L2_g3 sweep on 090 base ({len(all_cases)} cases)")
    print(f"  Dir A: L4_g3 {L4G3_VALS} (L2g3=0.78 fixed)")
    print(f"  Dir B: L2_g3 {L2G3_VALS} (L4g3=0.85 fixed)\n")
    uids = next_uid(count=len(all_cases)) if not dry else [f"DRY{i:03d}" for i in range(len(all_cases))]
    manifest = []
    for (l4, l2, lbl, dirn), uid in zip(all_cases, uids):
        rd, name = build_case(uid, l4, l2, lbl, dry)
        manifest.append({"uid":uid,"name":name,"run_dir":str(rd),
                         "dir":dirn,"L4_g3185g":l4,"L2_g3185g":l2,
                         "L7_g3185g":L7G3,"L7_g4185g":L7G4,"w_C2":W_C2})
    mp = MODEL_DIR/"runs"/"refine15_manifest.json"
    mp.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(f"\nManifest → {mp}")

if __name__ == "__main__": main()
