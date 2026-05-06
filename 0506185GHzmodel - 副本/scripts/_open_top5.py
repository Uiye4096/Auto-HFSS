import math, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from plot_interactive import build_html

RUNS    = Path(__file__).parent.parent / "runs"
F_MAX   = 30.0   # GHz — display and metric cutoff

def parse_s3p(path, fmax=F_MAX):
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
        if f > fmax: continue          # truncate to fmax
        fr.append(f)
        if fmt=="DB":   s11.append(r[1]);  s21.append(r[7]);  s31.append(r[13])
        elif fmt=="MA": s11.append(db(r[1])); s21.append(db(r[7])); s31.append(db(r[13]))
        else:           s11.append(db(math.hypot(r[1],r[2]))); s21.append(db(math.hypot(r[7],r[8]))); s31.append(db(math.hypot(r[13],r[14])))
    return fr, s11, s21, s31

def at(fr, v, f): return v[min(range(len(fr)), key=lambda i: abs(fr[i]-f))]
def crossing(fr, s21, s31):
    for i in range(len(fr)-1):
        d0, d1 = s21[i]-s31[i], s21[i+1]-s31[i+1]
        if d0*d1 <= 0:
            t = d0/(d0-d1) if abs(d0-d1)>1e-9 else 0.5
            return fr[i]+t*(fr[i+1]-fr[i])
    return None

def compute_metrics(fr, s11, s21, s31):
    fc  = crossing(fr, s21, s31)
    pb  = [at(fr, s21, f) for f in [20, 21, 22, 23, 25, 28]]
    pb25 = [at(fr, s21, f) for f in [20, 21, 22, 23, 25]]
    s19 = at(fr, s31, 19.0)
    return {
        "crossing_GHz":          round(fc, 4) if fc else None,
        "S31_at_19GHz_dB":       round(s19, 2),
        "S31_at_20GHz_dB":       round(at(fr, s31, 20.0), 2),
        "S31_at_28GHz_dB":       round(at(fr, s31, 28.0), 2),
        "S31_at_30GHz_dB":       round(at(fr, s31, 30.0), 2),
        "ripple_20_25GHz_dB":    round(max(pb25)-min(pb25), 2),
        "ripple_20_28GHz_dB":    round(max(pb)-min(pb), 2),
        "min_IL_20plus_dB":      round(min(pb25), 2),
        "S11_worst_19_25GHz_dB": round(max(at(fr,s11,f) for f in [19,20,21,22,25]), 2),
        "targets_met": {
            "crossing_ge_18p5GHz":    bool(fc and fc >= 18.5),
            "S31_at_19_le_neg10dB":   s19 <= -10.0,
            "S31_at_20_le_neg10dB":   at(fr, s31, 20.0) <= -10.0,
            "ripple_20_25GHz_le_1dB": (max(pb25)-min(pb25)) <= 1.0,
        }
    }

# All key cases: (uid, run_dir_name, label)
CASES = [
    ("BASE", "000_baseline",  "BASELINE"),
    ("024",  "024_L2g3_078",  "L7g3=0.90 (pre-refine6)"),
    ("037",  "037_L7g3_075",  "L7g3=0.75  FINAL ★"),
    ("047",  "047_L7g3_072",  "L7g3=0.72"),
    ("048",  "048_L7g3_073",  "L7g3=0.73"),
    ("049",  "049_L7g3_074",  "L7g3=0.74"),
    ("038",  "038_L7g3_080",  "L7g3=0.80"),
    ("039",  "039_L7g3_085",  "L7g3=0.85"),
]

HDR = f"{'UID':>4}  {'Label':<30} {'Cross':>7} {'S31@19':>7} {'S31@20':>7} {'S31@28':>7} {'S31@30':>7} {'Rpl25':>6} {'Rpl28':>6} {'IL':>5} {'S11w':>5}"
print(HDR); print("-"*len(HDR))

for uid, dname, label in CASES:
    rd  = RUNS / dname
    s3p = rd / "result.s3p"
    if not s3p.exists():
        print(f"{uid:>4}  {label:<30}  — no s3p"); continue
    fr, s11, s21, s31 = parse_s3p(s3p)
    m   = compute_metrics(fr, s11, s21, s31)
    fc  = m["crossing_GHz"]
    fc_s = f"{fc:.3f}" if fc else "  n/a "
    ok_cross = "✓" if m["targets_met"]["crossing_ge_18p5GHz"] else "✗"
    ok_s31   = "✓" if m["targets_met"]["S31_at_19_le_neg10dB"] else "✗"
    star = " ★" if all(m["targets_met"].values()) else ""
    print(f"{uid:>4}  {label:<30} {fc_s:>7}{ok_cross} {m['S31_at_19GHz_dB']:>6.1f}{ok_s31}"
          f" {m['S31_at_20GHz_dB']:>7.1f} {m['S31_at_28GHz_dB']:>7.1f} {m['S31_at_30GHz_dB']:>7.1f}"
          f" {m['ripple_20_25GHz_dB']:>6.2f} {m['ripple_20_28GHz_dB']:>6.2f}"
          f" {m['min_IL_20plus_dB']:>5.1f} {m['S11_worst_19_25GHz_dB']:>5.1f}{star}")
    hp = rd / "plot_30g.html"
    hp.write_text(build_html(fr, s11, s21, s31, m,
                  f"[{uid}] {label}  cross={fc_s} S31@19={m['S31_at_19GHz_dB']:.1f}dB  (5-30GHz)"),
                  encoding="utf-8")
    subprocess.Popen(["explorer", str(hp)])
    time.sleep(0.5)
