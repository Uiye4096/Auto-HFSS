"""
run_185g_sweep1.py — Run HFSS simulations and analyse results for 185g sweep1.

Usage:
    python scripts/run_185g_sweep1.py              # run all cases (sequential)
    python scripts/run_185g_sweep1.py --analyse    # skip sim, just re-analyse existing s3p
    python scripts/run_185g_sweep1.py --html       # also open HTML viewers
"""
import json
import math
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT        = Path(__file__).parent.parent.parent
MODEL_DIR   = Path(__file__).parent.parent
IPY         = Path(r"E:\HFFS\HFSS_2021\Program Files\AnsysEM\AnsysEM21.2\Win64\common\IronPython\ipy64.exe")
RUNNER      = ROOT / "12GHzdiplexer" / "scripts" / "run_hfss_case.py"
MANIFEST    = MODEL_DIR / "runs" / "sweep1_manifest.json"
MAX_WORKERS = 4

# ── S3P parsing (same logic as diplexer.py) ───────────────────────────────────

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
            s11.append(r[1]);  s21.append(r[7]);  s31.append(r[13])
        elif fmt == "MA":
            s11.append(db(r[1]));  s21.append(db(r[7]));  s31.append(db(r[13]))
        else:
            s11.append(db(math.hypot(r[1],  r[2])))
            s21.append(db(math.hypot(r[7],  r[8])))
            s31.append(db(math.hypot(r[13], r[14])))
    return fr, s11, s21, s31


def at(fr, vals, f):
    return vals[min(range(len(fr)), key=lambda i: abs(fr[i] - f))]


def crossing_freq(fr, s21, s31):
    for i in range(len(fr) - 1):
        d0, d1 = s21[i] - s31[i], s21[i+1] - s31[i+1]
        if d0 * d1 <= 0:
            t = d0 / (d0 - d1) if abs(d0 - d1) > 1e-9 else 0.5
            return fr[i] + t * (fr[i+1] - fr[i])
    return None


def compute_metrics(fr, s11, s21, s31):
    fc   = crossing_freq(fr, s21, s31)
    s19  = at(fr, s31, 19.0)
    s20  = at(fr, s31, 20.0)
    pb   = [at(fr, s21, f) for f in [20, 21, 22, 23, 25]]
    rip  = max(pb) - min(pb)
    il20 = min(pb)
    s11w = max(at(fr, s11, f) for f in [19, 20, 21, 22, 25])
    return {
        "crossing_GHz":          round(fc, 4) if fc else None,
        "S31_at_19GHz_dB":       round(s19,  2),
        "S31_at_20GHz_dB":       round(s20,  2),
        "ripple_20_25GHz_dB":    round(rip,  2),
        "min_IL_20plus_dB":      round(il20, 2),
        "S11_worst_19_25GHz_dB": round(s11w, 2),
    }


# ── Simulation runner ─────────────────────────────────────────────────────────

def run_case(entry):
    run_dir  = Path(entry["run_dir"])
    proj     = run_dir / "result.aedt"
    s3p      = run_dir / "result.s3p"
    log_path = run_dir / "run.log"

    if not proj.exists():
        return entry["name"], None, "project not built"

    if s3p.exists():
        return entry["name"], str(s3p), "already done"

    with open(log_path, "w") as lf:
        ret = subprocess.run(
            [str(IPY), str(RUNNER), str(proj), str(run_dir)],
            stdout=lf, stderr=subprocess.STDOUT,
        )
    if ret.returncode != 0 or not s3p.exists():
        return entry["name"], None, "HFSS failed"
    return entry["name"], str(s3p), "ok"


# ── HTML generation ───────────────────────────────────────────────────────────

def make_html(run_dir, fr, s11, s21, s31, metrics, title, open_it=False):
    sys.path.insert(0, str(ROOT))
    from plot_interactive import build_html
    m = dict(metrics)
    fc = m.get("crossing_GHz")
    m.setdefault("targets_met", {
        "crossing_ge_18p5GHz":    bool(fc and fc >= 18.5),
        "S31_at_19_le_neg10dB":   m["S31_at_19GHz_dB"] <= -10.0,
        "S31_at_20_le_neg10dB":   m["S31_at_20GHz_dB"] <= -10.0,
        "ripple_20_25GHz_le_1dB": m["ripple_20_25GHz_dB"] <= 1.0,
    })
    html_path = Path(run_dir) / "plot.html"
    html_path.write_text(build_html(fr, s11, s21, s31, m, title), encoding="utf-8")
    if open_it:
        subprocess.Popen(["explorer", str(html_path)])
    return html_path


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    analyse_only = "--analyse" in sys.argv
    open_html    = "--html" in sys.argv

    if not MANIFEST.exists():
        sys.exit("Run build_185g_sweep1.py first.")

    cases = json.loads(MANIFEST.read_text(encoding="utf-8"))

    # ── Run simulations ──────────────────────────────────────────────────────
    if not analyse_only:
        print(f"Running {len(cases)} simulations (max {MAX_WORKERS} parallel)...\n")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futs = {ex.submit(run_case, c): c for c in cases}
            for fut in as_completed(futs):
                name, s3p, status = fut.result()
                print(f"  {name}: {status}")
        print()

    # ── Analyse ──────────────────────────────────────────────────────────────
    BASELINE = {"crossing_GHz": 18.504, "S31_at_19GHz_dB": -7.9,
                "S31_at_20GHz_dB": -8.1, "ripple_20_25GHz_dB": 0.87,
                "min_IL_20plus_dB": -1.6, "S11_worst_19_25GHz_dB": -7.0}

    results = []
    for c in cases:
        s3p = Path(c["run_dir"]) / "result.s3p"
        if not s3p.exists():
            results.append({**c, "metrics": None})
            continue
        fr, s11, s21, s31 = parse_s3p(s3p)
        m = compute_metrics(fr, s11, s21, s31)
        results.append({**c, "metrics": m})

        if open_html:
            title = f"185g sweep1 wC4={c['w_C4']} wC2={c['w_C2']}"
            make_html(c["run_dir"], fr, s11, s21, s31, m, title, open_it=True)

    # ── Summary table ────────────────────────────────────────────────────────
    HDR = f"{'Case':<28} {'Cross':>7} {'S31@19':>8} {'S31@20':>8} {'Ripple':>7} {'IL':>6} {'S11w':>6}  Targets"
    SEP = "-" * len(HDR)
    print(HDR)
    print(SEP)

    def fmt_row(name, m):
        if m is None:
            return f"{name:<28}  {'(no s3p)':>55}"
        fc   = m["crossing_GHz"]
        s19  = m["S31_at_19GHz_dB"]
        s20  = m["S31_at_20GHz_dB"]
        rip  = m["ripple_20_25GHz_dB"]
        il   = m["min_IL_20plus_dB"]
        s11w = m["S11_worst_19_25GHz_dB"]
        ok19 = "✓" if s19 <= -10.0 else "✗"
        ok20 = "✓" if s20 <= -10.0 else "✗"
        okfc = "✓" if fc and fc >= 18.5 else "✗"
        okrp = "✓" if rip <= 1.0 else "✗"
        tags = f"{okfc}cross {ok19}S31@19 {ok20}S31@20 {okrp}ripple"
        fc_s = f"{fc:.3f}" if fc else "  n/a "
        return (f"{name:<28} {fc_s:>7} {s19:>8.1f} {s20:>8.1f}"
                f" {rip:>7.2f} {il:>6.1f} {s11w:>6.1f}  {tags}")

    # Baseline row
    print(fmt_row("★ baseline (as-is)", BASELINE))
    print(SEP)

    for r in sorted(results, key=lambda x: (
            -(x["metrics"]["S31_at_19GHz_dB"] if x["metrics"] else 99))):
        print(fmt_row(r["name"], r["metrics"]))

    # Targets-met summary
    met = [r for r in results if r["metrics"] and
           r["metrics"]["S31_at_19GHz_dB"] <= -10.0 and
           r["metrics"]["crossing_GHz"] and r["metrics"]["crossing_GHz"] >= 18.5]
    print(SEP)
    print(f"\nCases meeting S31@19≤-10 dB AND crossing≥18.5 GHz: {len(met)}/{len(results)}")
    if met:
        best = min(met, key=lambda x: x["metrics"]["S31_at_19GHz_dB"])
        print(f"Best S31@19: {best['name']}  "
              f"({best['metrics']['S31_at_19GHz_dB']:.1f} dB, "
              f"cross={best['metrics']['crossing_GHz']:.3f} GHz)")


if __name__ == "__main__":
    main()
