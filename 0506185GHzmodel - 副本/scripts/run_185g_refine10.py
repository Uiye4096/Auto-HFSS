"""run_185g_refine10.py — Round 10: l_line185g S11 phase sweep."""
import json, math, subprocess, sys, shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT       = Path(__file__).parent.parent.parent
MODEL_DIR  = Path(__file__).parent.parent
IPY        = Path(r"E:\HFFS\HFSS_2021\Program Files\AnsysEM\AnsysEM21.2\Win64\common\IronPython\ipy64.exe")
RUNNER     = ROOT / "12GHzdiplexer" / "scripts" / "run_hfss_case.py"
MANIFEST   = MODEL_DIR / "runs" / "refine10_manifest.json"
TUNING_LOG = MODEL_DIR / "TUNING_LOG.md"
MAX_WORKERS = 4
F_MAX = 30.0

REF024 = {"uid":"024","l_line185g":2.0,"crossing_GHz":18.535,
          "S31_at_19GHz_dB":-10.1,"S31_at_20GHz_dB":-11.9,
          "ripple_20_25GHz_dB":0.56,"min_IL_20plus_dB":-1.3,
          "S11_worst_19_25GHz_dB":-7.2,"S11_at_20GHz_dB":-12.1,
          "S11_at_25GHz_dB":-5.8,"S11_at_28GHz_dB":-4.6}


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
    fc   = crossing_freq(fr, s21, s31)
    pb25 = [at(fr, s21, f) for f in [20, 21, 22, 23, 25]]
    s19  = at(fr, s31, 19.0)
    return {
        "crossing_GHz":          round(fc, 4) if fc else None,
        "S31_at_19GHz_dB":       round(s19, 2),
        "S31_at_20GHz_dB":       round(at(fr, s31, 20.0), 2),
        "ripple_20_25GHz_dB":    round(max(pb25)-min(pb25), 2),
        "min_IL_20plus_dB":      round(min(pb25), 2),
        "S11_worst_19_25GHz_dB": round(max(at(fr, s11, f) for f in [19, 20, 21, 22, 25]), 2),
        "S11_worst_19_28GHz_dB": round(max(at(fr, s11, f) for f in [19, 20, 21, 22, 25, 28]), 2),
        "S11_at_20GHz_dB":       round(at(fr, s11, 20.0), 2),
        "S11_at_25GHz_dB":       round(at(fr, s11, 25.0), 2),
        "S11_at_28GHz_dB":       round(at(fr, s11, 28.0), 2),
    }

def run_case(entry):
    rd  = Path(entry["run_dir"]); proj=rd/"result.aedt"; s3p=rd/"result.s3p"
    if not proj.exists(): return entry["name"], None, "not built"
    if s3p.exists():      return entry["name"], str(s3p), "already done"
    with open(rd/"run.log","w") as lf:
        subprocess.run([str(IPY), str(RUNNER), str(proj), str(rd)], stdout=lf, stderr=subprocess.STDOUT)
    return entry["name"], str(s3p) if s3p.exists() else None, "ok" if s3p.exists() else "HFSS failed"

def make_html(run_dir, fr, s11, s21, s31, metrics, title):
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
    hp = Path(run_dir) / "plot_30g.html"
    hp.write_text(build_html(fr, s11, s21, s31, m, title), encoding="utf-8")
    return hp

def update_log(results):
    rows = []
    for r in results:
        m = r["metrics"]
        if m is None: rows.append(f"| {r['uid']} | {r['l_line185g']} | — | — | — | — | no s3p |"); continue
        fc = m["crossing_GHz"]
        fc_s = f"{fc:.3f}" if fc else " n/a "
        ok_fc  = "✓" if fc and fc >= 18.5 else "✗"
        ok_19  = "✓" if m["S31_at_19GHz_dB"] <= -10.0 else "✗"
        ok_s11 = "✓" if m["S11_worst_19_25GHz_dB"] <= -10.0 else "✗"
        star = " ★" if (fc and fc >= 18.5 and m["S31_at_19GHz_dB"] <= -10.0 and
                        m["ripple_20_25GHz_dB"] <= 1.0 and m["S11_worst_19_25GHz_dB"] <= -10.0) else ""
        rows.append(f"| {r['uid']} | {r['l_line185g']} | {fc_s} {ok_fc} | {m['S31_at_19GHz_dB']:.1f} {ok_19} | {m['S31_at_20GHz_dB']:.1f} | {m['ripple_20_25GHz_dB']:.2f} | {m['S11_worst_19_25GHz_dB']:.1f} {ok_s11} |{star}")

    met = [r for r in results if r["metrics"] and
           r["metrics"]["S31_at_19GHz_dB"] <= -10.0 and
           r["metrics"]["crossing_GHz"] and r["metrics"]["crossing_GHz"] >= 18.5 and
           r["metrics"]["ripple_20_25GHz_dB"] <= 1.0]
    best_s11 = min(met, key=lambda x: x["metrics"]["S11_worst_19_25GHz_dB"]) if met else None

    ref = REF024
    if best_s11:
        bm = best_s11["metrics"]
        delta = round(bm["S11_worst_19_25GHz_dB"] - ref["S11_worst_19_25GHz_dB"], 1)
        improved = delta < 0
        ref_str = (f"l_line185g = {best_s11['l_line185g']}mm 时 S11w = {bm['S11_worst_19_25GHz_dB']:.1f} dB "
                   f"({'改善 ' + str(abs(delta)) + ' dB' if improved else '未改善，与 024 持平'})。")
        if improved:
            nxt = f"以 {best_s11['uid']} (l_line={best_s11['l_line185g']}mm) 为新基点精细扫参，步长 0.1mm。"
        else:
            nxt = "l_line185g 相位旋转对 S11w 改善有限。下一步尝试 kong185G（间隙参数）或检查 HPF 端口匹配网络几何。"
    else:
        ref_str = "所有满足 S31/crossing 约束的 case S11w 均未改善。"
        nxt = "l_line185g 不是 S11 匹配的主控参数。下一步检查 kong185G 或 l_line2185g。"

    section = f"""
## Round 10 — refine10：l_line185g 线长扫参（S11 相位调谐）

**基准**：024  l_line=2.0mm  S11w = {ref['S11_worst_19_25GHz_dB']:.1f} dB  目标：< −10 dB

### 结果汇总

| UID | l_line | 交叉 GHz | S31@19 dB | S31@20 dB | 波纹 dB | S11w dB |
|---|---|---|---|---|---|---|
| 024（ref） | 2.0 | 18.535 ✓ | −10.1 ✓ | −11.9 | 0.56 | −7.2 |
{chr(10).join(rows)}

### 反思
{ref_str}

### 下一步
{nxt}

---

"""
    log = TUNING_LOG.read_text(encoding="utf-8")
    log = log.replace("<!-- 后续每次仿真完成后在此追加新的 Round -->",
                      section + "<!-- 后续每次仿真完成后在此追加新的 Round -->")
    TUNING_LOG.write_text(log, encoding="utf-8")
    print("TUNING_LOG updated (refine10).")

    if best_s11 and best_s11["metrics"]["S11_worst_19_25GHz_dB"] < ref["S11_worst_19_25GHz_dB"]:
        s3p = Path(best_s11["run_dir"]) / "result.s3p"
        if s3p.exists():
            shutil.copy(s3p, MODEL_DIR / "final" / f"diplexer_185g_{best_s11['uid']}.s3p")
            (MODEL_DIR/"final"/"parameters.json").write_text(
                json.dumps({"uid": best_s11["uid"], "metrics": best_s11["metrics"],
                            "status": "all_targets_met"}, indent=2), encoding="utf-8")
            print(f"  final/ updated → [{best_s11['uid']}]")


def main():
    analyse_only = "--analyse" in sys.argv
    cases = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if not analyse_only:
        print(f"Running {len(cases)} cases (max {MAX_WORKERS} parallel)...\n")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futs = {ex.submit(run_case, c): c for c in cases}
            for fut in as_completed(futs):
                name, _, status = fut.result(); print(f"  {name}: {status}")
        print()

    HDR = f"{'UID':>4} {'l_line':>6} {'Cross':>7} {'S31@19':>7} {'S31@20':>7} {'Rpl25':>6} {'S11w':>6} {'@20':>6} {'@25':>6} {'@28':>6}"
    print(HDR); print("-"*len(HDR))
    r = REF024
    fc_s = f"{r['crossing_GHz']:.3f}"
    print(f"{'024':>4} {'2.00':>6} {fc_s:>7} {r['S31_at_19GHz_dB']:>7.1f} {r['S31_at_20GHz_dB']:>7.1f}"
          f" {r['ripple_20_25GHz_dB']:>6.2f} {r['S11_worst_19_25GHz_dB']:>6.1f}"
          f" {r['S11_at_20GHz_dB']:>6.1f} {r['S11_at_25GHz_dB']:>6.1f} {r['S11_at_28GHz_dB']:>6.1f}  (ref)")
    print("-"*len(HDR))

    results = []
    for c in sorted(cases, key=lambda x: x["l_line185g"]):
        s3p = Path(c["run_dir"]) / "result.s3p"
        if not s3p.exists(): results.append({**c, "metrics": None}); continue
        fr, s11, s21, s31 = parse_s3p(s3p)
        m = compute_metrics(fr, s11, s21, s31)
        results.append({**c, "metrics": m})
        fc = m["crossing_GHz"]
        fc_s = f"{fc:.3f}" if fc else "  n/a "
        ok19  = "✓" if m["S31_at_19GHz_dB"] <= -10.0 else "✗"
        ok_s11 = "✓" if m["S11_worst_19_25GHz_dB"] <= -10.0 else "✗"
        star = " ★" if (fc and fc >= 18.5 and m["S31_at_19GHz_dB"] <= -10.0 and
                        m["ripple_20_25GHz_dB"] <= 1.0 and m["S11_worst_19_25GHz_dB"] <= -10.0) else ""
        print(f"{c['uid']:>4} {c['l_line185g']:>6.2f} {fc_s:>7}"
              f" {m['S31_at_19GHz_dB']:>7.1f}{ok19}"
              f" {m['S31_at_20GHz_dB']:>7.1f} {m['ripple_20_25GHz_dB']:>6.2f}"
              f" {m['S11_worst_19_25GHz_dB']:>6.1f}{ok_s11}"
              f" {m['S11_at_20GHz_dB']:>6.1f} {m['S11_at_25GHz_dB']:>6.1f} {m['S11_at_28GHz_dB']:>6.1f}{star}")
        make_html(c["run_dir"], fr, s11, s21, s31, m,
                  f"[{c['uid']}] l_line={c['l_line185g']}mm  S11w={m['S11_worst_19_25GHz_dB']:.1f}dB")

    update_log(results)


if __name__ == "__main__":
    main()
