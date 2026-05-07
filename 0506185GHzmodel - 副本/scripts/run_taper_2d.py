"""
run_taper_2d.py — 2D sweep: w_tapper x h_tapper on 087-base model with taper structure.
w_tapper (along-line base): 0.20, 0.40, 0.60, 0.80, 1.00 mm
h_tapper (cut depth):       0.05, 0.10, 0.15, 0.20, 0.25 mm
cx=0.2, cy=-0.2 fixed.  UIDs 002-026.
"""
import json, math, subprocess, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT      = Path(__file__).parent.parent.parent
MODEL_DIR = Path(__file__).parent.parent
IPY       = Path(r"E:\HFFS\HFSS_2021\Program Files\AnsysEM\AnsysEM21.2\Win64\common\IronPython\ipy64.exe")
RUNNER    = ROOT / "12GHzdiplexer" / "scripts" / "run_hfss_case.py"
INSPECT   = ROOT / "tools" / "aedt_inspect.py"
BASE_AEDT = MODEL_DIR / "final" / "diplexer_185g_087.aedt"
RUNS      = MODEL_DIR / "runs"
MAX_WORKERS = 4
F_MAX = 30.0

# 087 fixed parameters
PARAMS_BASE = {
    "w_C4185g": "1.15mm", "w_C2185g": "1.05mm",
    "L4_g3185g": "0.85mm", "L2_g3185g": "0.78mm",
    "L7_g3185g": "0.83mm", "L7_g4185g": "0.52mm",
    "l_line2185g": "0.60mm",
    "l_L5185g": "0.695808mm", "l_C4185g": "0.446477mm",
    "l_L3185g": "0.898752mm", "l_C2185g": "0.504461mm",
    "l_L1185g": "0.666816mm",
    "cx": "0.2mm", "cy": "-0.2mm",
}

# w_tapper: y-span cross-line, max ~0.35mm (feedline=0.395mm)
# h_tapper: x-depth along-line, can be larger
W_VALS = [0.10, 0.15, 0.20, 0.25, 0.30]  # cross-line span (mm)
H_VALS = [0.10, 0.20, 0.40, 0.60, 0.80]  # along-line depth (mm)

# ── S-param parsing ──────────────────────────────────────────────
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
        s11.append(r[1] if fmt=="DB" else (db(r[1]) if fmt=="MA" else db(math.hypot(r[1],r[2]))))
        s21.append(r[7] if fmt=="DB" else (db(r[7]) if fmt=="MA" else db(math.hypot(r[7],r[8]))))
        s31.append(r[13] if fmt=="DB" else (db(r[13]) if fmt=="MA" else db(math.hypot(r[13],r[14]))))
    return fr, s11, s21, s31

def at(fr, v, f): return v[min(range(len(fr)), key=lambda i: abs(fr[i]-f))]

def crossing_freq(fr, s21, s31):
    for i in range(len(fr)-1):
        d0, d1 = s21[i]-s31[i], s21[i+1]-s31[i+1]
        if d0*d1 <= 0:
            t = d0/(d0-d1) if abs(d0-d1) > 1e-9 else 0.5
            return fr[i]+t*(fr[i+1]-fr[i])
    return None

def compute(fr, s11, s21, s31):
    fc  = crossing_freq(fr, s21, s31)
    pb  = [at(fr, s21, f) for f in [20, 21, 22, 23, 25]]
    s11_pts = [i for i in range(len(fr)) if 19.0 <= fr[i] <= 28.0]
    s11w    = max((s11[i] for i in s11_pts), default=max(s11))
    s31_pts = [i for i in range(len(fr)) if 18.5 <= fr[i] <= 28.5]
    s31_stop = max((s31[i] for i in s31_pts), default=at(fr,s31,19))
    s21_pts = [s21[i] for i in range(len(fr)) if 20.0 <= fr[i] <= 28.5]
    return {
        "crossing_GHz":          round(fc, 4) if fc else None,
        "S31_at_19GHz_dB":       round(at(fr, s31, 19.0), 2),
        "S31_at_20GHz_dB":       round(at(fr, s31, 20.0), 2),
        "S31_worst_stop_dB":     round(s31_stop, 2),
        "ripple_20_25GHz_dB":    round(max(pb)-min(pb), 2),
        "S11_worst_19_28GHz_dB": round(s11w, 2),
        "S11_at_19GHz_dB":       round(at(fr, s11, 19.0), 2),
        "S11_at_20GHz_dB":       round(at(fr, s11, 20.0), 2),
        "avg_S21_20_285_dB":     round(sum(s21_pts)/len(s21_pts), 2) if s21_pts else None,
        "min_IL_20plus_dB":       round(min(pb), 2),
        "S11_worst_19_25GHz_dB":  round(s11w, 2),
        "targets_met": {
            "crossing_ge_18p5GHz":     bool(fc and fc >= 18.5),
            "S31_at_19_le_neg10dB":    round(at(fr, s31, 19.0), 2) <= -10.0,
            "S31_at_20_le_neg10dB":    round(at(fr, s31, 20.0), 2) <= -10.0,
            "S31_worst_stop_le_neg10": round(s31_stop, 2) <= -10.0,
            "ripple_20_25GHz_le_1dB":  round(max(pb)-min(pb), 2) <= 1.0,
            "S11w_le_neg10dB":         round(s11w, 2) <= -10.0,
        },
    }

# ── Build / Run ──────────────────────────────────────────────────
def build_case(uid, w, h):
    name = f"{uid}_w{int(w*100):03d}_h{int(h*100):03d}"
    rd   = RUNS / name; rd.mkdir(parents=True, exist_ok=True)
    upd  = dict(PARAMS_BASE)
    upd["w_tapper"] = f"{w}mm"
    upd["h_tapper"] = f"{h}mm"
    (rd/"updates.json").write_text(json.dumps(upd, indent=2), encoding="utf-8")
    r = subprocess.run(["python", str(INSPECT), str(BASE_AEDT),
                        "--set", str(rd/"updates.json"),
                        "--write-to", str(rd/"result.aedt"),
                        "--out", str(rd/"update_result.json")],
                       capture_output=True, text=True)
    return rd, name, r.returncode == 0

def run_hfss(entry):
    rd, name = Path(entry["run_dir"]), entry["name"]
    s3p = rd/"result.s3p"
    if s3p.exists(): return name, "already done"
    with open(rd/"run.log", "w") as lf:
        subprocess.run([str(IPY), str(RUNNER), str(rd/"result.aedt"), str(rd)],
                       stdout=lf, stderr=subprocess.STDOUT)
    return name, "ok" if s3p.exists() else "HFSS failed"

def make_html(rd, fr, s11, s21, s31, m, title):
    sys.path.insert(0, str(ROOT))
    from plot_interactive import build_html
    hp = rd/"plot_30g.html"
    hp.write_text(build_html(fr, s11, s21, s31, m, title), encoding="utf-8")

# ── Main ─────────────────────────────────────────────────────────
def main():
    sys.path.insert(0, str(Path(__file__).parent))
    from _uid import next_uid

    analyse_only = "--analyse" in sys.argv
    cases_grid = [(w, h) for h in H_VALS for w in W_VALS]  # h outer, w inner
    n = len(cases_grid)

    if not analyse_only:
        uids = next_uid(count=n)
        print(f"Building {n} cases (w×h: {len(W_VALS)}×{len(H_VALS)})...")
        manifest = []
        for (w, h), uid in zip(cases_grid, uids):
            rd, name, ok = build_case(uid, w, h)
            print(f"  {'OK' if ok else 'ERR'}: {name}")
            manifest.append({"uid": uid, "name": name, "run_dir": str(rd),
                             "w_tapper": w, "h_tapper": h})
        mp = RUNS/"taper_2d_manifest.json"
        mp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"\nRunning {n} cases (max {MAX_WORKERS} parallel)...")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futs = {ex.submit(run_hfss, c): c for c in manifest}
            for fut in as_completed(futs):
                name, status = fut.result(); print(f"  {name}: {status}")
    else:
        mp = RUNS/"taper_2d_manifest.json"
        manifest = json.loads(mp.read_text(encoding="utf-8"))

    # ── Reference: 087 no taper ──
    ref_s3p = RUNS/"087_L7g3_083_g4052"/"result.s3p"
    fr_r, s11_r, s21_r, s31_r = parse_s3p(ref_s3p)
    m_ref = compute(fr_r, s11_r, s21_r, s31_r)

    print(f"\n{'UID':>4} {'w':>5} {'h':>5}  {'cross':>7} {'S31@20':>7} {'rpl':>5} {'S11w':>6} {'Δcross':>7} {'ΔS11w':>6}")
    print("-"*75)
    print(f"{'087':>4} {'—':>5} {'—':>5}  {m_ref['crossing_GHz']:>7.3f} {m_ref['S31_at_20GHz_dB']:>7.1f} {m_ref['ripple_20_25GHz_dB']:>5.2f} {m_ref['S11_worst_19_28GHz_dB']:>6.1f}  (reference no taper)")
    print("-"*75)

    results = []
    for c in sorted(manifest, key=lambda x: (x["h_tapper"], x["w_tapper"])):
        s3p = Path(c["run_dir"])/"result.s3p"
        if not s3p.exists():
            print(f"{c['uid']:>4} {c['w_tapper']:>5.2f} {c['h_tapper']:>5.2f}  {'—':>7} {'—':>7} {'—':>5} {'—':>6}  (no result)")
            results.append({**c, "metrics": None}); continue
        fr, s11, s21, s31 = parse_s3p(s3p)
        m = compute(fr, s11, s21, s31)
        results.append({**c, "metrics": m})
        fc = m["crossing_GHz"]
        d_fc  = (fc - m_ref["crossing_GHz"]) if fc else float("nan")
        d_s11 = m["S11_worst_19_28GHz_dB"] - m_ref["S11_worst_19_28GHz_dB"]
        star  = " ★" if m["S11_worst_19_28GHz_dB"] <= -10.0 and fc and fc >= 18.5 and m["ripple_20_25GHz_dB"] <= 1.0 else ""
        print(f"{c['uid']:>4} {c['w_tapper']:>5.2f} {c['h_tapper']:>5.2f}  {fc:>7.3f} {m['S31_at_20GHz_dB']:>7.1f} {m['ripple_20_25GHz_dB']:>5.2f} {m['S11_worst_19_28GHz_dB']:>6.1f}  {d_fc:>+7.3f} {d_s11:>+6.2f}{star}")
        make_html(Path(c["run_dir"]), fr, s11, s21, s31, m,
                  f"[{c['uid']}] w={c['w_tapper']:.2f} h={c['h_tapper']:.2f}  S11w={m['S11_worst_19_28GHz_dB']:.1f}dB  cross={fc:.3f}GHz")

    # Summary: best S11w with all constraints
    valid = [r for r in results if r["metrics"] and
             r["metrics"]["crossing_GHz"] and r["metrics"]["crossing_GHz"] >= 18.5 and
             r["metrics"]["ripple_20_25GHz_dB"] <= 1.0 and
             r["metrics"]["S31_at_20GHz_dB"] <= -10.0]
    if valid:
        best = min(valid, key=lambda x: x["metrics"]["S11_worst_19_28GHz_dB"])
        bm = best["metrics"]
        print(f"\n  Best (all constraints): [{best['uid']}] w={best['w_tapper']:.2f} h={best['h_tapper']:.2f}"
              f"  S11w={bm['S11_worst_19_28GHz_dB']:.1f}  S31@20={bm['S31_at_20GHz_dB']:.1f}"
              f"  cross={bm['crossing_GHz']:.3f}  rpl={bm['ripple_20_25GHz_dB']:.2f}")
    else:
        print("\n  No case beats reference on all constraints.")

if __name__ == "__main__": main()
