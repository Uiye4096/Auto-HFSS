"""
build_185g_refine13.py — Round 13: L7_g4185g fine sweep around 0.52 peak.

Base: 087 (k=0.96, wC4=1.15, wC2=1.05, L2g3=0.78, L4g3=0.85, L7g3=0.83, L7g4=0.52)
S11w peak at L7_g4=0.52 (-9.3 dB). Fine sweep 0.48-0.56 step 0.02 to find true peak.
Also try 0.50, 0.54 to fill gaps.
→ L7_g4 = [0.48, 0.50, 0.52, 0.54, 0.56]   (0.52 is 087, included for continuity)
→ UIDs 089-093
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

K=0.96; W_C4=1.15; W_C2=1.05; L2G3=0.78; L4G3=0.85; L7G3=0.83

LPF_BASE = {"l_L5185g":0.7248,"l_C4185g":0.46508,"l_L3185g":0.9362,"l_C2185g":0.52548,"l_L1185g":0.6946}
L7G4_VALS = [0.48, 0.50, 0.52, 0.54, 0.56]

def build_case(uid, g4, dry_run=False):
    name = f"{uid}_g4f_{int(round(g4*100)):03d}"
    rd   = OUT_DIR / name; rd.mkdir(parents=True, exist_ok=True)
    upd  = {"w_C4185g":f"{W_C4}mm","w_C2185g":f"{W_C2}mm",
            "L4_g3185g":f"{L4G3}mm","L2_g3185g":f"{L2G3}mm",
            "L7_g3185g":f"{L7G3}mm","L7_g4185g":f"{g4}mm"}
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
    print(f"Round 13: L7_g4 fine sweep on 087 base (L7_g3=0.83)")
    print(f"  L7_g4 = {L7G4_VALS}  (0.52 is 087 ref)\n")
    uids = next_uid(count=len(L7G4_VALS)) if not dry else [f"DRY{i:03d}" for i in range(len(L7G4_VALS))]
    manifest = []
    for g4, uid in zip(L7G4_VALS, uids):
        rd, name = build_case(uid, g4, dry)
        manifest.append({"uid":uid,"name":name,"run_dir":str(rd),
                         "k":K,"w_C4":W_C4,"w_C2":W_C2,
                         "L4_g3185g":L4G3,"L2_g3185g":L2G3,
                         "L7_g3185g":L7G3,"L7_g4185g":g4})
    mp = MODEL_DIR/"runs"/"refine13_manifest.json"
    mp.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(f"\nManifest → {mp}")

if __name__ == "__main__": main()
