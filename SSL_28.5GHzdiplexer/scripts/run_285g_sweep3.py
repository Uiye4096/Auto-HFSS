"""
run_285g_sweep3.py — Round 3: corrected2 baseline + L2_g3185g sweep.
Base: diplexer_285g_corrected2.aedt (all lengths × 0.80 from corrected, l_C fringing × 2).
Sweep: L2_g3185g 0.28–0.52 mm.
"""
import json, math, subprocess, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT      = Path(__file__).parent.parent.parent
MODEL_DIR = Path(__file__).parent.parent
IPY       = Path(r"E:\HFFS\HFSS_2021\Program Files\AnsysEM\AnsysEM21.2\Win64\common\IronPython\ipy64.exe")
RUNNER    = ROOT / "12GHzdiplexer" / "scripts" / "run_hfss_case.py"
INSPECT   = ROOT / "tools" / "aedt_inspect.py"
BASE_AEDT = MODEL_DIR / "final" / "diplexer_285g_corrected2.aedt"
RUNS      = MODEL_DIR / "runs"
MANIFEST  = RUNS / "sweep3_manifest.json"
MAX_WORKERS = 4
F_MAX = 60.0

PARAMS_BASE = {
    "w_C4185g":    "1.15mm",
    "w_C2185g":    "1.05mm",
    "l_line2185g": "0.311579mm",
    "L4_g3185g":   "0.441403mm",
    "L7_g3185g":   "0.431018mm",
    "L7_g4185g":   "0.270035mm",
    "l_L5185g":    "0.361332mm",
    "l_C4185g":    "0.134655mm",
    "l_L3185g":    "0.466720mm",
    "l_C2185g":    "0.165564mm",
    "l_L1185g":    "0.346276mm",
    "cx":          "0.103860mm",
    "cy":          "-0.103860mm",
    "w_tapper":    "0.051930mm",
    "h_tapper":    "0.051930mm",
}

# L2 sweep — baseline 0.506316 × 0.80 = 0.405mm; sweep 0.28–0.52
L2_VALS = [0.28, 0.32, 0.36, 0.40, 0.44, 0.48, 0.52]

# ── S-param helpers ──────────────────────────────────────────────
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
        if f > F_MAX: continue
        fr.append(f)
        if fmt == "DB":   s11.append(r[1]);  s21.append(r[7]);  s31.append(r[13])
        elif fmt == "MA": s11.append(db(r[1])); s21.append(db(r[7])); s31.append(db(r[13]))
        else:             s11.append(db(math.hypot(r[1],r[2]))); s21.append(db(math.hypot(r[7],r[8]))); s31.append(db(math.hypot(r[13],r[14])))
    return fr, s11, s21, s31

def at(fr, v, f): return v[min(range(len(fr)), key=lambda i: abs(fr[i]-f))]

def all_crossings(fr, s21, s31):
    pts = []
    for i in range(len(fr)-1):
        d0, d1 = s21[i]-s31[i], s21[i+1]-s31[i+1]
        if d0*d1 <= 0:
            t = d0/(d0-d1) if abs(d0-d1)>1e-9 else 0.5
            pts.append((fr[i]+t*(fr[i+1]-fr[i]), s21[i]+t*(s21[i+1]-s21[i])))
    return pts

def best_crossing(fr, s21, s31):
    pts = all_crossings(fr, s21, s31)
    if not pts: return None
    return min(pts, key=lambda x: abs(x[1]-(-3.0)))[0]

def compute(fr, s11, s21, s31):
    fc   = best_crossing(fr, s21, s31)
    pb   = [at(fr, s21, f) for f in [30, 31, 32, 33, 35, 38]]
    s11w = max((s11[i] for i in range(len(fr)) if 29.0 <= fr[i] <= 43.0), default=max(s11))
    s21_pts = [s21[i] for i in range(len(fr)) if 30.0 <= fr[i] <= 43.0]
    all_c = all_crossings(fr, s21, s31)
    return {
        "crossing_GHz":          round(fc, 4) if fc else None,
        "all_crossings_GHz":     [(round(f,3), round(l,2)) for f,l in all_c],
        "S31_at_29GHz_dB":       round(at(fr, s31, 29.0), 2),
        "S31_at_30GHz_dB":       round(at(fr, s31, 30.0), 2),
        "S21_at_285GHz_dB":      round(at(fr, s21, 28.5), 2),
        "S31_at_285GHz_dB":      round(at(fr, s31, 28.5), 2),
        "ripple_30_38GHz_dB":    round(max(pb)-min(pb), 2) if pb else None,
        "S11_worst_29_43GHz_dB": round(s11w, 2),
        "avg_S21_30_43_dB":      round(sum(s21_pts)/len(s21_pts), 2) if s21_pts else None,
        "targets_met": {
            "crossing_ge_28p5GHz":    bool(fc and fc >= 28.5),
            "crossing_ge_18p5GHz":    bool(fc and fc >= 18.5),
            "S31_at_29_le_neg10dB":   at(fr, s31, 29.0) <= -10.0,
            "S31_at_30_le_neg10dB":   at(fr, s31, 30.0) <= -10.0,
            "S31_at_19_le_neg10dB":   at(fr, s31, 29.0) <= -10.0,
            "S31_at_20_le_neg10dB":   at(fr, s31, 30.0) <= -10.0,
            "S31_worst_stop_le_neg10": at(fr, s31, 30.0) <= -10.0,
            "ripple_30_38GHz_le_1dB": (max(pb)-min(pb)) <= 1.0 if pb else False,
            "ripple_20_25GHz_le_1dB": (max(pb)-min(pb)) <= 1.0 if pb else False,
            "S11w_le_neg10dB":        s11w <= -10.0,
        },
    }

def build_case(uid, L2):
    name = f"{uid}_s3_L2g3_{int(round(L2*100)):03d}"
    rd   = RUNS / name; rd.mkdir(parents=True, exist_ok=True)
    upd  = dict(PARAMS_BASE); upd["L2_g3185g"] = f"{L2:.5f}mm"
    (rd/"updates.json").write_text(json.dumps(upd, indent=2), encoding="utf-8")
    r = subprocess.run(
        ["python", str(INSPECT), str(BASE_AEDT),
         "--set", str(rd/"updates.json"),
         "--write-to", str(rd/"result.aedt")],
        capture_output=True, text=True
    )
    return rd, name, r.returncode == 0

def run_hfss(entry):
    rd, name = Path(entry["run_dir"]), entry["name"]
    if (rd/"result.s3p").exists(): return name, "already done"
    with open(rd/"run.log", "w") as lf:
        subprocess.run([str(IPY), str(RUNNER), str(rd/"result.aedt"), str(rd)],
                       stdout=lf, stderr=subprocess.STDOUT)
    return name, "ok" if (rd/"result.s3p").exists() else "HFSS failed"

def make_html(rd, fr, s11, s21, s31, m, title):
    sys.path.insert(0, str(ROOT))
    from plot_interactive import build_html
    m2 = dict(m)
    m2.setdefault("S31_at_19GHz_dB",       m2.get("S31_at_29GHz_dB", -99))
    m2.setdefault("S31_at_20GHz_dB",       m2.get("S31_at_30GHz_dB", -99))
    m2.setdefault("S31_worst_stop_dB",     m2.get("S31_at_30GHz_dB", -99))
    m2.setdefault("ripple_20_25GHz_dB",    m2.get("ripple_30_38GHz_dB", 0))
    m2.setdefault("min_IL_20plus_dB",      m2.get("avg_S21_30_43_dB", -99))
    m2.setdefault("S11_worst_19_25GHz_dB", m2.get("S11_worst_29_43GHz_dB", -99))
    hp = Path(rd) / "plot_60g.html"
    try:
        hp.write_text(build_html(fr, s11, s21, s31, m2, title), encoding="utf-8")
    except Exception as e:
        print(f"  [HTML warn] {e}")

def main():
    sys.path.insert(0, str(Path(__file__).parent))
    from _uid import next_uid

    analyse_only = "--analyse" in sys.argv
    n = len(L2_VALS)

    if not analyse_only:
        uids = next_uid(count=n)
        print(f"Building {n} cases (sweep3: corrected2 × 0.80 + L2 sweep)...")
        manifest = []
        for L2, uid in zip(L2_VALS, uids):
            rd, name, ok = build_case(uid, L2)
            print(f"  {'OK' if ok else 'ERR'}: {name}")
            manifest.append({"uid": uid, "name": name, "run_dir": str(rd), "L2_g3": L2})
        MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"\nRunning {n} HFSS cases (max {MAX_WORKERS} parallel)...")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futs = {ex.submit(run_hfss, c): c for c in manifest}
            for fut in as_completed(futs):
                name, status = fut.result()
                print(f"  {name}: {status}")
    else:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    print(f"\n{'UID':>4} {'L2_g3':>7}  {'cross':>7} {'S21@28.5':>8} {'S31@28.5':>8} {'S31@29':>7} {'rpl':>5} {'S11w':>6}")
    print("-" * 66)

    best = None
    for c in sorted(manifest, key=lambda x: x["L2_g3"]):
        s3p = Path(c["run_dir"]) / "result.s3p"
        if not s3p.exists():
            print(f"{c['uid']:>4} {c['L2_g3']:>7.4f}  {'—':>7}  (no result)")
            continue
        fr, s11, s21, s31 = parse_s3p(s3p)
        m = compute(fr, s11, s21, s31)
        fc   = m["crossing_GHz"]
        rpl  = m["ripple_30_38GHz_dB"]
        s11w = m["S11_worst_29_43GHz_dB"]
        star = " ★" if (fc and fc >= 28.5) else ""
        if fc and fc >= 28.5 and (best is None or s11w > best["S11_worst_29_43GHz_dB"]):
            best = {**m, "uid": c["uid"], "L2_g3": c["L2_g3"]}
        print(f"{c['uid']:>4} {c['L2_g3']:>7.4f}  "
              f"{str(round(fc,3)) if fc else '—':>7}  "
              f"{m['S21_at_285GHz_dB']:>8.1f}  "
              f"{m['S31_at_285GHz_dB']:>8.1f}  "
              f"{m['S31_at_29GHz_dB']:>7.1f}  "
              f"{str(rpl) if rpl else '—':>5}  "
              f"{s11w:>6.1f}{star}")
        print(f"       crossings: {m['all_crossings_GHz']}")
        make_html(c["run_dir"], fr, s11, s21, s31, m,
                  f"285g sweep3 — {c['name']} (L2={c['L2_g3']:.4f}mm)")

    if best:
        print(f"\n★ Best ≥28.5GHz: UID {best['uid']}  L2_g3={best['L2_g3']:.4f}mm  "
              f"cross={best['crossing_GHz']} GHz  S11w={best['S11_worst_29_43GHz_dB']:.1f} dB")
    else:
        print("\n(no case reached 28.5 GHz crossing yet)")

if __name__ == "__main__":
    main()
