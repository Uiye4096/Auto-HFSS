"""run_185g_refine6.py — Run Round 7A (L7_g3 sweep). MAX_WORKERS=2 for parallel with refine7."""
import json, math, subprocess, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT       = Path(__file__).parent.parent.parent
MODEL_DIR  = Path(__file__).parent.parent
IPY        = Path(r"E:\HFFS\HFSS_2021\Program Files\AnsysEM\AnsysEM21.2\Win64\common\IronPython\ipy64.exe")
RUNNER     = ROOT / "12GHzdiplexer" / "scripts" / "run_hfss_case.py"
MANIFEST   = MODEL_DIR / "runs" / "refine6_manifest.json"
TUNING_LOG = MODEL_DIR / "TUNING_LOG.md"
MAX_WORKERS = 2


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

def update_log(results, label="L7_g3"):
    rows = []
    for r in sorted(results, key=lambda x: x["L7_g3185g"]):
        m = r["metrics"]
        if m is None: rows.append(f"| {r['uid']} | {r['L7_g3185g']} | — | — | — | — | no s3p |"); continue
        fc=m["crossing_GHz"]; okfc="✓" if fc and fc>=18.5 else "✗"; ok19="✓" if m["S31_at_19GHz_dB"]<=-10.0 else "✗"
        star=" ★" if (fc and fc>=18.5 and m["S31_at_19GHz_dB"]<=-10.0) else ""
        rows.append(f"| {r['uid']} | {r['L7_g3185g']} | {fc:.3f} {okfc} | {m['S31_at_19GHz_dB']:.1f} {ok19} | {m['S31_at_20GHz_dB']:.1f} | {m['ripple_20_25GHz_dB']:.2f} | {m['min_IL_20plus_dB']:.1f} |{star}")
    met = [r for r in results if r["metrics"] and r["metrics"]["S31_at_19GHz_dB"]<=-10.0 and r["metrics"]["crossing_GHz"] and r["metrics"]["crossing_GHz"]>=18.5 and r["metrics"]["ripple_20_25GHz_dB"]<=1.0]
    if met:
        best=min(met, key=lambda x: x["metrics"]["S31_at_19GHz_dB"]); m=best["metrics"]
        ref=f"**假设成立！** [{best['uid']}] L7_g3={best['L7_g3185g']} 全部达标，cross={m['crossing_GHz']:.3f}, S31@19={m['S31_at_19GHz_dB']:.1f} dB。传输零点被 L7_g3 精确调谐。"
        nxt="更新 final/ 为最优 L7_g3 参数，进一步精细扫描其附近（±0.02mm）以最大化余量。"
        import shutil; best_s3p=Path(best["run_dir"])/"result.s3p"; fd=MODEL_DIR/"final"
        if best_s3p.exists(): shutil.copy(best_s3p, fd/f"diplexer_185g_{best['uid']}.s3p")
    else:
        ref="L7_g3 变化对 S31@19 改善有限，说明该元件不直接控制 19 GHz 传输零点，或零点与其他参数强耦合。" if results else "全部仿真失败。"
        nxt="等待方向 B 结果，综合决策下一步。"
    section = f"""
## Round 7A — refine6：L7_g3185g 扫参（结果）

### 结果汇总

| UID | L7_g3 | 交叉 GHz | S31@19 dB | S31@20 dB | 波纹 dB | IL dB |
|---|---|---|---|---|---|---|
| 034（ref） | 0.90 | 18.540 ✓ | −10.2 ✓ | −12.3 | 0.58 | −1.2 |
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
    print("TUNING_LOG updated (refine6).")

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
        if open_html: make_html(c["run_dir"],fr,s11,s21,s31,m, f"[{c['uid']}] L7_g3={c['L7_g3185g']}",open_it=True)
    HDR = f"{'UID':>4} {'L7g3':>5} {'Cross':>7} {'S31@19':>8} {'S31@20':>8} {'Ripple':>7} {'IL':>6}  Targets"
    SEP = "-"*len(HDR)
    print(HDR); print(SEP)
    print(f"{'034':>4} {'0.90':>5} {'18.540':>7} {'-10.2':>8} {'-12.3':>8} {'0.58':>7} {'-1.2':>6}  ✓✓ baseline")
    print(SEP)
    for r in sorted(results, key=lambda x: x["L7_g3185g"]):
        m=r["metrics"]
        if m is None: print(f"{r['uid']:>4} {r['L7_g3185g']:>5.2f}  (no s3p)"); continue
        fc=m["crossing_GHz"]; okfc="✓" if fc and fc>=18.5 else "✗"; ok19="✓" if m["S31_at_19GHz_dB"]<=-10.0 else "✗"
        star=" ★" if (fc and fc>=18.5 and m["S31_at_19GHz_dB"]<=-10.0) else ""
        fc_s = f"{fc:.3f}" if fc else "  n/a "
        print(f"{r['uid']:>4} {r['L7_g3185g']:>5.2f} {fc_s:>7}"
              f" {m['S31_at_19GHz_dB']:>8.1f} {m['S31_at_20GHz_dB']:>8.1f}"
              f" {m['ripple_20_25GHz_dB']:>7.2f} {m['min_IL_20plus_dB']:>6.1f}"
              f"  {okfc}cross {ok19}S31@19{star}")
    update_log(results)

if __name__ == "__main__":
    main()
