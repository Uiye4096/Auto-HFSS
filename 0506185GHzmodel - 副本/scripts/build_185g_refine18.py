"""
build_185g_refine18.py — Round 18: wC4 fine sweep 1.00-1.12mm on 087 base.

Round 17 revealed wC4=1.00-1.10 ALL break S11w ≤ -10 dB target.
Best combo: 125 (wC4=1.10) for S31 shape, 123 (wC4=1.00) for S11.
Fine sweep to find optimum balancing S11w + S31@20 + ripple.

wC4 = [1.00, 1.02, 1.04, 1.06, 1.08, 1.10, 1.12] → UIDs 136-142
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

K=0.96; W_C2=1.05; L4G3=0.85; L2G3=0.78; L7G3=0.83; L7G4=0.52; LINE2=0.60
LPF_BASE = {"l_L5185g":0.7248,"l_C4185g":0.46508,"l_L3185g":0.9362,"l_C2185g":0.52548,"l_L1185g":0.6946}
WC4_VALS = [1.00, 1.02, 1.04, 1.06, 1.08, 1.10, 1.12]

def build_case(uid, wc4, dry_run=False):
    name = f"{uid}_wC4f_{int(round(wc4*100)):03d}"
    rd   = OUT_DIR / name; rd.mkdir(parents=True, exist_ok=True)
    upd  = {"w_C4185g":f"{wc4}mm","w_C2185g":f"{W_C2}mm",
            "L4_g3185g":f"{L4G3}mm","L2_g3185g":f"{L2G3}mm",
            "L7_g3185g":f"{L7G3}mm","L7_g4185g":f"{L7G4}mm",
            "l_line2185g":f"{LINE2}mm"}
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
    print(f"Round 18: wC4 fine sweep on 087 base ({len(WC4_VALS)} cases)")
    print(f"  wC4 = {WC4_VALS}  (087 ref = 1.15, 125 best S31 = 1.10, 123 best S11 = 1.00)\n")
    uids = next_uid(count=len(WC4_VALS)) if not dry else [f"DRY{i:03d}" for i in range(len(WC4_VALS))]
    manifest = []
    for wc4, uid in zip(WC4_VALS, uids):
        rd, name = build_case(uid, wc4, dry)
        manifest.append({"uid":uid,"name":name,"run_dir":str(rd),
                         "w_C4":wc4,"w_C2":W_C2,"l_line2":LINE2,
                         "L4_g3185g":L4G3,"L2_g3185g":L2G3,
                         "L7_g3185g":L7G3,"L7_g4185g":L7G4})
    mp = MODEL_DIR/"runs"/"refine18_manifest.json"
    mp.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(f"Manifest → {mp}")

if __name__ == "__main__": main()
