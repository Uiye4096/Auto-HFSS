"""
plot_s3p.py  --  Parse a 3-port Touchstone file and write an SVG plot.

Usage:
    python plot_s3p.py <path_to.s3p> [--out <output.svg>] [--open]

If --out is omitted the SVG is written next to the .s3p file with the same stem.
If --open is given the SVG is opened in the default browser after writing.
"""

import argparse
import math
import os
import sys
import subprocess
from pathlib import Path


# ---------------------------------------------------------------------------
# Touchstone parser
# ---------------------------------------------------------------------------

def parse_s3p(path: Path):
    """Return (freqs_GHz, s21_dB, s31_dB) lists."""
    fmt = "MA"
    records = []
    buf = []

    for line in path.read_text(errors="ignore").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("!"):
            continue
        if stripped.startswith("#"):
            up = stripped.upper()
            if "DB" in up:
                fmt = "DB"
            elif "RI" in up:
                fmt = "RI"
            else:
                fmt = "MA"
            continue
        # detect continuation by leading whitespace
        if line[0] in (" ", "\t"):
            buf.extend(float(x) for x in stripped.split())
        else:
            if buf:
                records.append(buf)
            buf = [float(x) for x in stripped.split()]

    if buf:
        records.append(buf)

    freqs, s21_db, s31_db = [], [], []
    for r in records:
        if len(r) < 19:
            continue
        freq_ghz = r[0] / 1e9 if r[0] > 1e7 else r[0]
        freqs.append(freq_ghz)
        if fmt == "DB":
            s21_db.append(r[7])
            s31_db.append(r[13])
        elif fmt == "MA":
            s21_db.append(20 * math.log10(r[7])  if r[7]  > 0 else -100.0)
            s31_db.append(20 * math.log10(r[13]) if r[13] > 0 else -100.0)
        else:  # RI
            mag21 = math.hypot(r[7],  r[8])
            mag31 = math.hypot(r[13], r[14])
            s21_db.append(20 * math.log10(mag21) if mag21 > 0 else -100.0)
            s31_db.append(20 * math.log10(mag31) if mag31 > 0 else -100.0)

    return freqs, s21_db, s31_db


# ---------------------------------------------------------------------------
# Key metrics
# ---------------------------------------------------------------------------

def metrics(freqs, s21_db, s31_db):
    s21_first = next((f for f, v in zip(freqs, s21_db) if f > 5 and v >= -3), None)
    s31_pts   = [f for f, v in zip(freqs, s31_db) if v >= -3]
    s31_right = max(s31_pts) if s31_pts else None
    cross     = [(f, v21, v31) for f, v21, v31 in zip(freqs, s21_db, s31_db)
                 if abs(v21 - v31) < 0.6]
    crossing  = cross[len(cross) // 2] if cross else None
    return s21_first, s31_right, crossing


# ---------------------------------------------------------------------------
# SVG builder
# ---------------------------------------------------------------------------

def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def build_svg(freqs, s21_db, s31_db, title="S-parameter Plot"):
    W, H   = 900, 520
    PAD_L  = 72
    PAD_R  = 30
    PAD_T  = 50
    PAD_B  = 60
    PW     = W - PAD_L - PAD_R
    PH     = H - PAD_T - PAD_B

    db_min, db_max = -70.0, 5.0
    f_min  = freqs[0]  if freqs else 0
    f_max  = freqs[-1] if freqs else 40

    def fx(f):
        return PAD_L + PW * (f - f_min) / (f_max - f_min)

    def fy(db):
        db = _clamp(db, db_min, db_max)
        return PAD_T + PH * (1 - (db - db_min) / (db_max - db_min))

    def polyline(vals_f, vals_db, color, label, dash=""):
        pts = " ".join(f"{fx(f):.1f},{fy(v):.1f}" for f, v in zip(vals_f, vals_db))
        da  = f'stroke-dasharray="{dash}"' if dash else ""
        return (f'<polyline points="{pts}" fill="none" stroke="{color}" '
                f'stroke-width="2" {da}/>\n'
                f'<!-- {label} -->\n')

    s21_first, s31_right, crossing = metrics(freqs, s21_db, s31_db)

    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
                 f'style="font-family:sans-serif;background:#1e1e2e;">\n')

    # background rect
    lines.append(f'<rect x="{PAD_L}" y="{PAD_T}" width="{PW}" height="{PH}" '
                 f'fill="#13131f" stroke="#444" stroke-width="1"/>\n')

    # grid lines & Y labels
    for db in range(int(db_min), int(db_max) + 1, 10):
        y = fy(db)
        lines.append(f'<line x1="{PAD_L}" y1="{y:.1f}" x2="{PAD_L+PW}" y2="{y:.1f}" '
                     f'stroke="#333" stroke-width="1"/>\n')
        lines.append(f'<text x="{PAD_L-6}" y="{y+4:.1f}" text-anchor="end" '
                     f'font-size="11" fill="#aaa">{db}</text>\n')

    # -3 dB reference line (highlighted)
    y3 = fy(-3)
    lines.append(f'<line x1="{PAD_L}" y1="{y3:.1f}" x2="{PAD_L+PW}" y2="{y3:.1f}" '
                 f'stroke="#888" stroke-width="1" stroke-dasharray="6,4"/>\n')
    lines.append(f'<text x="{PAD_L+PW+4}" y="{y3+4:.1f}" font-size="10" fill="#888">-3 dB</text>\n')

    # X grid + labels (every 5 GHz)
    step = 5.0
    f_tick = math.ceil(f_min / step) * step
    while f_tick <= f_max + 0.01:
        x = fx(f_tick)
        lines.append(f'<line x1="{x:.1f}" y1="{PAD_T}" x2="{x:.1f}" y2="{PAD_T+PH}" '
                     f'stroke="#333" stroke-width="1"/>\n')
        lines.append(f'<text x="{x:.1f}" y="{PAD_T+PH+16}" text-anchor="middle" '
                     f'font-size="11" fill="#aaa">{f_tick:.0f}</text>\n')
        f_tick += step

    # axis labels
    lines.append(f'<text x="{PAD_L + PW//2}" y="{H-8}" text-anchor="middle" '
                 f'font-size="12" fill="#ccc">Frequency (GHz)</text>\n')
    lines.append(f'<text x="14" y="{PAD_T + PH//2}" text-anchor="middle" '
                 f'font-size="12" fill="#ccc" '
                 f'transform="rotate(-90,14,{PAD_T + PH//2})">S (dB)</text>\n')

    # title
    lines.append(f'<text x="{W//2}" y="30" text-anchor="middle" '
                 f'font-size="14" font-weight="bold" fill="#e0e0ff">{title}</text>\n')

    # S21 and S31 curves
    lines.append(polyline(freqs, s21_db, "#4fc3f7", "S21"))
    lines.append(polyline(freqs, s31_db, "#f48fb1", "S31"))

    # -3 dB markers
    if s21_first is not None:
        x = fx(s21_first); y = fy(-3)
        lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#4fc3f7" stroke="white" stroke-width="1"/>\n')
        lines.append(f'<text x="{x:.1f}" y="{y-10:.1f}" text-anchor="middle" '
                     f'font-size="11" fill="#4fc3f7">S21↑ {s21_first:.2f} GHz</text>\n')

    if s31_right is not None:
        x = fx(s31_right); y = fy(-3)
        lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#f48fb1" stroke="white" stroke-width="1"/>\n')
        lines.append(f'<text x="{x:.1f}" y="{y+18:.1f}" text-anchor="middle" '
                     f'font-size="11" fill="#f48fb1">S31→ {s31_right:.2f} GHz</text>\n')

    if crossing:
        fc, v21c, v31c = crossing
        x = fx(fc); y = fy((v21c + v31c) / 2)
        lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#ffcc02" stroke="white" stroke-width="1"/>\n')
        lines.append(f'<text x="{x:.1f}" y="{y-10:.1f}" text-anchor="middle" '
                     f'font-size="10" fill="#ffcc02">✕ {fc:.2f} GHz @ {v21c:.1f} dB</text>\n')

    # target line at 18.5 GHz
    if f_min <= 18.5 <= f_max:
        xt = fx(18.5)
        lines.append(f'<line x1="{xt:.1f}" y1="{PAD_T}" x2="{xt:.1f}" y2="{PAD_T+PH}" '
                     f'stroke="#66ff99" stroke-width="1" stroke-dasharray="4,4" opacity="0.7"/>\n')
        lines.append(f'<text x="{xt+3:.1f}" y="{PAD_T+14}" font-size="10" fill="#66ff99">target 18.5 GHz</text>\n')

    # legend
    lx, ly = PAD_L + 14, PAD_T + 16
    lines.append(f'<rect x="{lx-6}" y="{ly-14}" width="170" height="44" '
                 f'rx="4" fill="#1e1e2e" stroke="#555" stroke-width="1" opacity="0.85"/>\n')
    lines.append(f'<line x1="{lx}" y1="{ly}" x2="{lx+22}" y2="{ly}" '
                 f'stroke="#4fc3f7" stroke-width="2"/>\n')
    lines.append(f'<text x="{lx+26}" y="{ly+4}" font-size="12" fill="#4fc3f7">S21 (HPF channel)</text>\n')
    lines.append(f'<line x1="{lx}" y1="{ly+20}" x2="{lx+22}" y2="{ly+20}" '
                 f'stroke="#f48fb1" stroke-width="2"/>\n')
    lines.append(f'<text x="{lx+26}" y="{ly+24}" font-size="12" fill="#f48fb1">S31 (LPF channel)</text>\n')

    lines.append('</svg>\n')
    return "".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Plot S21/S31 from a .s3p file as SVG.")
    parser.add_argument("s3p", help="Path to the Touchstone .s3p file")
    parser.add_argument("--out",  default=None, help="Output SVG path (default: same dir as .s3p)")
    parser.add_argument("--open", action="store_true", help="Open the SVG in the default browser after writing")
    args = parser.parse_args()

    s3p_path = Path(args.s3p).resolve()
    out_path = Path(args.out).resolve() if args.out else s3p_path.with_suffix(".svg")

    freqs, s21_db, s31_db = parse_s3p(s3p_path)
    if not freqs:
        sys.exit(f"ERROR: no data parsed from {s3p_path}")

    s21_first, s31_right, crossing = metrics(freqs, s21_db, s31_db)
    print(f"S21 first -3 dB  : {s21_first} GHz")
    print(f"S31 right -3 dB  : {s31_right} GHz")
    if crossing:
        fc, v21c, v31c = crossing
        print(f"S21/S31 crossing : {fc:.3f} GHz  S21={v21c:.2f} dB  S31={v31c:.2f} dB")

    title = s3p_path.stem.replace("_", " ")
    svg = build_svg(freqs, s21_db, s31_db, title=title)
    out_path.write_text(svg, encoding="utf-8")
    print(f"SVG written → {out_path}")

    if args.open:
        if sys.platform.startswith("win"):
            os.startfile(str(out_path))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(out_path)])
        else:
            subprocess.Popen(["xdg-open", str(out_path)])


if __name__ == "__main__":
    main()
