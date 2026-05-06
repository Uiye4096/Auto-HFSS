"""
run_185g_40g_rescan.py — Re-run 037, 039, 024 with sweep extended to 40 GHz.

Patches result.aedt in each case folder:
  RangeEnd='35GHz' -> '40GHz'
  RangeCount=401   -> 471   (keeps ~75 MHz spacing over 35 GHz span)
Deletes existing s3p, re-runs HFSS, regenerates HTML plots.

Usage:
    python scripts/run_185g_40g_rescan.py
    python scripts/run_185g_40g_rescan.py --analyse  (just reparse existing s3p)
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
MAX_WORKERS = 3

CASES = [
    {"uid": "037", "run_dir": MODEL_DIR / "runs" / "037_L7g3_075",
     "label": "L7g3=0.75 (FINAL ★)"},
    {"uid": "047", "run_dir": MODEL_DIR / "runs" / "047_L7g3_072",
     "label": "L7g3=0.72"},
    {"uid": "048", "run_dir": MODEL_DIR / "runs" / "048_L7g3_073",
     "label": "L7g3=0.73"},
    {"uid": "038", "run_dir": MODEL_DIR / "runs" / "038_L7g3_080",
     "label": "L7g3=0.80"},
    {"uid": "049", "run_dir": MODEL_DIR / "runs" / "049_L7g3_074",
     "label": "L7g3=0.74"},
    {"uid": "039", "run_dir": MODEL_DIR / "runs" / "039_L7g3_085",
     "label": "L7g3=0.85"},
    {"uid": "024", "run_dir": MODEL_DIR / "runs" / "024_L2g3_078",
     "label": "L7g3=0.90 (baseline L7)"},
    {"uid": "BASE", "run_dir": MODEL_DIR / "runs" / "000_baseline",
     "label": "BASELINE (no mods)"},
]


def patch_aedt_40g(aedt_path):
    """Extend sweep to 40 GHz and increase point count."""
    text = aedt_path.read_text(encoding="utf-8", errors="ignore")
    if "40GHz" in text:
        return False  # already patched
    text = text.replace("RangeEnd='35GHz'", "RangeEnd='40GHz'")
    text = text.replace("RangeCount=401",   "RangeCount=471")
    aedt_path.write_text(text, encoding="utf-8")
    return True


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
    db = lambda v: 20 * math.log10(v) if v > 0 else -100.0
    fr, s11, s21, s31 = [], [], [], []
    for r in recs:
        if len(r) < 19: continue
        f = r[0] / 1e9 if r[0] > 1e7 else r[0]
        fr.append(f)
        if fmt == "DB":   s11.append(r[1]);  s21.append(r[7]);  s31.append(r[13])
        elif fmt == "MA": s11.append(db(r[1])); s21.append(db(r[7])); s31.append(db(r[13]))
        else:             s11.append(db(math.hypot(r[1],r[2]))); s21.append(db(math.hypot(r[7],r[8]))); s31.append(db(math.hypot(r[13],r[14])))
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
    pb   = [at(fr, s21, f) for f in [20, 21, 22, 23, 25]]
    return {
        "crossing_GHz":          round(fc, 4) if fc else None,
        "S31_at_19GHz_dB":       round(at(fr, s31, 19.0), 2),
        "S31_at_20GHz_dB":       round(at(fr, s31, 20.0), 2),
        "S31_at_30GHz_dB":       round(at(fr, s31, 30.0), 2),
        "S31_at_35GHz_dB":       round(at(fr, s31, 35.0), 2),
        "S31_at_40GHz_dB":       round(at(fr, s31, 40.0), 2),
        "ripple_20_25GHz_dB":    round(max(pb) - min(pb), 2),
        "min_IL_20plus_dB":      round(min(pb), 2),
        "S11_worst_19_25GHz_dB": round(max(at(fr, s11, f) for f in [19, 20, 21, 22, 25]), 2),
    }


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
    hp = Path(run_dir) / "plot_40g.html"
    hp.write_text(build_html(fr, s11, s21, s31, m, title), encoding="utf-8")
    if open_it:
        subprocess.Popen(["explorer", str(hp)])
    return hp


def run_case(c):
    run_dir = Path(c["run_dir"])
    proj    = run_dir / "result.aedt"
    s3p     = run_dir / "result.s3p"
    log_p   = run_dir / "run_40g.log"
    if not proj.exists():
        return c["uid"], "not built"
    patched = patch_aedt_40g(proj)
    if s3p.exists():
        s3p.unlink()  # delete old s3p so HFSS re-runs
        print(f"  [{c['uid']}] deleted old s3p, running with 40 GHz sweep...")
    elif patched:
        print(f"  [{c['uid']}] patched to 40 GHz, running...")
    with open(log_p, "w") as lf:
        subprocess.run([str(IPY), str(RUNNER), str(proj), str(run_dir)],
                       stdout=lf, stderr=subprocess.STDOUT)
    if not s3p.exists():
        return c["uid"], "HFSS failed"
    return c["uid"], "ok"


def main():
    analyse_only = "--analyse" in sys.argv

    if not analyse_only:
        print(f"Patching and re-running {len(CASES)} cases to 40 GHz...\n")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futs = {ex.submit(run_case, c): c for c in CASES}
            for fut in as_completed(futs):
                uid, status = fut.result()
                print(f"  [{uid}]: {status}")
        print()

    print(f"\n{'UID':>4}  {'Label':<30} {'Cross':>7} {'S31@19':>7} {'S31@20':>7} {'S31@30':>7} {'S31@35':>7} {'S31@40':>7} {'Ripple':>7} {'IL':>6}")
    print("-" * 100)
    for c in CASES:
        s3p = Path(c["run_dir"]) / "result.s3p"
        if not s3p.exists():
            print(f"  [{c['uid']}] no s3p"); continue
        fr, s11, s21, s31 = parse_s3p(s3p)
        m = compute_metrics(fr, s11, s21, s31)
        fc = m["crossing_GHz"]
        fc_s = f"{fc:.3f}" if fc else "  n/a "
        print(f"{c['uid']:>4}  {c['label']:<30}"
              f" {fc_s:>7}"
              f" {m['S31_at_19GHz_dB']:>7.1f}"
              f" {m['S31_at_20GHz_dB']:>7.1f}"
              f" {m['S31_at_30GHz_dB']:>7.1f}"
              f" {m['S31_at_35GHz_dB']:>7.1f}"
              f" {m['S31_at_40GHz_dB']:>7.1f}"
              f" {m['ripple_20_25GHz_dB']:>7.2f}"
              f" {m['min_IL_20plus_dB']:>6.1f}")
        make_html(c["run_dir"], fr, s11, s21, s31, m,
                  f"[{c['uid']}] 5-40GHz {c['label']}",
                  open_it=True)


if __name__ == "__main__":
    main()
