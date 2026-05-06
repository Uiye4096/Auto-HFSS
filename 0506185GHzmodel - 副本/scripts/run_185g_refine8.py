"""run_185g_refine8.py — Round 8: L7_g3 fine sweep around 0.75mm peak."""
import json, math, subprocess, sys, shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT       = Path(__file__).parent.parent.parent
MODEL_DIR  = Path(__file__).parent.parent
IPY        = Path(r"E:\HFFS\HFSS_2021\Program Files\AnsysEM\AnsysEM21.2\Win64\common\IronPython\ipy64.exe")
RUNNER     = ROOT / "12GHzdiplexer" / "scripts" / "run_hfss_case.py"
MANIFEST   = MODEL_DIR / "runs" / "refine8_manifest.json"
TUNING_LOG = MODEL_DIR / "TUNING_LOG.md"
MAX_WORKERS = 4

REF037 = {"uid":"037","L7_g3185g":0.75,"crossing_GHz":18.546,"S31_at_19GHz_dB":-10.9,
          "S31_at_20GHz_dB":-12.3,"ripple_20_25GHz_dB":0.54,"min_IL_20plus_dB":-1.4}


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
        fr.append(f)
        if fmt=="DB":   s11.append(r[1]);  s21.append(r[7]);  s31.append(r[13])
        elif fmt=="MA": s11.append(db(r[1])); s21.append(db(r[7])); s31.append(db(r[13]))
        else:           s11.append(db(math.hypot(r[1],r[2]))); s21.append(db(math.hypot(r[7],r[8]))); s31.append(db(math.hypot(r[13],r[14])))
    return fr, s11, s21, s31

def at(fr, v, f): return v[min(range(len(fr)), key=lambda i: abs(fr[i]-f))]

def crossing_freq(fr, s21, s31):
    for i in range(len(fr)-1):
        d0, d1 = s21[i]-s31[i], s21[i+1]-s31[i+1]
        if d0*d1 <= 0:
            t = d0/(d0-d1) if abs(d0-d1)>1e-9 else 0.5
            return fr[i]+t*(fr[i+1]-fr[i])
    return None

def compute_metrics(fr, s11, s21, s31):
    fc  = crossing_freq(fr, s21, s31)
    pb  = [at(fr,s21,f) for f in [20,21,22,23,25]]
    return {
        "crossing_GHz":          round(fc,4) if fc else None,
        "S31_at_19GHz_dB":       round(at(fr,s31,19.0),2),
        "S31_at_20GHz_dB":       round(at(fr,s31,20.0),2),
        "ripple_20_25GHz_dB":    round(max(pb)-min(pb),2),
        "min_IL_20plus_dB":      round(min(pb),2),
        "S11_worst_19_25GHz_dB": round(max(at(fr,s11,f) for f in [19,20,21,22,25]),2),
    }

def run_case(entry):
    rd = Path(entry["run_dir"]); proj=rd/"result.aedt"; s3p=rd/"result.s3p"
    if not proj.exists(): return entry["name"], None, "not built"
    if s3p.exists():      return entry["name"], str(s3p), "already done"
    with open(rd/"run.log","w") as lf:
        subprocess.run([str(IPY), str(RUNNER), str(proj), str(rd)], stdout=lf, stderr=subprocess.STDOUT)
    return entry["name"], str(s3p) if s3p.exists() else None, "ok" if s3p.exists() else "HFSS failed"

def make_html(run_dir, fr, s11, s21, s31, metrics, title, open_it=False):
    sys.path.insert(0, str(ROOT))
    from plot_interactive import build_html
    m = dict(metrics); fc=m.get("crossing_GHz")
    m.setdefault("targets_met", {
        "crossing_ge_18p5GHz": bool(fc and fc>=18.5),
        "S31_at_19_le_neg10dB": m["S31_at_19GHz_dB"]<=-10.0,
        "S31_at_20_le_neg10dB": m["S31_at_20GHz_dB"]<=-10.0,
        "ripple_20_25GHz_le_1dB": m["ripple_20_25GHz_dB"]<=1.0,
    })
    hp = Path(run_dir)/"plot.html"; hp.write_text(build_html(fr,s11,s21,s31,m,title), encoding="utf-8")
    if open_it: subprocess.Popen(["explorer", str(hp)])
    return hp

def update_log(results):
    all_r = [REF037] + [r for r in results if r["metrics"]]
    all_r = sorted(all_r, key=lambda x: x["L7_g3185g"] if isinstance(x,dict) else x["L7_g3185g"])
    rows = []
    for r in results:
        m = r["metrics"]
        if m is None: rows.append(f"| {r['uid']} | {r['L7_g3185g']} | — | — | — | no s3p |"); continue
        fc=m["crossing_GHz"]; okfc="✓" if fc and fc>=18.5 else "✗"; ok19="✓" if m["S31_at_19GHz_dB"]<=-10.0 else "✗"
        star=" ★" if (fc and fc>=18.5 and m["S31_at_19GHz_dB"]<=-10.0) else ""
        fc_s = f"{fc:.3f}" if fc else " n/a "
        rows.append(f"| {r['uid']} | {r['L7_g3185g']} | {fc_s} {okfc} | {m['S31_at_19GHz_dB']:.1f} {ok19} | {m['S31_at_20GHz_dB']:.1f} | {m['ripple_20_25GHz_dB']:.2f} | {m['min_IL_20plus_dB']:.1f} |{star}")

    met = [r for r in results if r["metrics"] and r["metrics"]["S31_at_19GHz_dB"]<=-10.0
           and r["metrics"]["crossing_GHz"] and r["metrics"]["crossing_GHz"]>=18.5
           and r["metrics"]["ripple_20_25GHz_dB"]<=1.0]
    all_met = met + [{"uid":"037","L7_g3185g":0.75,"metrics":{"crossing_GHz":18.546,"S31_at_19GHz_dB":-10.9,"S31_at_20GHz_dB":-12.3,"ripple_20_25GHz_dB":0.54,"min_IL_20plus_dB":-1.4,"S11_worst_19_25GHz_dB":-7.4}}]
    best = min(all_met, key=lambda x: x["metrics"]["S31_at_19GHz_dB"])
    bm = best["metrics"]
    ref = (f"L7_g3 在 {best['L7_g3185g']}mm 处取得最大 S31@19 抑制 {bm['S31_at_19GHz_dB']:.1f} dB。"
           f"传输零点调谐精准，S31 余量从优化初始的 0.2 dB 提升至 {abs(bm['S31_at_19GHz_dB'])-10:.1f} dB。")
    nxt = "更新 final/ 为最优 L7_g3。若需进一步提升，可探索 L7_g3 + wC2 联合微调，或以当前结果为最终设计。"

    if best["uid"] != "037":
        s3p = Path(MODEL_DIR / "runs" / best["name"] / "result.s3p") if "name" in best else None
        if s3p and s3p.exists():
            shutil.copy(s3p, MODEL_DIR / "final" / f"diplexer_185g_{best['uid']}.s3p")
            (MODEL_DIR/"final"/"parameters.json").write_text(
                json.dumps({"uid":best["uid"],"metrics":bm,"status":"all_targets_met"},indent=2),encoding="utf-8")
            print(f"  final/ updated → [{best['uid']}] L7_g3={best['L7_g3185g']}")

    section = f"""
## Round 8 — refine8：L7_g3185g 精细扫参（结果）

### 结果汇总（含 037 参考点）

| UID | L7_g3 | 交叉 GHz | S31@19 dB | S31@20 dB | 波纹 dB | IL dB |
|---|---|---|---|---|---|---|
| 034（ref） | 0.90 | 18.540 ✓ | −10.2 ✓ | −12.3 | 0.58 | −1.2 |
| **037（ref）** | **0.75** | **18.546 ✓** | **−10.9 ✓** | **−12.3** | **0.54** | **−1.4** |
{chr(10).join(rows)}

### 反思
{ref}

### 下一步
{nxt}

---

"""
    log = TUNING_LOG.read_text(encoding="utf-8")
    log = log.replace("<!-- 后续每次仿真完成后在此追加新的 Round -->", section+"<!-- 后续每次仿真完成后在此追加新的 Round -->")
    TUNING_LOG.write_text(log, encoding="utf-8")
    print("TUNING_LOG updated (refine8).")

def main():
    analyse_only = "--analyse" in sys.argv
    open_html    = "--html" in sys.argv
    cases = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if not analyse_only:
        print(f"Running {len(cases)} cases (max {MAX_WORKERS} parallel)...\n")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futs = {ex.submit(run_case,c): c for c in cases}
            for fut in as_completed(futs):
                name,_,status = fut.result(); print(f"  {name}: {status}")
        print()
    results = []
    for c in cases:
        s3p = Path(c["run_dir"])/"result.s3p"
        if not s3p.exists(): results.append({**c,"metrics":None}); continue
        fr,s11,s21,s31 = parse_s3p(s3p); m = compute_metrics(fr,s11,s21,s31)
        results.append({**c,"metrics":m})
        if open_html: make_html(c["run_dir"],fr,s11,s21,s31,m,f"[{c['uid']}] L7_g3={c['L7_g3185g']}",open_it=True)

    HDR = f"{'UID':>4} {'L7g3':>5} {'Cross':>7} {'S31@19':>8} {'S31@20':>8} {'Ripple':>7} {'IL':>6}  Targets"
    SEP = "-"*len(HDR)
    print(HDR); print(SEP)
    print(f"{'037':>4} {'0.75':>5} {'18.546':>7} {'-10.9':>8} {'-12.3':>8} {'0.54':>7} {'-1.4':>6}  ✓✓ refine6 peak")
    print(SEP)
    for r in sorted(results, key=lambda x: x["L7_g3185g"]):
        m=r["metrics"]
        if m is None: print(f"{r['uid']:>4} {r['L7_g3185g']:>5.2f}  (no s3p)"); continue
        fc=m["crossing_GHz"]; okfc="✓" if fc and fc>=18.5 else "✗"; ok19="✓" if m["S31_at_19GHz_dB"]<=-10.0 else "✗"
        fc_s = f"{fc:.3f}" if fc else "  n/a "
        star=" ★" if (fc and fc>=18.5 and m["S31_at_19GHz_dB"]<=-10.0) else ""
        print(f"{r['uid']:>4} {r['L7_g3185g']:>5.2f} {fc_s:>7}"
              f" {m['S31_at_19GHz_dB']:>8.1f} {m['S31_at_20GHz_dB']:>8.1f}"
              f" {m['ripple_20_25GHz_dB']:>7.2f} {m['min_IL_20plus_dB']:>6.1f}"
              f"  {okfc}cross {ok19}S31@19{star}")
    update_log(results)

if __name__ == "__main__":
    main()
