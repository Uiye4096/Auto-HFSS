"""
run_285g_sweep6.py — Round 6: fix LPF (case024), push HPF cutoff up independently.
Start: case024 params (fringing-corrected LPF, L2=0.40mm, crossing~24.7GHz).
Strategy: scale HPF stubs (L4_g3, L7_g3, L7_g4, l_line2) by k_HPF < 1.0
          → HPF cutoff shifts from ~24GHz toward 28.5GHz.
          Sweep L2 at each k_HPF to bracket crossing.
LPF params: FROZEN from case024.
HPF scale k_HPF: 0.75, 0.80, 0.85, 0.90  (need ~0.84 to reach 24→28.5 GHz)
L2_g3 sweep per k_HPF: independent scan.
"""
import json, math, subprocess, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT      = Path(__file__).parent.parent.parent
MODEL_DIR = Path(__file__).parent.parent
IPY       = Path(r"E:\HFFS\HFSS_2021\Program Files\AnsysEM\AnsysEM21.2\Win64\common\IronPython\ipy64.exe")
RUNNER    = ROOT / "12GHzdiplexer" / "scripts" / "run_hfss_case.py"
INSPECT   = ROOT / "tools" / "aedt_inspect.py"
BASE_AEDT = MODEL_DIR / "final" / "diplexer_285g_corrected.aedt"   # case024 baseline
RUNS      = MODEL_DIR / "runs"
MANIFEST  = RUNS / "sweep6_manifest.json"
MAX_WORKERS = 4
F_MAX = 60.0

# ── LPF: FROZEN from case024 (fringing-corrected) ──────────────
LPF = {
    "w_C4185g":  "1.15mm",
    "w_C2185g":  "1.05mm",
    "l_L5185g":  "0.451665mm",
    "l_C4185g":  "0.218870mm",
    "l_L3185g":  "0.583400mm",
    "l_C2185g":  "0.257090mm",
    "l_L1185g":  "0.432845mm",
    "cx":        "0.129825mm",
    "cy":        "-0.129825mm",
    "w_tapper":  "0.064912mm",
    "h_tapper":  "0.064912mm",
}

# ── HPF base values from corrected1 baseline (case024) ─────────
HPF_BASE = {
    "l_line2185g": 0.389474,
    "L4_g3185g":   0.551754,
    "L7_g3185g":   0.538772,
    "L7_g4185g":   0.337544,
}

# HPF scale × L2 scan grid
# k=0.842 is the theoretical push 24GHz→28.5GHz factor
K_HPF_VALS = [0.75, 0.80, 0.85, 0.90]
# L2 sweep: shorter range since HPF cutoff is moving up
L2_PER_K  = {
    0.75: [0.24, 0.28, 0.32, 0.36],
    0.80: [0.28, 0.32, 0.36, 0.40],
    0.85: [0.30, 0.34, 0.38, 0.42],
    0.90: [0.32, 0.36, 0.40, 0.44],
}

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

def main_crossing(fr, s21, s31):
    """
    Return the PRIMARY diplexer crossing: the first (lowest-freq) crossing where
    S21 rises above S31 for the first time (LPF→HPF handoff).
    This avoids spurious high-freq crossings.
    """
    pts = all_crossings(fr, s21, s31)
    if not pts: return None
    # The main crossing is where S21 first exceeds S31 going up in frequency.
    # Before this crossing: S31 > S21 (LPF dominant).
    # After this crossing: S21 > S31 (HPF dominant), at least initially.
    # Find all crossings where the sign change is LPF→HPF (d0<0 means S21<S31 before).
    lpf_to_hpf = []
    for i in range(len(fr)-1):
        d0 = s21[i]-s31[i]
        d1 = s21[i+1]-s31[i+1]
        if d0 < 0 and d1 >= 0:   # S21 crosses ABOVE S31
            t = d0/(d0-d1) if abs(d0-d1)>1e-9 else 0.5
            fc = fr[i]+t*(fr[i+1]-fr[i])
            lv = s21[i]+t*(s21[i+1]-s21[i])
            lpf_to_hpf.append((fc, lv))
    if not lpf_to_hpf:
        return min(pts, key=lambda x: abs(x[1]-(-3.0)))[0]
    # Among LPF→HPF crossings, prefer the one closest to -3 dB
    return min(lpf_to_hpf, key=lambda x: abs(x[1]-(-3.0)))[0]

def compute(fr, s11, s21, s31):
    fc   = main_crossing(fr, s21, s31)
    pb   = [at(fr, s21, f) for f in [30, 31, 32, 33, 35, 38]]
    s11w = max((s11[i] for i in range(len(fr)) if 29.0 <= fr[i] <= 43.0), default=max(s11))
    s21_pts = [s21[i] for i in range(len(fr)) if 30.0 <= fr[i] <= 43.0]
    all_c = all_crossings(fr, s21, s31)
    return {
        "crossing_GHz":          round(fc, 4) if fc else None,
        "all_crossings_GHz":     [(round(f,3), round(l,2)) for f,l in all_c],
        "S21_at_285GHz_dB":      round(at(fr, s21, 28.5), 2),
        "S31_at_285GHz_dB":      round(at(fr, s31, 28.5), 2),
        "S31_at_29GHz_dB":       round(at(fr, s31, 29.0), 2),
        "S31_at_30GHz_dB":       round(at(fr, s31, 30.0), 2),
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

def build_case(uid, k, L2):
    name = f"{uid}_s6_k{int(round(k*100)):03d}_L2_{int(round(L2*100)):03d}"
    rd   = RUNS / name; rd.mkdir(parents=True, exist_ok=True)
    upd  = dict(LPF)
    for par, val in HPF_BASE.items():
        upd[par] = f"{val*k:.6f}mm"
    upd["L2_g3185g"] = f"{L2:.5f}mm"
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

    cases = [(k, L2) for k in K_HPF_VALS for L2 in L2_PER_K[k]]
    n = len(cases)

    if not analyse_only:
        uids = next_uid(count=n)
        print(f"Building {n} cases (sweep6: LPF frozen, HPF push only)...")
        print(f"  LPF fixed: l_C4={LPF['l_C4185g']}, l_C2={LPF['l_C2185g']}, w_C4={LPF['w_C4185g']}")
        manifest = []
        for (k, L2), uid in zip(cases, uids):
            rd, name, ok = build_case(uid, k, L2)
            print(f"  {'OK' if ok else 'ERR'}: {name}")
            manifest.append({"uid": uid, "name": name, "run_dir": str(rd), "k_HPF": k, "L2_g3": L2})
        MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"\nRunning {n} HFSS cases (max {MAX_WORKERS} parallel)...")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futs = {ex.submit(run_hfss, c): c for c in manifest}
            for fut in as_completed(futs):
                name, status = fut.result()
                print(f"  {name}: {status}")
    else:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    print(f"\n{'UID':>4} {'kHPF':>6} {'L2':>6}  {'cross':>7} {'@28.5 S21':>9} {'S31':>6} {'gap':>5} {'rpl':>5} {'S11w':>6}")
    print("-" * 74)

    by_k = {}
    for c in manifest:
        s3p = Path(c["run_dir"]) / "result.s3p"
        if not s3p.exists():
            print(f"{c['uid']:>4} {c['k_HPF']:>6.2f} {c['L2_g3']:>6.3f}  {'—':>7}  (no result)")
            continue
        fr, s11, s21, s31 = parse_s3p(s3p)
        m = compute(fr, s11, s21, s31)
        fc   = m["crossing_GHz"]
        rpl  = m["ripple_30_38GHz_dB"]
        s11w = m["S11_worst_29_43GHz_dB"]
        gap  = round(m["S21_at_285GHz_dB"] - m["S31_at_285GHz_dB"], 1)
        star = " ★" if (fc and fc >= 28.5) else ""
        print(f"{c['uid']:>4} {c['k_HPF']:>6.2f} {c['L2_g3']:>6.3f}  "
              f"{str(round(fc,2)) if fc else '—':>7}  "
              f"{m['S21_at_285GHz_dB']:>9.1f}  {m['S31_at_285GHz_dB']:>6.1f}  "
              f"{gap:>+5.1f}  {str(rpl) if rpl else '—':>5}  {s11w:>6.1f}{star}")
        print(f"       cross_all: {m['all_crossings_GHz']}")
        make_html(c["run_dir"], fr, s11, s21, s31, m,
                  f"285g sweep6 — {c['name']} (k={c['k_HPF']:.2f} L2={c['L2_g3']:.3f}mm)")
        k = c["k_HPF"]
        if k not in by_k or (fc and (not by_k[k]["fc"] or
                (fc >= 28.5 and (not by_k[k].get("star") or s11w > by_k[k]["s11w"]))
                or (not fc or abs(fc-28.5) < abs((by_k[k]["fc"] or 99)-28.5)))):
            by_k[k] = {"uid": c["uid"], "fc": fc, "s11w": s11w, "L2": c["L2_g3"],
                        "star": fc and fc>=28.5}

    print("\n── Best per k_HPF ──")
    for k in sorted(by_k):
        b = by_k[k]
        star = " ★" if b["star"] else ""
        print(f"  k={k:.2f}: UID {b['uid']}  L2={b['L2']:.3f}mm  cross={b['fc']} GHz  S11w={b['s11w']:.1f} dB{star}")

if __name__ == "__main__":
    main()
