"""
diplexer.py — Unified HFSS diplexer simulation entry point.

Usage (single run):
  python diplexer.py --wC 1.45 --L4 0.85 --L2 0.75 --k 0.90 --idx 0.60 --c1y 0.22

Multiple parallel runs (PowerShell):
  1.30, 1.40, 1.45 | ForEach-Object -Parallel {
      python D:/Desktop/HFSS_real/diplexer.py --wC $_ --L4 0.85 --k 0.90
  }

Each run creates:
  <project>/runs/run_wC145_L485_L275_k090_<timestamp>/
      project.aedt   — parameterised HFSS project
      result.s3p     — exported S-parameters
      plot.svg       — S-parameter chart
      params.json    — parameters + metrics
      run.log        — HFSS log
"""
import argparse
import json
import logging
import math
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ── Paths (adjust if your install differs) ────────────────────────────────────
HFSS_ROOT  = Path(r"D:\Desktop\HFSS_real")
IPY        = Path(r"E:\HFFS\HFSS_2021\Program Files\AnsysEM\AnsysEM21.2\Win64\common\IronPython\ipy64.exe")
INSPECT    = HFSS_ROOT / "tools" / "aedt_inspect.py"
HFSS_RUNNER = HFSS_ROOT / "12GHzdiplexer" / "scripts" / "run_hfss_case.py"

# ── LPF element base lengths (at k = 1.0, uniform) ───────────────────────────
LPF_BASE = {
    "l_L512g": 0.770,
    "l_C412g": 0.616,
    "l_L312g": 0.912,
    "l_C212g": 0.506,
    "l_L112g": 0.516,
}
LPF_SUM_BASE = sum(LPF_BASE.values())   # 3.320 mm

# Geometry alignment formulas (kept as HFSS expressions)
ALIGNMENT = {
    "compensation_y":
        "L2_g212g + cover_HPF_out12g + l_line212g + 1.426mm - l_sub12g",
    "compensation_y_2":
        "l_line312g + l_L512g + l_C412g + l_L312g + l_C212g + "
        "l_L112g + l_line412g - l_sub_LPF12g",
}


# ─────────────────────────────────────────────────────────────────────────────
# Argument parsing
# ─────────────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="Run a single HFSS diplexer HPF simulation.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--project", default="12GHzdiplexer2",
                   help="Project folder name under HFSS_real, or full path")
    # HPF parameters
    p.add_argument("--wC",  type=float, default=1.45,
                   help="w_C412g = w_C212g  [mm]  LPF cap width")
    p.add_argument("--L4",  type=float, default=0.85,
                   help="L4_g312g  [mm]  HPF stub L4 gap")
    p.add_argument("--L2",  type=float, default=0.75,
                   help="L2_g312g  [mm]  HPF stub L2 gap")
    p.add_argument("--idx", type=float, default=0.60,
                   help="index1  (dimensionless HPF coupling factor)")
    p.add_argument("--c1y", type=float, default=0.22,
                   help="w_C1_y  [mm]  HPF input cap y-dim")
    # LPF scaling
    p.add_argument("--k",   type=float, default=0.90,
                   help="LPF uniform scaling factor (0 < k ≤ 1)")
    # Fixed substrate (rarely changed)
    p.add_argument("--wSub",  type=float, default=1.70,
                   help="w_sub12G  [mm]  substrate width (fixed)")
    p.add_argument("--wLine", type=float, default=0.395,
                   help="w_line12g  [mm]  main line width (fixed)")
    # Misc
    p.add_argument("--dry-run", action="store_true",
                   help="Build project file but skip HFSS simulation")
    p.add_argument("--as-is", action="store_true",
                   help="Simulate the base project without any parameter changes")
    p.add_argument("--open-svg", action="store_true",
                   help="Open SVG in default browser after plotting")
    return p.parse_args()


# ─────────────────────────────────────────────────────────────────────────────
# Parameter building
# ─────────────────────────────────────────────────────────────────────────────

def build_updates(args):
    k = args.k
    lpf = {name: f"{val * k:.6f}mm" for name, val in LPF_BASE.items()}
    lpf["l_sub_LPF12g"] = f"{1.04 + LPF_SUM_BASE * k:.6f}mm"
    updates = {
        "w_sub12G":  f"{args.wSub:.6f}mm",
        "w_line12g": f"{args.wLine:.6f}mm",
        "w_C412g":   f"{args.wC:.6f}mm",
        "w_C212g":   f"{args.wC:.6f}mm",
        "L4_g312g":  f"{args.L4:.6f}mm",
        "L2_g312g":  f"{args.L2:.6f}mm",
        "index1":    f"{args.idx:.6f}m",
        "w_C1_y":    f"{args.c1y:.6f}mm",
        **lpf,
        **ALIGNMENT,
    }
    return updates


def run_dir_name(args):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if getattr(args, "as_is", False):
        return f"run_baseline_{ts}"
    return (
        f"run_wC{int(round(args.wC * 100)):03d}"
        f"_L4{int(round(args.L4 * 100)):03d}"
        f"_L2{int(round(args.L2 * 100)):03d}"
        f"_k{int(round(args.k * 100)):03d}"
        f"_idx{int(round(args.idx * 100)):03d}"
        f"_c1y{int(round(args.c1y * 100)):03d}"
        f"_{ts}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# S3P parsing
# ─────────────────────────────────────────────────────────────────────────────

def parse_s3p(path):
    recs, fmt, buf = [], "MA", []
    for line in Path(path).read_text(errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith("!"): continue
        if s.startswith("#"):
            fmt = "DB" if "DB" in s.upper() else ("RI" if "RI" in s.upper() else "MA")
            continue
        if line[0] in (" ", "\t"):
            buf.extend(float(x) for x in s.split())
        else:
            if buf: recs.append(buf)
            buf = [float(x) for x in s.split()]
    if buf: recs.append(buf)

    db = lambda v: 20 * math.log10(v) if v > 0 else -100.0
    fr, s11, s21, s31 = [], [], [], []
    for r in recs:
        if len(r) < 19: continue
        f = r[0] / 1e9 if r[0] > 1e7 else r[0]
        fr.append(f)
        if fmt == "DB":
            s11.append(r[1]);                            s21.append(r[7]);  s31.append(r[13])
        elif fmt == "MA":
            s11.append(db(r[1]));                        s21.append(db(r[7]));  s31.append(db(r[13]))
        else:
            s11.append(db(math.hypot(r[1],  r[2])))
            s21.append(db(math.hypot(r[7],  r[8])))
            s31.append(db(math.hypot(r[13], r[14])))
    return fr, s11, s21, s31


def at(fr, vals, f):
    return vals[min(range(len(fr)), key=lambda i: abs(fr[i] - f))]


def crossing_freq(fr, s21, s31):
    for i in range(len(fr) - 1):
        d0 = s21[i]  - s31[i]
        d1 = s21[i+1] - s31[i+1]
        if d0 * d1 <= 0:
            t = d0 / (d0 - d1) if abs(d0 - d1) > 1e-9 else 0.5
            return fr[i] + t * (fr[i+1] - fr[i])
    return None


def compute_metrics(fr, s11, s21, s31):
    fc    = crossing_freq(fr, s21, s31)
    s19   = at(fr, s31, 19.0)
    s20   = at(fr, s31, 20.0)
    pb    = [at(fr, s21, f) for f in [20, 21, 22, 23, 25]]
    rip25 = max(pb) - min(pb)
    il20  = min(pb)
    s11w  = max(at(fr, s11, f) for f in [19, 20, 21, 22, 25])
    return {
        "crossing_GHz":          round(fc, 4) if fc else None,
        "S31_at_19GHz_dB":       round(s19,  2),
        "S31_at_20GHz_dB":       round(s20,  2),
        "ripple_20_25GHz_dB":    round(rip25, 2),
        "min_IL_20plus_dB":      round(il20,  2),
        "S11_worst_19_25GHz_dB": round(s11w,  2),
        "targets_met": {
            "crossing_ge_18p5GHz":     bool(fc and fc >= 18.5),
            "S31_at_19_le_neg10dB":    s19 <= -10.0,
            "S31_at_20_le_neg10dB":    s20 <= -10.0,
            "ripple_20_25GHz_le_1dB":  rip25 <= 1.0,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# SVG plot
# ─────────────────────────────────────────────────────────────────────────────

def make_svg(fr, s11, s21, s31, metrics, title):
    W, H = 920, 560
    ML, MR, MT, MB = 72, 24, 32, 56
    PW = W - ML - MR
    PH = H - MT - MB
    fmin, fmax, ymin, ymax = 0, 40, -40, 5

    def px(f): return ML + (f - fmin) / (fmax - fmin) * PW
    def py(y): return MT + (ymax - y) / (ymax - ymin) * PH
    def polyline(fv, sv, color, width=2.5, dash=""):
        pts = " ".join(
            f"{px(f):.1f},{max(MT-2, min(MT+PH+2, py(s))):.1f}"
            for f, s in zip(fv, sv) if fmin <= f <= fmax
        )
        da = f' stroke-dasharray="{dash}"' if dash else ""
        return f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{width}"{da}/>'

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">')
    svg.append(f'<rect width="{W}" height="{H}" fill="#12131f" rx="8"/>')

    for y in range(ymin, ymax + 1, 5):
        yp = py(y)
        col = "#ccddee" if y == 0 else "#2a3a4a"; ow = 1.2 if y == 0 else 0.8
        svg.append(f'<line x1="{ML}" y1="{yp:.1f}" x2="{ML+PW}" y2="{yp:.1f}" stroke="{col}" stroke-width="{ow}" opacity="0.55"/>')
        svg.append(f'<text x="{ML-8}" y="{yp+4:.1f}" text-anchor="end" fill="#8899aa" font-size="11" font-family="monospace">{y}</text>')

    for f in range(0, 41, 5):
        xp = px(f)
        svg.append(f'<line x1="{xp:.1f}" y1="{MT}" x2="{xp:.1f}" y2="{MT+PH}" stroke="#2a3a4a" stroke-width="0.8" opacity="0.7"/>')
        svg.append(f'<text x="{xp:.1f}" y="{MT+PH+20}" text-anchor="middle" fill="#8899aa" font-size="11" font-family="monospace">{f}</text>')

    svg.append(f'<rect x="{px(18.5):.1f}" y="{MT}" width="{px(40)-px(18.5):.1f}" height="{PH}" fill="#44aaff" opacity="0.04"/>')
    svg.append(f'<line x1="{px(18.5):.1f}" y1="{MT}" x2="{px(18.5):.1f}" y2="{MT+PH}" stroke="#ffcc00" stroke-width="1.5" stroke-dasharray="7,4" opacity="0.75"/>')
    svg.append(f'<text x="{px(18.5)+4:.1f}" y="{MT+14}" fill="#ffcc00" font-size="10" font-family="monospace">18.5 GHz</text>')
    svg.append(f'<line x1="{ML}" y1="{py(-10):.1f}" x2="{ML+PW}" y2="{py(-10):.1f}" stroke="#ff6644" stroke-width="1.4" stroke-dasharray="5,3" opacity="0.65"/>')
    svg.append(f'<text x="{ML+5}" y="{py(-10)-5:.1f}" fill="#ff6644" font-size="10" font-family="monospace">-10 dB</text>')

    svg.append(polyline(fr, s21, "#4db8ff", 2.8))
    svg.append(polyline(fr, s31, "#ff4477", 2.8))
    svg.append(polyline(fr, s11, "#55ee99", 1.8, "5,3"))

    fc = metrics.get("crossing_GHz")
    if fc:
        cx, cy = px(fc), py(at(fr, s21, fc))
        svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" fill="none" stroke="#ffdd44" stroke-width="1.5"/>')

    svg.append(f'<rect x="{ML}" y="{MT}" width="{PW}" height="{PH}" fill="none" stroke="#445566" stroke-width="1.2"/>')

    # Legend
    lx, ly = ML + 14, MT + 16
    svg.append(f'<rect x="{lx-6}" y="{ly-14}" width="168" height="70" rx="4" fill="#1e2535" opacity="0.85"/>')
    for lbl, col, dash in [("S21 — HPF", "#4db8ff", ""), ("S31 — LPF", "#ff4477", ""), ("S11 — return", "#55ee99", "5,2")]:
        da = f' stroke-dasharray="{dash}"' if dash else ""
        svg.append(f'<line x1="{lx}" y1="{ly}" x2="{lx+24}" y2="{ly}" stroke="{col}" stroke-width="2"{da}/>')
        svg.append(f'<text x="{lx+30}" y="{ly+4}" fill="{col}" font-size="11" font-family="sans-serif">{lbl}</text>')
        ly += 22

    # Metrics box
    tm = metrics.get("targets_met", {})
    ann = [
        (title, "#ffee66", 12, True),
        (f"Cross  = {fc:.3f} GHz {'✓' if tm.get('crossing_ge_18p5GHz') else '✗'}" if fc else "Cross  = n/a", "#aaddff", 10, False),
        (f"S31@19 = {metrics['S31_at_19GHz_dB']:.1f} dB {'✓' if tm.get('S31_at_19_le_neg10dB') else '✗'}", "#aaddff", 10, False),
        (f"S31@20 = {metrics['S31_at_20GHz_dB']:.1f} dB {'✓' if tm.get('S31_at_20_le_neg10dB') else '✗'}", "#aaddff", 10, False),
        (f"Ripple = {metrics['ripple_20_25GHz_dB']:.2f} dB {'✓' if tm.get('ripple_20_25GHz_le_1dB') else '✗'}", "#aaddff", 10, False),
        (f"IL 20+ = {metrics['min_IL_20plus_dB']:.1f} dB", "#aaddff", 10, False),
    ]
    ax = ML + PW - 8; ay = MT + 16
    bh = len(ann) * 15 + 8
    svg.append(f'<rect x="{ax-232}" y="{ay-14}" width="238" height="{bh}" rx="4" fill="#1e2535" opacity="0.85"/>')
    for txt, col, sz, bold in ann:
        fw = "bold" if bold else "normal"
        svg.append(f'<text x="{ax}" y="{ay}" text-anchor="end" fill="{col}" font-size="{sz}" font-family="monospace" font-weight="{fw}">{txt}</text>')
        ay += 15

    svg.append(f'<text x="{ML+PW//2}" y="{H-8}" text-anchor="middle" fill="#8899aa" font-size="12" font-family="sans-serif">Frequency (GHz)</text>')
    svg.append(f'<text x="16" y="{MT+PH//2}" text-anchor="middle" fill="#8899aa" font-size="12" font-family="sans-serif" transform="rotate(-90,16,{MT+PH//2})">S-Parameters (dB)</text>')
    svg.append(f'<text x="{W//2}" y="{MT-10}" text-anchor="middle" fill="#ddeeff" font-size="13" font-family="sans-serif" font-weight="bold">{title}</text>')
    svg.append("</svg>")
    return "\n".join(svg)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()

    # Resolve project directory
    proj_arg = Path(args.project)
    project_dir = proj_arg if proj_arg.is_absolute() else HFSS_ROOT / proj_arg
    base_aedt   = project_dir / (project_dir.name.split("2")[0] + "2" if "2" not in project_dir.name else project_dir.name.rstrip("0123456789") + project_dir.name.lstrip(project_dir.name.rstrip("0123456789")))
    # Simpler: just look for the .aedt file at project root
    base_candidates = list(project_dir.glob("*.aedt"))
    base_candidates = [f for f in base_candidates if not f.name.endswith(".lock")]
    if not base_candidates:
        sys.exit(f"ERROR: No .aedt file found in {project_dir}")
    base_aedt = base_candidates[0]

    # Create run directory
    run_name = run_dir_name(args)
    run_dir  = project_dir / "runs" / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    # Set up logging to both console and file
    log_path = run_dir / "run.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
    )
    log = logging.getLogger()

    log.info(f"Run directory : {run_dir}")
    log.info(f"Base project  : {base_aedt}")

    proj_path = run_dir / "result.aedt"

    if args.as_is:
        # No parameter changes — copy base project directly
        import shutil
        shutil.copy2(base_aedt, proj_path)
        log.info("--as-is: using base project unchanged.")
    else:
        # Build parameter updates
        updates  = build_updates(args)
        up_path  = run_dir / "updates.json"
        up_path.write_text(json.dumps(updates, indent=2), encoding="utf-8")
        log.info(f"Parameters    : wC={args.wC}  L4={args.L4}  L2={args.L2}  k={args.k}  idx={args.idx}  c1y={args.c1y}")

        # Generate parameterised .aedt
        result_path = run_dir / "update_result.json"
        log.info("Applying parameter updates to project...")
        ret = subprocess.run(
            ["python", str(INSPECT), str(base_aedt),
             "--set", str(up_path),
             "--write-to", str(proj_path),
             "--out", str(result_path)],
            capture_output=True, text=True,
        )
        if ret.returncode != 0:
            log.error(f"aedt_inspect failed:\n{ret.stderr}")
            sys.exit(1)
        log.info("Project written.")

    # Run HFSS simulation
    s3p_path = run_dir / "result.s3p"
    if args.dry_run:
        log.info("--dry-run: skipping simulation.")
    else:
        log.info("Starting HFSS simulation...")
        ret = subprocess.run(
            [str(IPY), str(HFSS_RUNNER), str(proj_path), str(run_dir)],
            capture_output=True, text=True,
        )
        if ret.returncode != 0 or not s3p_path.exists():
            log.error("HFSS simulation FAILED.")
            if ret.stdout: log.error(ret.stdout[-2000:])
            if ret.stderr: log.error(ret.stderr[-2000:])
            sys.exit(1)
        log.info("Simulation complete.")

    # Parse and analyse results
    if s3p_path.exists():
        fr, s11, s21, s31 = parse_s3p(s3p_path)
        metrics = compute_metrics(fr, s11, s21, s31)
        fc = metrics["crossing_GHz"]
        tm = metrics["targets_met"]

        log.info("─" * 60)
        log.info(f"  Crossing freq : {fc:.3f} GHz  {'✓' if tm['crossing_ge_18p5GHz'] else '✗  (target ≥ 18.5)'}")
        log.info(f"  S31 @ 19 GHz  : {metrics['S31_at_19GHz_dB']:.1f} dB  {'✓' if tm['S31_at_19_le_neg10dB'] else '✗  (target ≤ -10)'}")
        log.info(f"  S31 @ 20 GHz  : {metrics['S31_at_20GHz_dB']:.1f} dB  {'✓' if tm['S31_at_20_le_neg10dB'] else '✗  (target ≤ -10)'}")
        log.info(f"  Ripple 20-25  : {metrics['ripple_20_25GHz_dB']:.2f} dB {'✓' if tm['ripple_20_25GHz_le_1dB'] else '✗  (target ≤ 1)'}")
        log.info(f"  Min IL 20+    : {metrics['min_IL_20plus_dB']:.1f} dB")
        all_ok = all(tm.values())
        log.info(f"  ALL TARGETS   : {'✓ PASS' if all_ok else '✗ FAIL'}")
        log.info("─" * 60)

        # Save params.json
        record = {
            "run":        run_name,
            "timestamp":  datetime.now().isoformat(),
            "as_is":      args.as_is,
            "parameters": {} if args.as_is else {
                "wC": args.wC, "L4": args.L4, "L2": args.L2,
                "k":  args.k,  "idx": args.idx, "c1y": args.c1y,
                "wSub": args.wSub, "wLine": args.wLine,
            },
            "metrics": metrics,
        }
        params_path = run_dir / "params.json"
        params_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        log.info(f"Saved: {params_path.name}")

        # Generate SVG
        title = ("baseline (as-is)" if args.as_is else
                 f"wC={args.wC}  L4={args.L4}  L2={args.L2}  "
                 f"k={args.k}  idx={args.idx}  c1y={args.c1y}")
        svg_path = run_dir / "plot.svg"
        svg_path.write_text(make_svg(fr, s11, s21, s31, metrics, title), encoding="utf-8")
        log.info(f"Saved: {svg_path.name}")

        if args.open_svg:
            subprocess.Popen(["explorer", str(svg_path)])

    log.info(f"Done. Results in: {run_dir}")


if __name__ == "__main__":
    main()
