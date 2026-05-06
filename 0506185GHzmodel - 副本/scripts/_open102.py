import math, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from plot_interactive import build_html, compute_metrics

def parse_s3p(path, fmax=30.0):
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
        if f > fmax: continue
        fr.append(f)
        if fmt=="DB":   s11.append(r[1]);  s21.append(r[7]);  s31.append(r[13])
        elif fmt=="MA": s11.append(db(r[1])); s21.append(db(r[7])); s31.append(db(r[13]))
        else:           s11.append(db(math.hypot(r[1],r[2]))); s21.append(db(math.hypot(r[7],r[8]))); s31.append(db(math.hypot(r[13],r[14])))
    return fr, s11, s21, s31

RUNS = Path(__file__).parent.parent / "runs"
uid, dname = "102", "102_L4g3_075"
s3p = RUNS / dname / "result.s3p"
fr, s11, s21, s31 = parse_s3p(s3p)
m = compute_metrics(fr, s11, s21, s31)
stop = m.get("S31_worst_stop_dB", m["S31_at_19GHz_dB"])
s11w = m["S11_worst_19_25GHz_dB"]
print(f"[{uid}]  cross={m['crossing_GHz']:.3f}  S31@19={m['S31_at_19GHz_dB']:.1f}  S31@20={m['S31_at_20GHz_dB']:.1f}  S31_stop={stop:.1f}  S11w={s11w:.1f}  rpl={m['ripple_20_25GHz_dB']:.2f}")
print(f"       IL={m['min_IL_20plus_dB']:.1f}")
title = f"[{uid}] L4g3=0.75 L2g3=0.78 L7g3=0.83 L7g4=0.50  S11w={s11w:.1f}dB  cross={m['crossing_GHz']:.3f}GHz"
hp = RUNS / dname / "plot_30g.html"
hp.write_text(build_html(fr, s11, s21, s31, m, title), encoding="utf-8")
subprocess.Popen(["explorer", str(hp)])
