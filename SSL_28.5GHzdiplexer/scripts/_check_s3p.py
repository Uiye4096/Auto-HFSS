"""Print S21/S31 values at key frequencies from case 018 to diagnose crossing."""
import math
from pathlib import Path

def parse_s3p(path, fmax=60.0):
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
        if fmt == "DB":   s11.append(r[1]);  s21.append(r[7]);  s31.append(r[13])
        elif fmt == "MA": s11.append(db(r[1])); s21.append(db(r[7])); s31.append(db(r[13]))
        else:             s11.append(db(math.hypot(r[1],r[2]))); s21.append(db(math.hypot(r[7],r[8]))); s31.append(db(math.hypot(r[13],r[14])))
    return fr, s11, s21, s31

s3p = Path(r"D:\Desktop\HFSS_real\SSL_28.5GHzdiplexer\runs\018_L2g3_051\result.s3p")
fr, s11, s21, s31 = parse_s3p(s3p)

check_freqs = [10, 15, 18.5, 20, 21, 22, 24, 26, 28.5, 29, 30, 32, 35, 38, 40, 45, 50]
print(f"{'f GHz':>7}  {'S11':>7}  {'S21':>7}  {'S31':>7}  {'S21-S31':>8}")
print("-"*48)
for fc in check_freqs:
    idx = min(range(len(fr)), key=lambda i: abs(fr[i]-fc))
    f = fr[idx]
    print(f"{f:>7.2f}  {s11[idx]:>7.2f}  {s21[idx]:>7.2f}  {s31[idx]:>7.2f}  {s21[idx]-s31[idx]:>8.2f}")

# Find actual crossing(s)
print("\nAll S21=S31 crossings:")
for i in range(len(fr)-1):
    d0, d1 = s21[i]-s31[i], s21[i+1]-s31[i+1]
    if d0*d1 <= 0:
        t = d0/(d0-d1) if abs(d0-d1) > 1e-9 else 0.5
        fc2 = fr[i]+t*(fr[i+1]-fr[i])
        lv = s21[i]+t*(s21[i+1]-s21[i])
        print(f"  {fc2:.4f} GHz  level={lv:.2f} dB")
