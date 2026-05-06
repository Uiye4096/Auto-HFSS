"""
build_185g_refine14.py — Round 14: w_C2185g sweep on 090 base.

Base: 090 (k=0.96, wC4=1.15, wC2=1.05, L4g3=0.85, L2g3=0.78, L7g3=0.83, L7g4=0.50)
S11w=-9.4 dB. w_C2 affects HPF arm low-end matching (19-22 GHz).
Goal: push S11w to ≤-10 dB.

Sweep w_C2185g = [0.90, 0.95, 1.00, 1.05, 1.10, 1.15, 1.20]
(1.05 is 090 reference, included for continuity)
→ UIDs 094-100
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

K=0.96; W_C4=1.15; L2G3=0.78; L4G3=0.85; L7G3=0.83; L7G4=0.50

LPF_BASE = {"l_L5185g":0.7248,"l_C4185g":0.46508,"l_L3185g":0.9362,"l_C2185g":0.52548,"l_L1185g":0.6946}
WC2_VALS = [0.90, 0.95, 1.00, 1.05, 1.10, 1.15, 1.20]

def build_case(uid, wc2, dry_run=False):
    name = f"{uid}_wC2_{int(round(wc2*100)):03d}"
    rd   = OUT_DIR / name; rd.mkdir(parents=True, exist_ok=True)
    upd  = {"w_C4185g":f"{W_C4}mm","w_C2185g":f"{wc2}mm",
            "L4_g3185g":f"{L4G3}mm","L2_g3185g":f"{L2G3}mm",
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
    print(f"Round 14: w_C2185g sweep on 090 base (L7g3=0.83, L7g4=0.50)")
    print(f"  w_C2185g = {WC2_VALS}  (1.05 = 090 ref)\n")
    uids = next_uid(count=len(WC2_VALS)) if not dry else [f"DRY{i:03d}" for i in range(len(WC2_VALS))]
    manifest = []
    for wc2, uid in zip(WC2_VALS, uids):
        rd, name = build_case(uid, wc2, dry)
        manifest.append({"uid":uid,"name":name,"run_dir":str(rd),
                         "k":K,"w_C4":W_C4,"w_C2":wc2,
                         "L4_g3185g":L4G3,"L2_g3185g":L2G3,
                         "L7_g3185g":L7G3,"L7_g4185g":L7G4})
    mp = MODEL_DIR/"runs"/"refine14_manifest.json"
    mp.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(f"Manifest → {mp}")

if __name__ == "__main__": main()
