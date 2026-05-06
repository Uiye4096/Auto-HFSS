"""
run_185g_refine4.py — Run and analyse Round 5 L4_g3 sweep.

Usage:
    python scripts/run_185g_refine4.py
    python scripts/run_185g_refine4.py --analyse
    python scripts/run_185g_refine4.py --analyse --html
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
MANIFEST  = MODEL_DIR / "runs" / "refine4_manifest.json"
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
    """Append Round 5 results + reflection to TUNING_LOG.md."""
    rows = []
    for r in sorted(results, key=lambda x: x["L4_g3185g"]):
        m = r["metrics"]
        if m is None:
            rows.append(f"| {r['uid']} | {r['L4_g3185g']} | — | — | — | — | — | no s3p |")
            continue
        fc   = m["crossing_GHz"]
        okfc = "✓" if fc and fc >= 18.5 else "✗"
        ok19 = "✓" if m["S31_at_19GHz_dB"] <= -10.0 else "✗"
        star = " ★" if (fc and fc >= 18.5 and m["S31_at_19GHz_dB"] <= -10.0) else ""
        rows.append(f"| {r['uid']} | {r['L4_g3185g']} | "
                    f"{fc:.3f} {okfc} | "
                    f"{m['S31_at_19GHz_dB']:.1f} {ok19} | "
                    f"{m['S31_at_20GHz_dB']:.1f} | "
                    f"{m['ripple_20_25GHz_dB']:.2f} | "
                    f"{m['min_IL_20plus_dB']:.1f} |{star}")

    met = [r for r in results if r["metrics"] and
           r["metrics"]["S31_at_19GHz_dB"] <= -10.0 and
           r["metrics"]["crossing_GHz"] and r["metrics"]["crossing_GHz"] >= 18.5 and
           r["metrics"]["ripple_20_25GHz_dB"] <= 1.0]

    # Determine reflection
    if met:
        best = min(met, key=lambda x: x["metrics"]["S31_at_19GHz_dB"])
        m = best["metrics"]
        reflection = (
            f"**假设成立**：L4_g3 独立提升 crossing。"
            f"Case [{best['uid']}] (L4_g3={best['L4_g3185g']}) 全部达标，"
            f"cross={m['crossing_GHz']:.3f}, S31@19={m['S31_at_19GHz_dB']:.1f} dB，"
            f"较 024 有更大余量。更新 final/ 推荐此参数。"
        )
        next_step = "将 best case 参数保存到 final/，进一步微调 L4_g3 和 L2_g3 的组合，探索最大余量点。"
    else:
        # Check if crossing improved at all
        cross_vals = [(r["L4_g3185g"], r["metrics"]["crossing_GHz"])
                      for r in results if r["metrics"]]
        if cross_vals:
            min_l4, max_cross = min(cross_vals, key=lambda x: x[0])
            max_l4, min_cross = max(cross_vals, key=lambda x: x[0])
            delta = (max_cross or 0) - (min_cross or 0) if max_cross and min_cross else 0
            if delta > 50:
                reflection = (
                    f"**假设部分成立**：L4_g3 减小使 crossing 提升 ~{delta:.0f} MHz，"
                    f"但同时影响 S31，两个目标仍未同时满足。"
                    f"最近候选：crossing 或 S31 接近边界，下一步细化。"
                )
                next_step = "在 L4_g3 最优点附近细插值，同时微调 L2_g3（0.79–0.81）进行 2D 精细扫描，寻找同时满足两个目标的组合。"
            else:
                reflection = (
                    "L4_g3 减小对 crossing 影响有限，说明两个 HPF stub 相互耦合较强。"
                    "单独调 L4_g3 无法脱离 L2_g3 的约束独立推高 crossing。"
                )
                next_step = "转向 wC2 微调（1.05→1.08）配合 024 的 L2_g3=0.78，探索能否用更大的 wC2 补回 0.7 dB S31 余量，同时 L2_g3 小幅减小来维持 crossing。"
        else:
            reflection = "所有 case 仿真失败，检查 HFSS 路径和参数。"
            next_step = "排查仿真失败原因。"

    section = f"""
## Round 5 — refine4：L4_g3185g 扫参（结果）

### 结果汇总

| UID | L4_g3 | 交叉 GHz | S31@19 dB | S31@20 dB | 波纹 dB | IL dB |
|---|---|---|---|---|---|---|
| 025（ref） | 0.81（L2_g3=0.81）| 18.383 ✗ | −11.3 ✓ | −11.0 | 0.62 | −1.5 |
| 024（ref） | 0.85（L2_g3=0.78）| 18.535 ✓ | −10.3 ✓ | −11.9 | 0.56 | −1.3 |
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
    print(f"\nTUNING_LOG updated.")


def main():
    analyse_only = "--analyse" in sys.argv
    open_html    = "--html" in sys.argv

    if not MANIFEST.exists():
        sys.exit("Run build_185g_refine4.py first.")

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
                      f"185g refine4 [{c['uid']}] L4_g3={c['L4_g3185g']} L2_g3={c['L2_g3185g']}",
                      open_it=True)

    HDR = f"{'UID':>4} {'L4g3':>5} {'Cross':>7} {'S31@19':>8} {'S31@20':>8} {'Ripple':>7} {'IL':>6} {'S11w':>6}  Targets"
    SEP = "-" * len(HDR)
    print(HDR); print(SEP)
    print(f"{'025':>4} {'0.85':>5} {'18.383':>7} {'-11.3':>8} {'-11.0':>8} {'0.62':>7} {'-1.5':>6} {'-7.4':>6}  ✗cross ✓S31@19  ← L2g3=0.81 base")
    print(f"{'024':>4} {'0.85':>5} {'18.535':>7} {'-10.3':>8} {'-11.9':>8} {'0.56':>7} {'-1.3':>6} {'-7.2':>6}  ✓cross ✓S31@19  ← current best")
    print(SEP)

    for r in sorted(results, key=lambda x: x["L4_g3185g"]):
        m = r["metrics"]
        if m is None:
            print(f"{r['uid']:>4} {r['L4_g3185g']:>5.2f}  (no s3p)"); continue
        fc   = m["crossing_GHz"]
        okfc = "✓" if fc and fc >= 18.5 else "✗"
        ok19 = "✓" if m["S31_at_19GHz_dB"] <= -10.0 else "✗"
        ok20 = "✓" if m["S31_at_20GHz_dB"] <= -10.0 else "✗"
        okrp = "✓" if m["ripple_20_25GHz_dB"] <= 1.0 else "✗"
        fc_s = f"{fc:.3f}" if fc else "  n/a "
        star = " ★" if (fc and fc >= 18.5 and m["S31_at_19GHz_dB"] <= -10.0) else ""
        print(f"{r['uid']:>4} {r['L4_g3185g']:>5.2f} {fc_s:>7}"
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
        print(f"Best: [{best['uid']}] L4_g3={best['L4_g3185g']}  "
              f"cross={best['metrics']['crossing_GHz']:.3f}  "
              f"S31@19={best['metrics']['S31_at_19GHz_dB']:.1f} dB")

    update_tuning_log(results)


if __name__ == "__main__":
    main()
