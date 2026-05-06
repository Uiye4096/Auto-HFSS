"""
run_185g_refine3.py — Run and analyse Phase 4 L2_g3 sweep.

Usage:
    python scripts/run_185g_refine3.py
    python scripts/run_185g_refine3.py --analyse
    python scripts/run_185g_refine3.py --analyse --html
"""
import json
import math
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT      = Path(__file__).parent.parent.parent
MODEL_DIR = Path(__file__).parent.parent
IPY       = Path(r"E:\HFFS\HFSS_2021\Program Files\AnsysEM\AnsysEM21.2\Win64\common\IronPython\ipy64.exe")
RUNNER    = ROOT / "12GHzdiplexer" / "scripts" / "run_hfss_case.py"
MANIFEST  = MODEL_DIR / "runs" / "refine3_manifest.json"
MAX_WORKERS = 4


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
    s11w = max(at(fr, s11, f) for f in [19, 20, 21, 22, 25])
    return {
        "crossing_GHz":          round(fc, 4) if fc else None,
        "S31_at_19GHz_dB":       round(s19,  2),
        "S31_at_20GHz_dB":       round(s20,  2),
        "ripple_20_25GHz_dB":    round(rip,  2),
        "min_IL_20plus_dB":      round(min(pb), 2),
        "S11_worst_19_25GHz_dB": round(s11w, 2),
    }


def run_case(entry):
    run_dir = Path(entry["run_dir"])
    proj    = run_dir / "result.aedt"
    s3p     = run_dir / "result.s3p"
    log_p   = run_dir / "run.log"
    if not proj.exists():
        return entry["name"], None, "not built"
    if s3p.exists():
        return entry["name"], str(s3p), "already done"
    with open(log_p, "w") as lf:
        subprocess.run([str(IPY), str(RUNNER), str(proj), str(run_dir)],
                       stdout=lf, stderr=subprocess.STDOUT)
    if not s3p.exists():
        return entry["name"], None, "HFSS failed"
    return entry["name"], str(s3p), "ok"


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


def main():
    analyse_only = "--analyse" in sys.argv
    open_html    = "--html" in sys.argv

    if not MANIFEST.exists():
        sys.exit("Run build_185g_refine3.py first.")

    cases = json.loads(MANIFEST.read_text(encoding="utf-8"))

    if not analyse_only:
        print(f"Running {len(cases)} cases (max {MAX_WORKERS} parallel)...\n")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futs = {ex.submit(run_case, c): c for c in cases}
            for fut in as_completed(futs):
                name, _, status = fut.result()
                print(f"  {name}: {status}")
        print()

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
            make_html(c["run_dir"], fr, s11, s21, s31, m,
                      f"185g refine3 [{c['uid']}] L2_g3={c['L2_g3185g']} k={c['k']} wC4={c['w_C4']}",
                      open_it=True)

    HDR = f"{'UID':>4} {'L2g3':>6} {'Cross':>7} {'S31@19':>8} {'S31@20':>8} {'Ripple':>7} {'IL':>6} {'S11w':>6}  Targets"
    SEP = "-" * len(HDR)
    print(HDR)
    print(SEP)
    # Reference
    print(f"{'015':>4} {'0.85':>6} {'18.372':>7} {'-9.8':>8} {'-10.4':>8} {'0.81':>7} {'-1.6':>6} {'-7.2':>6}  ✗cross ✗S31@19 ✓S31@20  ← Phase3 base")
    print(SEP)

    for r in sorted(results, key=lambda x: x["L2_g3185g"]):
        m = r["metrics"]
        if m is None:
            print(f"{r['uid']:>4} {r['L2_g3185g']:>6.2f}  (no s3p)")
            continue
        fc   = m["crossing_GHz"]
        okfc = "✓" if fc and fc >= 18.5 else "✗"
        ok19 = "✓" if m["S31_at_19GHz_dB"] <= -10.0 else "✗"
        ok20 = "✓" if m["S31_at_20GHz_dB"] <= -10.0 else "✗"
        okrp = "✓" if m["ripple_20_25GHz_dB"] <= 1.0 else "✗"
        fc_s = f"{fc:.3f}" if fc else "  n/a "
        star = " ★" if (fc and fc >= 18.5 and m["S31_at_19GHz_dB"] <= -10.0) else ""
        print(f"{r['uid']:>4} {r['L2_g3185g']:>6.2f} {fc_s:>7}"
              f" {m['S31_at_19GHz_dB']:>8.1f} {m['S31_at_20GHz_dB']:>8.1f}"
              f" {m['ripple_20_25GHz_dB']:>7.2f} {m['min_IL_20plus_dB']:>6.1f}"
              f" {m['S11_worst_19_25GHz_dB']:>6.1f}"
              f"  {okfc}cross {ok19}S31@19 {ok20}S31@20 {okrp}ripple{star}")

    met = [r for r in results if r["metrics"] and
           r["metrics"]["S31_at_19GHz_dB"] <= -10.0 and
           r["metrics"]["crossing_GHz"] and r["metrics"]["crossing_GHz"] >= 18.5 and
           r["metrics"]["ripple_20_25GHz_dB"] <= 1.0]
    print(SEP)
    print(f"\nAll targets met: {len(met)}/{len(results)}")
    if met:
        best = min(met, key=lambda x: x["metrics"]["S31_at_19GHz_dB"])
        print(f"Best: [{best['uid']}] L2_g3={best['L2_g3185g']}  "
              f"cross={best['metrics']['crossing_GHz']:.3f}  "
              f"S31@19={best['metrics']['S31_at_19GHz_dB']:.1f} dB")


if __name__ == "__main__":
    main()
