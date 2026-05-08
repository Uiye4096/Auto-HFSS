"""
run_285g_sweep1.py — Round 1: L2_g3185g sweep around scaled baseline.
Baseline: 087 × (18.5/28.5), crossing target ≥ 28.5 GHz.
Sweep variable: L2_g3185g (HPF stub → crossing frequency sensitivity check)
"""
import json, math, subprocess, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT      = Path(__file__).parent.parent.parent
MODEL_DIR = Path(__file__).parent.parent
IPY       = Path(r"E:\HFFS\HFSS_2021\Program Files\AnsysEM\AnsysEM21.2\Win64\common\IronPython\ipy64.exe")
RUNNER    = ROOT / "12GHzdiplexer" / "scripts" / "run_hfss_case.py"
INSPECT   = ROOT / "tools" / "aedt_inspect.py"
BASE_AEDT = MODEL_DIR / "final" / "diplexer_285g_baseline.aedt"
RUNS      = MODEL_DIR / "runs"
MANIFEST  = RUNS / "sweep1_manifest.json"
MAX_WORKERS = 4
F_MAX = 60.0   # GHz — scan to 60 GHz for 28.5 GHz design

# Scaled baseline parameters (18.5 GHz × 0.6491)
PARAMS_BASE = {
    "w_C4185g":    "1.15mm",   # WIDTH — unchanged
    "w_C2185g":    "1.05mm",   # WIDTH — unchanged
    "l_line2185g": "0.389474mm",
    "L4_g3185g":   "0.551754mm",
    "L7_g3185g":   "0.538772mm",
    "L7_g4185g":   "0.337544mm",
    "l_L5185g":    "0.451665mm",
    "l_C4185g":    "0.289818mm",
    "l_L3185g":    "0.583400mm",
    "l_C2185g":    "0.327457mm",
    "l_L1185g":    "0.432845mm",
    "cx":          "0.129825mm",
    "cy":          "-0.129825mm",
    "w_tapper":    "0.064912mm",
    "h_tapper":    "0.064912mm",
}

# L2_g3185g sweep: 0.45 → 0.57 mm (baseline=0.5063 mm)
L2_VALS = [0.45, 0.47, 0.49, 0.51, 0.53, 0.55, 0.57]

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
        if fmt == "DB":
            s11.append(r[1]);  s21.append(r[7]);  s31.append(r[13])
        elif fmt == "MA":
            s11.append(db(r[1])); s21.append(db(r[7])); s31.append(db(r[13]))
        else:
            s11.append(db(math.hypot(r[1],r[2])))
            s21.append(db(math.hypot(r[7],r[8])))
            s31.append(db(math.hypot(r[13],r[14])))
    return fr, s11, s21, s31

def at(fr, v, f): return v[min(range(len(fr)), key=lambda i: abs(fr[i]-f))]

def crossing_freq(fr, s21, s31):
    for i in range(len(fr)-1):
        d0, d1 = s21[i]-s31[i], s21[i+1]-s31[i+1]
        if d0*d1 <= 0:
            t = d0/(d0-d1) if abs(d0-d1)>1e-9 else 0.5
            return fr[i]+t*(fr[i+1]-fr[i])
    return None

def compute(fr, s11, s21, s31):
    fc   = crossing_freq(fr, s21, s31)
    # Passband: 30–38 GHz (≈ 20–25 GHz scaled by 28.5/18.5)
    pb   = [at(fr, s21, f) for f in [30, 31, 32, 33, 35, 38]]
    # S11 worst in HPF passband 29–43 GHz (≈ 19–28 GHz scaled)
    s11w = max((s11[i] for i in range(len(fr)) if 29.0 <= fr[i] <= 43.0), default=max(s11))
    s21_pts = [s21[i] for i in range(len(fr)) if 30.0 <= fr[i] <= 43.0]
    return {
        "crossing_GHz":            round(fc, 4) if fc else None,
        "S31_at_29GHz_dB":         round(at(fr, s31, 29.0), 2),
        "S31_at_30GHz_dB":         round(at(fr, s31, 30.0), 2),
        "ripple_30_38GHz_dB":      round(max(pb)-min(pb), 2) if pb else None,
        "S11_worst_29_43GHz_dB":   round(s11w, 2),
        "avg_S21_30_43_dB":        round(sum(s21_pts)/len(s21_pts), 2) if s21_pts else None,
        "targets_met": {
            "crossing_ge_28p5GHz":     bool(fc and fc >= 28.5),
            "S31_at_29_le_neg10dB":    at(fr, s31, 29.0) <= -10.0,
            "S31_at_30_le_neg10dB":    at(fr, s31, 30.0) <= -10.0,
            "ripple_30_38GHz_le_1dB":  (max(pb)-min(pb)) <= 1.0 if pb else False,
            "S11w_le_neg10dB":         s11w <= -10.0,
        },
    }

# ── Build / Run / HTML ───────────────────────────────────────────
def build_case(uid, L2):
    name = f"{uid}_L2g3_{int(round(L2*100)):03d}"
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
    hp = Path(rd) / "plot_60g.html"
    hp.write_text(build_html(fr, s11, s21, s31, m, title), encoding="utf-8")

# ── Main ─────────────────────────────────────────────────────────
def main():
    sys.path.insert(0, str(Path(__file__).parent))
    from _uid import next_uid

    analyse_only = "--analyse" in sys.argv
    n = len(L2_VALS)

    if not analyse_only:
        uids = next_uid(count=n)
        print(f"Building {n} cases (L2_g3185g sweep for 28.5 GHz)...")
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

    print(f"\n{'UID':>4} {'L2_g3':>7}  {'cross':>7} {'S31@29':>7} {'S31@30':>7} {'rpl':>5} {'S11w':>6}")
    print("-" * 58)
    print(f"  baseline  0.5063  (scaled 087, expect ~28.5 GHz crossing)")
    print("-" * 58)

    best = None
    for c in sorted(manifest, key=lambda x: x["L2_g3"]):
        s3p = Path(c["run_dir"]) / "result.s3p"
        if not s3p.exists():
            print(f"{c['uid']:>4} {c['L2_g3']:>7.4f}  {'—':>7} {'—':>7} {'—':>7} {'—':>5} {'—':>6}  (no result)")
            continue
        fr, s11, s21, s31 = parse_s3p(s3p)
        m = compute(fr, s11, s21, s31)
        fc  = m["crossing_GHz"]
        rpl = m["ripple_30_38GHz_dB"]
        s11w = m["S11_worst_29_43GHz_dB"]
        star = ""
        if (fc and fc >= 28.5 and m["S31_at_30GHz_dB"] <= -10.0
                and rpl is not None and rpl <= 1.0):
            star = " ★"
            if best is None or s11w < best["S11_worst_29_43GHz_dB"]:
                best = {**m, "uid": c["uid"], "L2_g3": c["L2_g3"]}
        print(f"{c['uid']:>4} {c['L2_g3']:>7.4f}  "
              f"{fc if fc else '—':>7}  "
              f"{m['S31_at_29GHz_dB']:>7.1f} "
              f"{m['S31_at_30GHz_dB']:>7.1f} "
              f"{rpl if rpl else '—':>5} "
              f"{s11w:>6.1f}{star}")
        make_html(c["run_dir"], fr, s11, s21, s31, m,
                  f"285g sweep1 — {c['name']} (L2={c['L2_g3']:.4f}mm)")

    if best:
        print(f"\n★ Best: UID {best['uid']}  L2_g3={best['L2_g3']:.4f} mm  "
              f"cross={best['crossing_GHz']} GHz  S11w={best['S11_worst_29_43GHz_dB']:.1f} dB")

if __name__ == "__main__":
    main()
