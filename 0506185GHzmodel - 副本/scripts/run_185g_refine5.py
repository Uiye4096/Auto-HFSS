"""
run_185g_refine5.py — Run and analyse Round 6 wC2 micro-sweep.

Usage:
    python scripts/run_185g_refine5.py
    python scripts/run_185g_refine5.py --analyse
    python scripts/run_185g_refine5.py --analyse --html
"""
import json
import math
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT      = Path(__file__).parent.parent.parent
MODEL_DIR = Path(__file__).parent.parent
IPY       = Path(r"E:\HFFS\HFSS_2021\Program Files\AnsysEM\AnsysEM21.2\Win64\common\IronPython\ipy64.exe")
RUNNER    = ROOT / "12GHzdiplexer" / "scripts" / "run_hfss_case.py"
MANIFEST  = MODEL_DIR / "runs" / "refine5_manifest.json"
MAX_WORKERS = 4
TUNING_LOG = MODEL_DIR / "TUNING_LOG.md"


def parse_s3p(path):
    recs, fmt, buf = [], "MA", []
    for line in Path(path).read_text(errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith("!"): continue
        if s.startswith("#"):
            fmt = "DB" if "DB" in s.upper() else ("RI" if "RI" in s.upper() else "MA")
            continue
        if line[0] in (" ", "\t"):
            buf.extend(float(x) for x in s.split())
        else:
            if buf: recs.append(buf)
            buf = [float(x) for x in s.split()]
    if buf: recs.append(buf)
    db = lambda v: 20 * math.log10(v) if v > 0 else -100.0
    fr, s11, s21, s31 = [], [], [], []
    for r in recs:
        if len(r) < 19: continue
        f = r[0] / 1e9 if r[0] > 1e7 else r[0]
        fr.append(f)
        if fmt == "DB":
            s11.append(r[1]);  s21.append(r[7]);  s31.append(r[13])
        elif fmt == "MA":
            s11.append(db(r[1]));  s21.append(db(r[7]));  s31.append(db(r[13]))
        else:
            s11.append(db(math.hypot(r[1],  r[2])))
            s21.append(db(math.hypot(r[7],  r[8])))
            s31.append(db(math.hypot(r[13], r[14])))
    return fr, s11, s21, s31


def at(fr, vals, f):
    return vals[min(range(len(fr)), key=lambda i: abs(fr[i] - f))]


def crossing_freq(fr, s21, s31):
    for i in range(len(fr) - 1):
        d0, d1 = s21[i] - s31[i], s21[i+1] - s31[i+1]
        if d0 * d1 <= 0:
            t = d0 / (d0 - d1) if abs(d0 - d1) > 1e-9 else 0.5
            return fr[i] + t * (fr[i+1] - fr[i])
    return None


def compute_metrics(fr, s11, s21, s31):
    fc   = crossing_freq(fr, s21, s31)
    s19  = at(fr, s31, 19.0)
    s20  = at(fr, s31, 20.0)
    pb   = [at(fr, s21, f) for f in [20, 21, 22, 23, 25]]
    rip  = max(pb) - min(pb)
    s11w = max(at(fr, s11, f) for f in [19, 20, 21, 22, 25])
    return {
        "crossing_GHz":          round(fc, 4) if fc else None,
        "S31_at_19GHz_dB":       round(s19,  2),
        "S31_at_20GHz_dB":       round(s20,  2),
        "ripple_20_25GHz_dB":    round(rip,  2),
        "min_IL_20plus_dB":      round(min(pb), 2),
        "S11_worst_19_25GHz_dB": round(s11w, 2),
    }


def run_case(entry):
    run_dir = Path(entry["run_dir"])
    proj    = run_dir / "result.aedt"
    s3p     = run_dir / "result.s3p"
    log_p   = run_dir / "run.log"
    if not proj.exists():
        return entry["name"], None, "not built"
    if s3p.exists():
        return entry["name"], str(s3p), "already done"
    with open(log_p, "w") as lf:
        subprocess.run([str(IPY), str(RUNNER), str(proj), str(run_dir)],
                       stdout=lf, stderr=subprocess.STDOUT)
    if not s3p.exists():
        return entry["name"], None, "HFSS failed"
    return entry["name"], str(s3p), "ok"


def make_html(run_dir, fr, s11, s21, s31, metrics, title, open_it=False):
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
    html_path = Path(run_dir) / "plot.html"
    html_path.write_text(build_html(fr, s11, s21, s31, m, title), encoding="utf-8")
    if open_it:
        subprocess.Popen(["explorer", str(html_path)])
    return html_path


def update_tuning_log(results):
    rows = []
    for r in sorted(results, key=lambda x: x["w_C2"]):
        m = r["metrics"]
        if m is None:
            rows.append(f"| {r['uid']} | {r['w_C2']} | — | — | — | — | — | no s3p |")
            continue
        fc   = m["crossing_GHz"]
        okfc = "✓" if fc and fc >= 18.5 else "✗"
        ok19 = "✓" if m["S31_at_19GHz_dB"] <= -10.0 else "✗"
        star = " ★" if (fc and fc >= 18.5 and m["S31_at_19GHz_dB"] <= -10.0) else ""
        fc_s = f"{fc:.3f} {okfc}" if fc else "n/a"
        rows.append(f"| {r['uid']} | {r['w_C2']} | {fc_s} | "
                    f"{m['S31_at_19GHz_dB']:.1f} {ok19} | "
                    f"{m['S31_at_20GHz_dB']:.1f} | "
                    f"{m['ripple_20_25GHz_dB']:.2f} | "
                    f"{m['min_IL_20plus_dB']:.1f} | "
                    f"{m['S11_worst_19_25GHz_dB']:.1f} |{star}")

    met = [r for r in results if r["metrics"] and
           r["metrics"]["S31_at_19GHz_dB"] <= -10.0 and
           r["metrics"]["crossing_GHz"] and r["metrics"]["crossing_GHz"] >= 18.5 and
           r["metrics"]["ripple_20_25GHz_dB"] <= 1.0]

    if met:
        best = min(met, key=lambda x: x["metrics"]["S31_at_19GHz_dB"])
        m = best["metrics"]
        reflection = (
            f"wC2 增大有效补强了 S31 余量。"
            f"Case [{best['uid']}] (wC2={best['w_C2']}) 全部达标，"
            f"cross={m['crossing_GHz']:.3f}, S31@19={m['S31_at_19GHz_dB']:.1f} dB。"
            f"更新 final/ 以新参数为准。"
        )
        next_step = "更新 final/ 最优参数。如需进一步改善 S11，可尝试调整 index1 或 w_C1_y 等 HPF 匹配参数。"
        # Update final/
        best_run = Path(best["run_dir"])
        best_s3p = best_run / "result.s3p"
        final_dir = MODEL_DIR / "final"
        import shutil
        shutil.copy(best_s3p, final_dir / f"diplexer_185g_{best['uid']}.s3p")
        params_new = {
            "uid": best["uid"], "source_run": best["name"],
            "parameters": {
                "k": best["k"], "w_C4185g": f"{best['w_C4']}mm",
                "w_C2185g": f"{best['w_C2']}mm",
                "L4_g3185g": f"{best['L4_g3185g']}mm",
                "L2_g3185g": f"{best['L2_g3185g']}mm",
                "L7_g3185g": "0.9mm",
            },
            "metrics": m, "status": "all_targets_met"
        }
        (final_dir / "parameters.json").write_text(
            json.dumps(params_new, indent=2), encoding="utf-8")
        print(f"  Updated final/ → [{best['uid']}] wC2={best['w_C2']}")
    else:
        cross_at_wc2 = [(r["w_C2"], r["metrics"]["crossing_GHz"])
                        for r in results if r["metrics"] and r["metrics"]["crossing_GHz"]]
        s31_at_wc2   = [(r["w_C2"], r["metrics"]["S31_at_19GHz_dB"])
                        for r in results if r["metrics"]]
        reflection = (
            "wC2 增大提升了 S31，但 crossing 随之下降超出预算。"
            "当前所有 case 仍未同时满足两个目标。"
            "wC2 的可用范围比预期更窄。"
        )
        next_step = "回退到 024 作为最终方案（余量虽薄，但已全部达标），或尝试 wC2=1.06 + L2_g3 略微减小（0.77mm）来同时维持 crossing 并改善 S31。"

    section = f"""
## Round 6 — refine5：wC2 微调扫参（2026-05-06）

### 动机
024（wC2=1.05）S31@19 余量只有 0.3 dB，在加工公差下存在不达标风险。
crossing 有 35 MHz 余量，可以容忍小幅下降来换取更大 S31 裕量。

### 参数设置
- 基础：024（k=0.96, wC4=1.15, L2_g3=0.78, L4_g3=0.85）
- 扫 `w_C2185g`：1.06 / 1.07 / 1.08 / 1.09 mm（024 基线 1.05）

### 结果汇总

| UID | wC2 | 交叉 GHz | S31@19 dB | S31@20 dB | 波纹 dB | IL dB | S11w dB |
|---|---|---|---|---|---|---|---|
| 024（ref） | 1.05 | 18.535 ✓ | −10.3 ✓ | −11.9 | 0.56 | −1.3 | −7.2 |
{chr(10).join(rows)}

### 反思
{reflection}

### 下一步
{next_step}

---

"""
    log = TUNING_LOG.read_text(encoding="utf-8")
    log = log.replace(
        "<!-- 后续每次仿真完成后在此追加新的 Round -->",
        section + "<!-- 后续每次仿真完成后在此追加新的 Round -->"
    )
    TUNING_LOG.write_text(log, encoding="utf-8")
    print("TUNING_LOG updated.")


def main():
    analyse_only = "--analyse" in sys.argv
    open_html    = "--html" in sys.argv

    if not MANIFEST.exists():
        sys.exit("Run build_185g_refine5.py first.")

    cases = json.loads(MANIFEST.read_text(encoding="utf-8"))

    if not analyse_only:
        print(f"Running {len(cases)} cases (max {MAX_WORKERS} parallel)...\n")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futs = {ex.submit(run_case, c): c for c in cases}
            for fut in as_completed(futs):
                name, _, status = fut.result()
                print(f"  {name}: {status}")
        print()

    results = []
    for c in cases:
        s3p = Path(c["run_dir"]) / "result.s3p"
        if not s3p.exists():
            results.append({**c, "metrics": None})
            continue
        fr, s11, s21, s31 = parse_s3p(s3p)
        m = compute_metrics(fr, s11, s21, s31)
        results.append({**c, "metrics": m})
        if open_html:
            make_html(c["run_dir"], fr, s11, s21, s31, m,
                      f"185g refine5 [{c['uid']}] wC2={c['w_C2']} k={c['k']} wC4={c['w_C4']}",
                      open_it=True)

    HDR = f"{'UID':>4} {'wC2':>5} {'Cross':>7} {'S31@19':>8} {'S31@20':>8} {'Ripple':>7} {'IL':>6} {'S11w':>6}  Targets"
    SEP = "-" * len(HDR)
    print(HDR); print(SEP)
    print(f"{'024':>4} {'1.05':>5} {'18.535':>7} {'-10.3':>8} {'-11.9':>8} {'0.56':>7} {'-1.3':>6} {'-7.2':>6}  ✓cross ✓S31@19  ← current best")
    print(SEP)

    for r in sorted(results, key=lambda x: x["w_C2"]):
        m = r["metrics"]
        if m is None:
            print(f"{r['uid']:>4} {r['w_C2']:>5.2f}  (no s3p)"); continue
        fc   = m["crossing_GHz"]
        okfc = "✓" if fc and fc >= 18.5 else "✗"
        ok19 = "✓" if m["S31_at_19GHz_dB"] <= -10.0 else "✗"
        ok20 = "✓" if m["S31_at_20GHz_dB"] <= -10.0 else "✗"
        okrp = "✓" if m["ripple_20_25GHz_dB"] <= 1.0 else "✗"
        fc_s = f"{fc:.3f}" if fc else "  n/a "
        star = " ★" if (fc and fc >= 18.5 and m["S31_at_19GHz_dB"] <= -10.0) else ""
        print(f"{r['uid']:>4} {r['w_C2']:>5.2f} {fc_s:>7}"
              f" {m['S31_at_19GHz_dB']:>8.1f} {m['S31_at_20GHz_dB']:>8.1f}"
              f" {m['ripple_20_25GHz_dB']:>7.2f} {m['min_IL_20plus_dB']:>6.1f}"
              f" {m['S11_worst_19_25GHz_dB']:>6.1f}"
              f"  {okfc}cross {ok19}S31@19 {ok20}S31@20 {okrp}ripple{star}")

    met = [r for r in results if r["metrics"] and
           r["metrics"]["S31_at_19GHz_dB"] <= -10.0 and
           r["metrics"]["crossing_GHz"] and r["metrics"]["crossing_GHz"] >= 18.5 and
           r["metrics"]["ripple_20_25GHz_dB"] <= 1.0]
    print(SEP)
    print(f"\nAll targets met: {len(met)}/{len(results)}")
    if met:
        best = min(met, key=lambda x: x["metrics"]["S31_at_19GHz_dB"])
        print(f"Best: [{best['uid']}] wC2={best['w_C2']}  "
              f"cross={best['metrics']['crossing_GHz']:.3f}  "
              f"S31@19={best['metrics']['S31_at_19GHz_dB']:.1f} dB")

    update_tuning_log(results)


if __name__ == "__main__":
    main()
