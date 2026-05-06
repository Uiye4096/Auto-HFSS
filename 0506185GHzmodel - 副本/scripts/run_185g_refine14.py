"""run_185g_refine14.py — Round 14: w_C2185g sweep on 090 base."""
import json, math, subprocess, sys, shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT       = Path(__file__).parent.parent.parent
MODEL_DIR  = Path(__file__).parent.parent
IPY        = Path(r"E:\HFFS\HFSS_2021\Program Files\AnsysEM\AnsysEM21.2\Win64\common\IronPython\ipy64.exe")
RUNNER     = ROOT / "12GHzdiplexer" / "scripts" / "run_hfss_case.py"
MANIFEST   = MODEL_DIR / "runs" / "refine14_manifest.json"
TUNING_LOG = MODEL_DIR / "TUNING_LOG.md"
MAX_WORKERS = 4
F_MAX = 30.0

REF090 = {"uid":"090","w_C2":1.05,"crossing_GHz":18.534,
          "S31_at_19GHz_dB":-8.2,"S31_at_20GHz_dB":-12.1,
          "ripple_20_25GHz_dB":0.56,"S11_worst_19_25GHz_dB":-9.4}
REF024 = {"uid":"024","S11_worst_19_25GHz_dB":-7.2}

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
def crossing_freq(fr, s21, s31):
    for i in range(len(fr)-1):
        d0, d1 = s21[i]-s31[i], s21[i+1]-s31[i+1]
        if d0*d1 <= 0:
            t = d0/(d0-d1) if abs(d0-d1) > 1e-9 else 0.5
            return fr[i]+t*(fr[i+1]-fr[i])
    return None

def compute_metrics(fr, s11, s21, s31):
    fc  = crossing_freq(fr, s21, s31)
    pb  = [at(fr, s21, f) for f in [20, 21, 22, 23, 25]]
    s19 = at(fr, s31, 19.0)
    stop_pts = [i for i in range(len(fr)) if 18.5 <= fr[i] <= 28.5]
    s31_stop = max((s31[i] for i in stop_pts), default=s19) if stop_pts else s19
    return {
        "crossing_GHz":          round(fc, 4) if fc else None,
        "S31_at_19GHz_dB":       round(s19, 2),
        "S31_at_20GHz_dB":       round(at(fr, s31, 20.0), 2),
        "S31_worst_stop_dB":     round(s31_stop, 2),
        "ripple_20_25GHz_dB":    round(max(pb)-min(pb), 2),
        "min_IL_20plus_dB":      round(min(pb), 2),
        "S11_worst_19_25GHz_dB": round(max(at(fr, s11, f) for f in [19, 20, 21, 22, 25]), 2),
        "S11_at_20GHz_dB":       round(at(fr, s11, 20.0), 2),
        "S11_at_25GHz_dB":       round(at(fr, s11, 25.0), 2),
        "S11_at_28GHz_dB":       round(at(fr, s11, 28.0), 2),
    }

def run_case(entry):
    rd = Path(entry["run_dir"]); proj = rd/"result.aedt"; s3p = rd/"result.s3p"
    if not proj.exists(): return entry["name"], None, "not built"
    if s3p.exists():      return entry["name"], str(s3p), "already done"
    with open(rd/"run.log", "w") as lf:
        subprocess.run([str(IPY), str(RUNNER), str(proj), str(rd)], stdout=lf, stderr=subprocess.STDOUT)
    return entry["name"], str(s3p) if s3p.exists() else None, "ok" if s3p.exists() else "HFSS failed"

def make_html(run_dir, fr, s11, s21, s31, metrics, title):
    sys.path.insert(0, str(ROOT))
    from plot_interactive import build_html
    m = dict(metrics); fc = m.get("crossing_GHz")
    m.setdefault("targets_met", {
        "crossing_ge_18p5GHz":     bool(fc and fc >= 18.5),
        "S31_at_19_le_neg10dB":    m["S31_at_19GHz_dB"] <= -10.0,
        "S31_worst_stop_le_neg10": m["S31_worst_stop_dB"] <= -10.0,
        "S31_at_20_le_neg10dB":    m["S31_at_20GHz_dB"] <= -10.0,
        "ripple_20_25GHz_le_1dB":  m["ripple_20_25GHz_dB"] <= 1.0,
    })
    hp = Path(run_dir)/"plot_30g.html"
    hp.write_text(build_html(fr, s11, s21, s31, m, title), encoding="utf-8")
    return hp

def update_log(results):
    rows = []
    for r in sorted(results, key=lambda x: x["w_C2"]):
        m = r["metrics"]
        if m is None: rows.append(f"| {r['uid']} | {r['w_C2']} | — | — | — | — | no s3p |"); continue
        fc = m["crossing_GHz"]; fc_s = f"{fc:.3f}" if fc else "n/a"
        ok_fc  = "✓" if fc and fc >= 18.5 else "✗"
        ok_s11 = "★" if m["S11_worst_19_25GHz_dB"] <= -10.0 else ("✗" if m["S11_worst_19_25GHz_dB"] > -9.0 else "△")
        rows.append(f"| {r['uid']} | {r['w_C2']:.2f} | {fc_s} {ok_fc} | {m['S31_at_19GHz_dB']:.1f} | {m['S31_at_20GHz_dB']:.1f} | {m['ripple_20_25GHz_dB']:.2f} | {m['S11_worst_19_25GHz_dB']:.1f} {ok_s11} |")

    candidates = [r for r in results if r["metrics"] and r["metrics"]["crossing_GHz"]
                  and r["metrics"]["crossing_GHz"] >= 18.5 and r["metrics"]["ripple_20_25GHz_dB"] <= 1.0]
    best = min(candidates, key=lambda x: x["metrics"]["S11_worst_19_25GHz_dB"]) if candidates else None

    if best:
        bm = best["metrics"]
        delta = round(bm["S11_worst_19_25GHz_dB"] - REF090["S11_worst_19_25GHz_dB"], 1)
        broke = bm["S11_worst_19_25GHz_dB"] <= -10.0
        ref_str = (f"突破！{best['uid']} (wC2={best['w_C2']:.2f}mm): S11w={bm['S11_worst_19_25GHz_dB']:.1f} dB ≤ −10 dB ★" if broke else
                   f"最优：{best['uid']} (wC2={best['w_C2']:.2f}mm) S11w={bm['S11_worst_19_25GHz_dB']:.1f} dB（vs 090 变化 {delta:+.1f} dB）。")
        nxt = ("将此 case 确立为 final，已全部达标！" if broke else
               f"wC2={best['w_C2']:.2f}mm 是局部最优。下一步尝试同时扫 wC4（对称性）或 k 值微调。")
    else:
        ref_str = "无满足约束的 case。"; nxt = "扩大扫参范围。"

    section = f"""
## Round 14 — refine14：w_C2185g 扫参（090 base，攻克 S11 ≤ −10 dB）

**090 base**：L7_g3=0.83, L7_g4=0.50, wC2=1.05mm  S11w=−9.4 dB

### 结果汇总

| UID | wC2 | 交叉 GHz | S31@19 | S31@20 | 波纹 | S11w |
|---|---|---|---|---|---|---|
| 090（ref） | 1.05 | 18.534 ✓ | −8.2 | −12.1 | 0.56 | −9.4 △ |
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
    print("TUNING_LOG updated (refine14).")

    if best and best["metrics"]["S11_worst_19_25GHz_dB"] <= REF024["S11_worst_19_25GHz_dB"]:
        s3p = Path(best["run_dir"]) / "result.s3p"
        if s3p.exists():
            shutil.copy(s3p, MODEL_DIR/"final"/f"diplexer_185g_{best['uid']}.s3p")
            (MODEL_DIR/"final"/"parameters.json").write_text(
                json.dumps({"uid": best["uid"], "metrics": best["metrics"],
                            "L7_g3185g": 0.83, "L7_g4185g": 0.50, "w_C2185g": best["w_C2"],
                            "status": "new_best_S11"}, indent=2), encoding="utf-8")
            print(f"  final/ updated → [{best['uid']}]")

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

    HDR = f"{'UID':>4} {'wC2':>5} {'Cross':>7} {'S31@19':>7} {'S31@20':>7} {'Rpl25':>6} {'S11w':>6} {'S11@20':>6} {'S11@25':>6} {'S11@28':>6}"
    print(HDR); print("-"*len(HDR))
    r = REF090
    print(f"{'090':>4} {'1.05':>5} {r['crossing_GHz']:>7.3f} {r['S31_at_19GHz_dB']:>7.1f} {r['S31_at_20GHz_dB']:>7.1f} {r['ripple_20_25GHz_dB']:>6.2f} {r['S11_worst_19_25GHz_dB']:>6.1f}  (ref)")
    print("-"*len(HDR))

    results = []
    for c in sorted(cases, key=lambda x: x["w_C2"]):
        s3p = Path(c["run_dir"]) / "result.s3p"
        if not s3p.exists(): results.append({**c, "metrics": None}); continue
        fr, s11, s21, s31 = parse_s3p(s3p)
        m = compute_metrics(fr, s11, s21, s31)
        results.append({**c, "metrics": m})
        fc = m["crossing_GHz"]; fc_s = f"{fc:.3f}" if fc else "  n/a "
        ok_s11 = "★" if m["S11_worst_19_25GHz_dB"] <= -10.0 else "✗"
        star = " ★★" if (fc and fc >= 18.5 and m["S31_at_20GHz_dB"] <= -10.0
                         and m["ripple_20_25GHz_dB"] <= 1.0
                         and m["S11_worst_19_25GHz_dB"] <= -10.0) else ""
        print(f"{c['uid']:>4} {c['w_C2']:>5.2f} {fc_s:>7}"
              f" {m['S31_at_19GHz_dB']:>7.1f} {m['S31_at_20GHz_dB']:>7.1f}"
              f" {m['ripple_20_25GHz_dB']:>6.2f} {m['S11_worst_19_25GHz_dB']:>6.1f}{ok_s11}"
              f" {m['S11_at_20GHz_dB']:>6.1f} {m['S11_at_25GHz_dB']:>6.1f} {m['S11_at_28GHz_dB']:>6.1f}{star}")
        make_html(c["run_dir"], fr, s11, s21, s31, m,
                  f"[{c['uid']}] wC2={c['w_C2']:.2f}  S11w={m['S11_worst_19_25GHz_dB']:.1f}dB")

    update_log(results)
    winners = [r for r in results if r["metrics"] and r["metrics"]["S11_worst_19_25GHz_dB"] <= -10.0]
    if winners:
        print(f"\n{'='*60}")
        print("  ★ S11w ≤ −10 dB ACHIEVED!")
        for w in sorted(winners, key=lambda x: x["metrics"]["S11_worst_19_25GHz_dB"]):
            print(f"    [{w['uid']}] wC2={w['w_C2']:.2f}  S11w={w['metrics']['S11_worst_19_25GHz_dB']:.1f} dB")
        print(f"{'='*60}")

if __name__ == "__main__": main()
