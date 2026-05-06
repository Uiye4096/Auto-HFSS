"""Generate SVG plot for r27_c1y022 best result."""
import math
from pathlib import Path

s3p_path = Path(r"D:\Desktop\HFSS_real\12GHzdiplexer2\derived\refine27\r27_c1y022\sim\r27_c1y022.s3p")

recs, fmt, buf = [], "MA", []
for line in s3p_path.read_text(errors="ignore").splitlines():
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

db = lambda v: 20 * math.log10(v) if v > 0 else -100
fr, s11, s21, s31 = [], [], [], []
for r in recs:
    if len(r) < 19: continue
    f = r[0] / 1e9 if r[0] > 1e7 else r[0]; fr.append(f)
    if fmt == "DB":
        s11.append(r[1]); s21.append(r[7]); s31.append(r[13])
    elif fmt == "MA":
        s11.append(db(r[1])); s21.append(db(r[7])); s31.append(db(r[13]))
    else:
        s11.append(db(math.hypot(r[1], r[2])))
        s21.append(db(math.hypot(r[7], r[8])))
        s31.append(db(math.hypot(r[13], r[14])))

W, H = 920, 560
ML, MR, MT, MB = 72, 24, 32, 56
PW = W - ML - MR
PH = H - MT - MB
fmin, fmax = 0, 40
ymin, ymax = -40, 5

def px(f): return ML + (f - fmin) / (fmax - fmin) * PW
def py(y): return MT + (ymax - y) / (ymax - ymin) * PH

def polyline(fv, sv, color, width=2.5, dash=""):
    pts = " ".join(f"{px(f):.1f},{max(MT-2, min(MT+PH+2, py(s))):.1f}"
                   for f, s in zip(fv, sv) if fmin <= f <= fmax)
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{width}"{da}/>'

svg = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">')
svg.append(f'<rect width="{W}" height="{H}" fill="#12131f" rx="8"/>')

# Grid lines
for y in range(ymin, ymax + 1, 5):
    yp = py(y)
    col = "#ccddee" if y == 0 else "#2a3a4a"
    ow  = 0.8 if y != 0 else 1.2
    svg.append(f'<line x1="{ML}" y1="{yp:.1f}" x2="{ML+PW}" y2="{yp:.1f}" stroke="{col}" stroke-width="{ow}" opacity="0.55"/>')
    svg.append(f'<text x="{ML-8}" y="{yp+4:.1f}" text-anchor="end" fill="#8899aa" font-size="11" font-family="monospace">{y}</text>')

for f in range(0, 41, 5):
    xp = px(f)
    svg.append(f'<line x1="{xp:.1f}" y1="{MT}" x2="{xp:.1f}" y2="{MT+PH}" stroke="#2a3a4a" stroke-width="0.8" opacity="0.7"/>')
    svg.append(f'<text x="{xp:.1f}" y="{MT+PH+20}" text-anchor="middle" fill="#8899aa" font-size="11" font-family="monospace">{f}</text>')

# Shaded passband region 18.5–40 GHz
svg.append(f'<rect x="{px(18.5):.1f}" y="{MT}" width="{px(40)-px(18.5):.1f}" height="{PH}" fill="#44aaff" opacity="0.05"/>')

# Reference lines
svg.append(f'<line x1="{px(18.5):.1f}" y1="{MT}" x2="{px(18.5):.1f}" y2="{MT+PH}" stroke="#ffcc00" stroke-width="1.5" stroke-dasharray="7,4" opacity="0.75"/>')
svg.append(f'<text x="{px(18.5)+4:.1f}" y="{MT+14}" fill="#ffcc00" font-size="10" font-family="monospace">18.5 GHz</text>')

svg.append(f'<line x1="{ML}" y1="{py(-10):.1f}" x2="{ML+PW}" y2="{py(-10):.1f}" stroke="#ff6644" stroke-width="1.4" stroke-dasharray="5,3" opacity="0.65"/>')
svg.append(f'<text x="{ML+5}" y="{py(-10)-5:.1f}" fill="#ff6644" font-size="10" font-family="monospace">−10 dB target</text>')

svg.append(f'<line x1="{ML}" y1="{py(-1):.1f}" x2="{ML+PW}" y2="{py(-1):.1f}" stroke="#66dd88" stroke-width="1.2" stroke-dasharray="4,3" opacity="0.5"/>')
svg.append(f'<text x="{ML+5}" y="{py(-1)-4:.1f}" fill="#66dd88" font-size="10" font-family="monospace">−1 dB</text>')

# Traces
svg.append(polyline(fr, s21, "#4db8ff", 2.8))
svg.append(polyline(fr, s31, "#ff4477", 2.8))
svg.append(polyline(fr, s11, "#55ee99", 1.8, "5,3"))

# Crossing marker
cross_f = 18.552
svg.append(f'<circle cx="{px(cross_f):.1f}" cy="{py(-10.8):.1f}" r="5" fill="none" stroke="#ffdd44" stroke-width="1.5"/>')
svg.append(f'<text x="{px(cross_f)+8:.1f}" y="{py(-10.8)+4:.1f}" fill="#ffdd44" font-size="10" font-family="monospace">× 18.552 GHz, −10.8 dB</text>')

# Border
svg.append(f'<rect x="{ML}" y="{MT}" width="{PW}" height="{PH}" fill="none" stroke="#445566" stroke-width="1.2"/>')

# Legend box
lx, ly0 = ML + 14, MT + 16
svg.append(f'<rect x="{lx-6}" y="{ly0-14}" width="160" height="70" rx="4" fill="#1e2535" opacity="0.85"/>')
for lbl, col, dash in [("S21 — HPF passband", "#4db8ff", ""), ("S31 — LPF arm", "#ff4477", ""), ("S11 — return loss", "#55ee99", "5,2")]:
    da = f' stroke-dasharray="{dash}"' if dash else ""
    svg.append(f'<line x1="{lx}" y1="{ly0}" x2="{lx+24}" y2="{ly0}" stroke="{col}" stroke-width="2"{da}/>')
    svg.append(f'<text x="{lx+30}" y="{ly0+4}" fill="{col}" font-size="11" font-family="sans-serif">{lbl}</text>')
    ly0 += 22

# Metrics annotation (top-right)
ann = [
    ("r27_c1y022  ·  Final Best", "#ffee66", 13, True),
    ("Cross  = 18.552 GHz  ✓", "#aaddff", 11, False),
    ("S31@19 = −10.8 dB   ✓", "#aaddff", 11, False),
    ("S31@20 = −15.8 dB   ✓", "#aaddff", 11, False),
    ("Ripple(20–25 GHz) = 0.6 dB ✓", "#aaddff", 11, False),
    ("IL(20+ GHz) = −3.1 dB", "#aaddff", 11, False),
]
ax = ML + PW - 8
ay = MT + 16
bh = len(ann) * 16 + 10
svg.append(f'<rect x="{ax - 222}" y="{ay-14}" width="228" height="{bh}" rx="4" fill="#1e2535" opacity="0.85"/>')
for txt, col, sz, bold in ann:
    fw = "bold" if bold else "normal"
    svg.append(f'<text x="{ax}" y="{ay}" text-anchor="end" fill="{col}" font-size="{sz}" font-family="monospace" font-weight="{fw}">{txt}</text>')
    ay += 16

# Axis labels
svg.append(f'<text x="{ML+PW//2}" y="{H-8}" text-anchor="middle" fill="#8899aa" font-size="12" font-family="sans-serif">Frequency (GHz)</text>')
svg.append(f'<text x="16" y="{MT+PH//2}" text-anchor="middle" fill="#8899aa" font-size="12" font-family="sans-serif" transform="rotate(-90,16,{MT+PH//2})">S-Parameters (dB)</text>')
svg.append(f'<text x="{W//2}" y="{MT-10}" text-anchor="middle" fill="#ddeeff" font-size="14" font-family="sans-serif" font-weight="bold">Diplexer HPF Refinement — Best Configuration (r27_c1y022)</text>')

svg.append("</svg>")

out = Path(r"D:\Desktop\HFSS_real\12GHzdiplexer2\derived\r27_c1y022_final.svg")
out.write_text("\n".join(svg), encoding="utf-8")
print(f"Saved: {out}")
