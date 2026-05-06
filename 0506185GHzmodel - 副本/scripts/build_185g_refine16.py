"""
build_185g_refine16.py — Round 16: L2_g3 sweep on 102 base (L4_g3=0.75).

102 best: L4g3=0.75, L2g3=0.78, crossing=18.638✓, S11w=-9.7 dB (diff 0.3 from -10)
111 best: L4g3=0.85, L2g3=0.82, S11w=-9.7 but crossing=18.435✗

102 has 0.14 GHz crossing margin. Combining L4g3=0.75 + L2g3=0.80~0.84
may push S11w below -10 while keeping crossing >= 18.5.

Sweep L2_g3 = [0.78, 0.79, 0.80, 0.81, 0.82, 0.83, 0.84]  on 102 base
→ UIDs 114-120
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

K=0.96; W_C4=1.15; W_C2=1.05; L4G3=0.75; L7G3=0.83; L7G4=0.50

LPF_BASE = {"l_L5185g":0.7248,"l_C4185g":0.46508,"l_L3185g":0.9362,"l_C2185g":0.52548,"l_L1185g":0.6946}
L2G3_VALS = [0.78, 0.79, 0.80, 0.81, 0.82, 0.83, 0.84]

def build_case(uid, l2g3, dry_run=False):
    name = f"{uid}_L2g3_{int(round(l2g3*100)):03d}_L4g3075"
    rd   = OUT_DIR / name; rd.mkdir(parents=True, exist_ok=True)
    upd  = {"w_C4185g":f"{W_C4}mm","w_C2185g":f"{W_C2}mm",
            "L4_g3185g":f"{L4G3}mm","L2_g3185g":f"{l2g3}mm",
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
    print(f"Round 16: L2_g3 sweep on 102 base (L4_g3=0.75, L7_g3=0.83, L7_g4=0.50)")
    print(f"  102 ref: S11w=-9.7 dB, crossing=18.638 GHz (+0.14 margin)")
    print(f"  L2_g3 = {L2G3_VALS}\n")
    uids = next_uid(count=len(L2G3_VALS)) if not dry else [f"DRY{i:03d}" for i in range(len(L2G3_VALS))]
    manifest = []
    for l2, uid in zip(L2G3_VALS, uids):
        rd, name = build_case(uid, l2, dry)
        manifest.append({"uid":uid,"name":name,"run_dir":str(rd),
                         "L4_g3185g":L4G3,"L2_g3185g":l2,
                         "L7_g3185g":L7G3,"L7_g4185g":L7G4,"w_C2":W_C2})
    mp = MODEL_DIR/"runs"/"refine16_manifest.json"
    mp.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(f"Manifest → {mp}")

if __name__ == "__main__": main()
