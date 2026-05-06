"""run_185g_refine9.py — Round 9: L4_g4/L2_g4 S11 matching sweep."""
import json, math, subprocess, sys, shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT       = Path(__file__).parent.parent.parent
MODEL_DIR  = Path(__file__).parent.parent
IPY        = Path(r"E:\HFFS\HFSS_2021\Program Files\AnsysEM\AnsysEM21.2\Win64\common\IronPython\ipy64.exe")
RUNNER     = ROOT / "12GHzdiplexer" / "scripts" / "run_hfss_case.py"
MANIFEST   = MODEL_DIR / "runs" / "refine9_manifest.json"
TUNING_LOG = MODEL_DIR / "TUNING_LOG.md"
MAX_WORKERS = 4
F_MAX = 30.0

REF024 = {"uid":"024","L4_g4185g":0.501,"crossing_GHz":18.535,
          "S31_at_19GHz_dB":-10.1,"S31_at_20GHz_dB":-11.9,
          "ripple_20_25GHz_dB":0.56,"min_IL_20plus_dB":-1.3,
          "S11_worst_19_25GHz_dB":-7.2}


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
    s11_pts = [at(fr, s11, f) for f in [19, 20, 21, 22, 25, 28]]
    return {
        "crossing_GHz":          round(fc, 4) if fc else None,
        "S31_at_19GHz_dB":       round(s19, 2),
        "S31_at_20GHz_dB":       round(at(fr, s31, 20.0), 2),
        "ripple_20_25GHz_dB":    round(max(pb25)-min(pb25), 2),
        "min_IL_20plus_dB":      round(min(pb25), 2),
        "S11_worst_19_25GHz_dB": round(max(s11_pts[:5]), 2),
        "S11_worst_19_28GHz_dB": round(max(s11_pts), 2),
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
        if m is None: rows.append(f"| {r['uid']} | {r['L4_g4185g']} | — | — | — | — | no s3p |"); continue
        fc = m["crossing_GHz"]
        fc_s = f"{fc:.3f}" if fc else " n/a "
        ok_fc = "✓" if fc and fc >= 18.5 else "✗"
        ok_19 = "✓" if m["S31_at_19GHz_dB"] <= -10.0 else "✗"
        star  = " ★" if (fc and fc >= 18.5 and m["S31_at_19GHz_dB"] <= -10.0 and m["S11_worst_19_25GHz_dB"] <= -10.0) else ""
        rows.append(f"| {r['uid']} | {r['L4_g4185g']} | {fc_s} {ok_fc} | {m['S31_at_19GHz_dB']:.1f} {ok_19} | {m['S31_at_20GHz_dB']:.1f} | {m['ripple_20_25GHz_dB']:.2f} | {m['S11_worst_19_25GHz_dB']:.1f} |{star}")

    met_all = [r for r in results if r["metrics"] and
               r["metrics"]["S31_at_19GHz_dB"] <= -10.0 and
               r["metrics"]["crossing_GHz"] and r["metrics"]["crossing_GHz"] >= 18.5 and
               r["metrics"]["ripple_20_25GHz_dB"] <= 1.0]
    best_s11 = min(met_all, key=lambda x: x["metrics"]["S11_worst_19_25GHz_dB"]) if met_all else None

    if best_s11:
        bm = best_s11["metrics"]
        improved = bm["S11_worst_19_25GHz_dB"] < REF024["S11_worst_19_25GHz_dB"]
        ref_str = (f"最优 S11 case: {best_s11['uid']} (L4_g4=L2_g4={best_s11['L4_g4185g']}mm), "
                   f"S11w={bm['S11_worst_19_25GHz_dB']:.1f}dB "
                   f"({'改善 ' + str(round(bm['S11_worst_19_25GHz_dB']-REF024['S11_worst_19_25GHz_dB'],1)) + 'dB' if improved else '未改善'})。")
        nxt = "若改善显著，以此为新基点做 L4_g4/L2_g4 独立扫参或精细扫参。" if improved else \
              "L4_g4/L2_g4 对 S11 影响有限，下一步考虑 l_line185g 或 kong185G 调匹配。"
    else:
        ref_str = "所有 case 满足主目标（S31/crossing/ripple），但 S11w 未见明显改善。"
        nxt = "考虑其他 S11 调匹配参数：l_line185g 线长或 kong185G 间隙扫参。"

    section = f"""
## Round 9 — refine9：L4_g4/L2_g4 匹配 stub 扫参（S11 改善）

**基准**：024  S11w = {REF024['S11_worst_19_25GHz_dB']:.1f} dB  目标：< −10 dB

### 结果汇总

| UID | L4_g4=L2_g4 | 交叉 GHz | S31@19 dB | S31@20 dB | 波纹 dB | S11w dB |
|---|---|---|---|---|---|---|
| 024（ref） | 0.501 | 18.535 ✓ | −10.1 ✓ | −11.9 | 0.56 | −7.2 |
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
    print("TUNING_LOG updated (refine9).")

    if best_s11 and best_s11["metrics"]["S11_worst_19_25GHz_dB"] < REF024["S11_worst_19_25GHz_dB"]:
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

    HDR = f"{'UID':>4} {'g4':>5} {'Cross':>7} {'S31@19':>7} {'S31@20':>7} {'Rpl25':>6} {'S11w':>6} {'S11@20':>7} {'S11@25':>7} {'S11@28':>7}"
    print(HDR); print("-"*len(HDR))
    ref = REF024
    fc_s = f"{ref['crossing_GHz']:.3f}"
    print(f"{'024':>4} {'0.501':>5} {fc_s:>7} {ref['S31_at_19GHz_dB']:>7.1f} {ref['S31_at_20GHz_dB']:>7.1f} {ref['ripple_20_25GHz_dB']:>6.2f} {ref['S11_worst_19_25GHz_dB']:>6.1f}   (ref)")
    print("-"*len(HDR))

    results = []
    for c in cases:
        s3p = Path(c["run_dir"]) / "result.s3p"
        if not s3p.exists(): results.append({**c, "metrics": None}); continue
        fr, s11, s21, s31 = parse_s3p(s3p)
        m = compute_metrics(fr, s11, s21, s31)
        results.append({**c, "metrics": m})
        fc = m["crossing_GHz"]
        fc_s = f"{fc:.3f}" if fc else "  n/a "
        ok19 = "✓" if m["S31_at_19GHz_dB"] <= -10.0 else "✗"
        star = " ★" if (fc and fc >= 18.5 and m["S31_at_19GHz_dB"] <= -10.0 and m["S11_worst_19_25GHz_dB"] <= -10.0) else ""
        print(f"{c['uid']:>4} {c['L4_g4185g']:>5.3f} {fc_s:>7}"
              f" {m['S31_at_19GHz_dB']:>7.1f}{ok19}"
              f" {m['S31_at_20GHz_dB']:>7.1f} {m['ripple_20_25GHz_dB']:>6.2f}"
              f" {m['S11_worst_19_25GHz_dB']:>6.1f} {m['S11_at_20GHz_dB']:>7.1f}"
              f" {m['S11_at_25GHz_dB']:>7.1f} {m['S11_at_28GHz_dB']:>7.1f}{star}")
        make_html(c["run_dir"], fr, s11, s21, s31, m,
                  f"[{c['uid']}] L4_g4=L2_g4={c['L4_g4185g']}mm  S11w={m['S11_worst_19_25GHz_dB']:.1f}dB")

    update_log(results)


if __name__ == "__main__":
    main()
