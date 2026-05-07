"""
run_taper_baseline.py
Run case 001: 087 params + default taper (cx=0.2, cy=-0.2, w=0.2, h=0.1)
Compare against pre-taper 087 result.
"""
import json, math, subprocess, sys
from pathlib import Path

ROOT      = Path(__file__).parent.parent.parent
MODEL_DIR = Path(__file__).parent.parent
IPY       = Path(r"E:\HFFS\HFSS_2021\Program Files\AnsysEM\AnsysEM21.2\Win64\common\IronPython\ipy64.exe")
RUNNER    = ROOT / "12GHzdiplexer" / "scripts" / "run_hfss_case.py"
INSPECT   = ROOT / "tools" / "aedt_inspect.py"
BASE_AEDT = MODEL_DIR / "final" / "diplexer_185g_087.aedt"
RUNS      = MODEL_DIR / "runs"
F_MAX     = 30.0

# 087 base parameters (non-taper)
PARAMS_087 = {
    "w_C4185g":  "1.15mm",
    "w_C2185g":  "1.05mm",
    "L4_g3185g": "0.85mm",
    "L2_g3185g": "0.78mm",
    "L7_g3185g": "0.83mm",
    "L7_g4185g": "0.52mm",
    "l_line2185g":"0.60mm",
    "l_L5185g":  "0.695808mm",
    "l_C4185g":  "0.446477mm",
    "l_L3185g":  "0.898752mm",
    "l_C2185g":  "0.504461mm",
    "l_L1185g":  "0.666816mm",
    # taper at model defaults
    "cx":        "0.2mm",
    "cy":        "-0.2mm",
    "w_tapper":  "0.2mm",   # default (y-span, cross-line)
    "h_tapper":  "0.1mm",   # default (x-depth, along-line)
}

def parse_s3p(path, fmax=F_MAX):
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
        if f > fmax: continue
        fr.append(f)
        if fmt == "DB":   s11.append(r[1]);  s21.append(r[7]);  s31.append(r[13])
        elif fmt == "MA": s11.append(db(r[1])); s21.append(db(r[7])); s31.append(db(r[13]))
        else:             s11.append(db(math.hypot(r[1],r[2]))); s21.append(db(math.hypot(r[7],r[8]))); s31.append(db(math.hypot(r[13],r[14])))
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
    s21_pts = [s21[i] for i in range(len(fr)) if 20.0 <= fr[i] <= 28.5]
    return {
        "crossing_GHz":          round(fc, 4) if fc else None,
        "S31_at_19GHz_dB":       round(at(fr, s31, 19.0), 2),
        "S31_at_20GHz_dB":       round(at(fr, s31, 20.0), 2),
        "ripple_20_25GHz_dB":    round(max(pb)-min(pb), 2),
        "min_IL_20plus_dB":      round(min(pb), 2),
        "S11_worst_19_28GHz_dB": round(s11w, 2),
        "S11_at_19GHz_dB":       round(at(fr, s11, 19.0), 2),
        "S11_at_20GHz_dB":       round(at(fr, s11, 20.0), 2),
        "avg_S21_20_285_dB":     round(sum(s21_pts)/len(s21_pts), 2) if s21_pts else None,
    }

def print_metrics(label, m):
    fc = m["crossing_GHz"]
    print(f"\n  [{label}]")
    print(f"    crossing    = {fc:.3f} GHz {'✓' if fc and fc>=18.5 else '✗'}")
    print(f"    S31@19      = {m['S31_at_19GHz_dB']:.1f} dB")
    print(f"    S31@20      = {m['S31_at_20GHz_dB']:.1f} dB  {'✓' if m['S31_at_20GHz_dB']<=-10 else '✗'}")
    print(f"    ripple      = {m['ripple_20_25GHz_dB']:.2f} dB  {'✓' if m['ripple_20_25GHz_dB']<=1 else '✗'}")
    print(f"    S11w(19-28) = {m['S11_worst_19_28GHz_dB']:.1f} dB  {'✓' if m['S11_worst_19_28GHz_dB']<=-10 else '✗'}")
    print(f"    S11@19      = {m['S11_at_19GHz_dB']:.1f} dB  S11@20 = {m['S11_at_20GHz_dB']:.1f} dB")
    print(f"    avg S21     = {m['avg_S21_20_285_dB']:.2f} dB")

def build_case(uid, params, name):
    rd = RUNS / name; rd.mkdir(parents=True, exist_ok=True)
    (rd/"updates.json").write_text(json.dumps(params, indent=2), encoding="utf-8")
    r = subprocess.run(["python", str(INSPECT), str(BASE_AEDT),
                        "--set", str(rd/"updates.json"),
                        "--write-to", str(rd/"result.aedt"),
                        "--out", str(rd/"update_result.json")],
                       capture_output=True, text=True)
    ok = r.returncode == 0
    print(f"  Build {'OK' if ok else 'FAILED'}: {name}")
    return rd, ok

def run_hfss(rd):
    proj = rd/"result.aedt"; s3p = rd/"result.s3p"
    if s3p.exists(): print("  Already done, skipping HFSS."); return True
    with open(rd/"run.log", "w") as lf:
        ret = subprocess.run([str(IPY), str(RUNNER), str(proj), str(rd)],
                             stdout=lf, stderr=subprocess.STDOUT)
    ok = s3p.exists()
    print(f"  HFSS {'OK' if ok else 'FAILED'}")
    return ok

def open_html(rd, fr, s11, s21, s31, m, title):
    sys.path.insert(0, str(ROOT))
    from plot_interactive import build_html
    fc = m.get("crossing_GHz")
    m.setdefault("min_IL_20plus_dB", m.get("min_IL_20plus_dB", -99))
    m.setdefault("S11_worst_19_25GHz_dB", m.get("S11_worst_19_28GHz_dB", -99))
    m.setdefault("S31_worst_stop_dB", m.get("S31_at_19GHz_dB", -99))
    m.setdefault("targets_met", {
        "crossing_ge_18p5GHz":     bool(fc and fc >= 18.5),
        "S31_at_19_le_neg10dB":    m.get("S31_at_19GHz_dB", 0) <= -10.0,
        "S31_at_20_le_neg10dB":    m.get("S31_at_20GHz_dB", 0) <= -10.0,
        "S31_worst_stop_le_neg10": m.get("S31_at_19GHz_dB", 0) <= -10.0,
        "ripple_20_25GHz_le_1dB":  m.get("ripple_20_25GHz_dB", 99) <= 1.0,
        "S11w_le_neg10dB":         m.get("S11_worst_19_28GHz_dB", 0) <= -10.0,
    })
    hp = rd/"plot_30g.html"
    hp.write_text(build_html(fr, s11, s21, s31, m, title), encoding="utf-8")
    subprocess.Popen(["explorer", str(hp)])

def main():
    sys.path.insert(0, str(Path(__file__).parent))
    from _uid import next_uid

    uid  = next_uid()  # 001
    name = f"{uid}_taper_baseline"
    print(f"\n=== Taper Baseline Simulation (case {uid}) ===")
    print(f"  Model : {BASE_AEDT.name}  (with taper structure)")
    print(f"  Params: 087 base + cx=0.2 cy=-0.2 w_tapper=0.2 h_tapper=0.1\n")

    rd, ok = build_case(uid, PARAMS_087, name)
    if not ok: print("Build failed, exit."); return

    run_hfss(rd)

    s3p = rd/"result.s3p"
    if not s3p.exists(): print("No s3p, simulation failed."); return

    fr_new, s11_new, s21_new, s31_new = parse_s3p(s3p)
    m_new = compute(fr_new, s11_new, s21_new, s31_new)

    # 087 reference
    ref_s3p = RUNS/"087_L7g3_083_g4052"/"result.s3p"
    fr_ref, s11_ref, s21_ref, s31_ref = parse_s3p(ref_s3p)
    m_ref = compute(fr_ref, s11_ref, s21_ref, s31_ref)

    print("\n--- Metrics comparison ---")
    print_metrics("087  (no taper)", m_ref)
    print_metrics(f"{uid}  (taper default)", m_new)

    print("\n--- Delta (taper - no_taper) ---")
    for k in ["crossing_GHz","S31_at_19GHz_dB","S31_at_20GHz_dB",
              "ripple_20_25GHz_dB","S11_worst_19_28GHz_dB","avg_S21_20_285_dB"]:
        v_ref = m_ref.get(k); v_new = m_new.get(k)
        if v_ref is not None and v_new is not None:
            delta = v_new - v_ref
            arrow = "↑" if delta > 0 else "↓"
            print(f"    {k:32s}: {delta:+.2f}  {arrow}")

    open_html(rd, fr_new, s11_new, s21_new, s31_new, m_new,
              f"[{uid}] Taper baseline  cx=0.2 cy=-0.2 w=0.2 h=0.1  S11w={m_new['S11_worst_19_28GHz_dB']:.1f}dB")
    print(f"\nHTML plot opened: {rd/'plot_30g.html'}")

if __name__ == "__main__": main()
