import math, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from plot_interactive import build_html, compute_metrics

def parse_s3p(path):
    recs, fmt, buf = [], "MA", []
    for line in Path(path).read_text(errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith("!"): continue
        if s.startswith("#"):
            fmt = "DB" if "DB" in s.upper() else ("RI" if "RI" in s.upper() else "MA")
            continue
        if line[0] in (" ", "\t"): buf.extend(float(x) for x in s.split())
        else:
            if buf: recs.append(buf)
            buf = [float(x) for x in s.split()]
    if buf: recs.append(buf)
    db = lambda v: 20*math.log10(v) if v > 0 else -100.0
    fr, s11, s21, s31 = [], [], [], []
    for r in recs:
        if len(r) < 19: continue
        f = r[0]/1e9 if r[0] > 1e7 else r[0]
        if f > 30: continue
        fr.append(f)
        s11.append(r[1] if fmt=="DB" else (db(r[1]) if fmt=="MA" else db(math.hypot(r[1],r[2]))))
        s21.append(r[7] if fmt=="DB" else (db(r[7]) if fmt=="MA" else db(math.hypot(r[7],r[8]))))
        s31.append(r[13] if fmt=="DB" else (db(r[13]) if fmt=="MA" else db(math.hypot(r[13],r[14]))))
    return fr, s11, s21, s31

RUNS = Path(__file__).parent.parent / "runs"
CASES = [
    ("087", "087_L7g3_083_g4052",   "No taper (ref)"),
    ("001", "001_taper_baseline",    "Taper default cx=0.2 cy=-0.2 w=0.2 h=0.1"),
]

print(f"\n{'UID':>4}  {'cross':>7}  {'S31@19':>7}  {'S31@20':>7}  {'rpl':>5}  {'S11w':>6}  label")
print("-"*70)
for uid, dname, label in CASES:
    s3p = RUNS / dname / "result.s3p"
    if not s3p.exists(): print(f"  {uid}: no s3p"); continue
    fr, s11, s21, s31 = parse_s3p(s3p)
    m = compute_metrics(fr, s11, s21, s31)
    fc = m["crossing_GHz"]; s11w = m["S11_worst_19_25GHz_dB"]
    print(f"{uid:>4}  {fc:>7.3f}  {m['S31_at_19GHz_dB']:>7.1f}  {m['S31_at_20GHz_dB']:>7.1f}  {m['ripple_20_25GHz_dB']:>5.2f}  {s11w:>6.1f}  {label}")
    hp = RUNS / dname / "plot_30g.html"
    hp.write_text(build_html(fr, s11, s21, s31, m, f"[{uid}] {label}  S11w={s11w:.1f}dB"), encoding="utf-8")
    subprocess.Popen(["explorer", str(hp)]); time.sleep(0.6)
