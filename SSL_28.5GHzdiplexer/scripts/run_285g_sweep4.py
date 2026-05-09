"""
run_285g_sweep4.py — Round 4: targeted LPF-only push.
HPF is pinned at L2=0.44mm (sweep3 case035, S21@28.5=-3.4dB ~ passband edge).
Only l_C4185g and l_C2185g are varied to push LPF cutoff from ~25 to ~28.5 GHz.
l_C2 = l_C4 * RATIO (ratio maintained from corrected2 baseline).
All other params frozen from sweep3 corrected2.
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
MANIFEST  = RUNS / "sweep4_manifest.json"
MAX_WORKERS = 4
F_MAX = 60.0

# All other params frozen from corrected2 (sweep3), L2 fixed at 0.44mm
L2_FIXED  = 0.44
L4_FIXED  = 0.441403
L7G3      = 0.431018
L7G4      = 0.270035
L_LINE2   = 0.311579
L_L5      = 0.361332
L_L3      = 0.466720
L_L1      = 0.346276
CX        = 0.103860
CY        = -0.103860
W_TAPPER  = 0.051930
H_TAPPER  = 0.051930

# Ratio l_C2/l_C4 from corrected2 baseline
RATIO_C2_C4 = 0.165564 / 0.134655   # 1.229

# l_C4 sweep: scan from 0.07 to 0.14mm to find where S31@28.5 ≈ S21@28.5 ≈ -3.4dB
C4_VALS = [0.07, 0.08, 0.09, 0.10, 0.11, 0.12, 0.14]

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

def build_case(uid, lc4):
    lc2  = lc4 * RATIO_C2_C4
    name = f"{uid}_s4_C4_{int(round(lc4*1000)):03d}"
    rd   = RUNS / name; rd.mkdir(parents=True, exist_ok=True)
    upd  = {
        "w_C4185g":    "1.15mm",
        "w_C2185g":    "1.05mm",
        "L2_g3185g":   f"{L2_FIXED:.6f}mm",
        "L4_g3185g":   f"{L4_FIXED:.6f}mm",
        "L7_g3185g":   f"{L7G3:.6f}mm",
        "L7_g4185g":   f"{L7G4:.6f}mm",
        "l_line2185g": f"{L_LINE2:.6f}mm",
        "l_L5185g":    f"{L_L5:.6f}mm",
        "l_C4185g":    f"{lc4:.6f}mm",
        "l_L3185g":    f"{L_L3:.6f}mm",
        "l_C2185g":    f"{lc2:.6f}mm",
        "l_L1185g":    f"{L_L1:.6f}mm",
        "cx":          f"{CX:.6f}mm",
        "cy":          f"{CY:.6f}mm",
        "w_tapper":    f"{W_TAPPER:.6f}mm",
        "h_tapper":    f"{H_TAPPER:.6f}mm",
    }
    (rd/"updates.json").write_text(json.dumps(upd, indent=2), encoding="utf-8")
    r = subprocess.run(
        ["python", str(INSPECT), str(BASE_AEDT),
         "--set", str(rd/"updates.json"),
         "--write-to", str(rd/"result.aedt")],
        capture_output=True, text=True
    )
    return rd, name, r.returncode == 0, lc2

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
    n = len(C4_VALS)

    if not analyse_only:
        uids = next_uid(count=n)
        print(f"Building {n} cases (sweep4: LPF cap-only push, L2={L2_FIXED}mm fixed)...")
        manifest = []
        for lc4, uid in zip(C4_VALS, uids):
            lc2 = lc4 * RATIO_C2_C4
            rd, name, ok, _ = build_case(uid, lc4)
            print(f"  {'OK' if ok else 'ERR'}: {name}  l_C4={lc4:.4f}  l_C2={lc2:.4f}")
            manifest.append({"uid": uid, "name": name, "run_dir": str(rd), "l_C4": lc4, "l_C2": lc2})
        MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"\nRunning {n} HFSS cases (max {MAX_WORKERS} parallel)...")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futs = {ex.submit(run_hfss, c): c for c in manifest}
            for fut in as_completed(futs):
                name, status = fut.result()
                print(f"  {name}: {status}")
    else:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    print(f"\n{'UID':>4} {'l_C4':>7} {'l_C2':>7}  {'cross':>7} {'S21@28.5':>8} {'S31@28.5':>8} {'S31@29':>7} {'rpl':>5} {'S11w':>6}")
    print("-" * 72)

    best = None
    for c in sorted(manifest, key=lambda x: x["l_C4"]):
        s3p = Path(c["run_dir"]) / "result.s3p"
        if not s3p.exists():
            print(f"{c['uid']:>4} {c['l_C4']:>7.4f} {c['l_C2']:>7.4f}  {'—':>7}  (no result)")
            continue
        fr, s11, s21, s31 = parse_s3p(s3p)
        m = compute(fr, s11, s21, s31)
        fc   = m["crossing_GHz"]
        rpl  = m["ripple_30_38GHz_dB"]
        s11w = m["S11_worst_29_43GHz_dB"]
        gap  = round(m["S21_at_285GHz_dB"] - m["S31_at_285GHz_dB"], 1)
        star = " ★" if (fc and fc >= 28.5) else ""
        note = f"  gap@28.5={gap:+.1f}dB" if abs(gap) < 5 else ""
        if fc and fc >= 28.5 and (best is None or s11w > best["S11_worst_29_43GHz_dB"]):
            best = {**m, "uid": c["uid"], "l_C4": c["l_C4"]}
        print(f"{c['uid']:>4} {c['l_C4']:>7.4f} {c['l_C2']:>7.4f}  "
              f"{str(round(fc,3)) if fc else '—':>7}  "
              f"{m['S21_at_285GHz_dB']:>8.1f}  "
              f"{m['S31_at_285GHz_dB']:>8.1f}  "
              f"{m['S31_at_29GHz_dB']:>7.1f}  "
              f"{str(rpl) if rpl else '—':>5}  "
              f"{s11w:>6.1f}{star}{note}")
        print(f"       crossings: {m['all_crossings_GHz']}")
        make_html(c["run_dir"], fr, s11, s21, s31, m,
                  f"285g sweep4 — {c['name']} (l_C4={c['l_C4']:.4f}mm, L2=0.44mm fixed)")

    if best:
        print(f"\n★ Best: UID {best['uid']}  l_C4={best['l_C4']:.4f}mm  "
              f"cross={best['crossing_GHz']} GHz  S11w={best['S11_worst_29_43GHz_dB']:.1f} dB")
    else:
        print("\n(no case reached 28.5 GHz crossing yet — check gap@28.5 column)")

if __name__ == "__main__":
    main()
