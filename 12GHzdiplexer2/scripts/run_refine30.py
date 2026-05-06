"""Run refine30 — 185g LPF redistribution + k-scaling to hit 18.5+ GHz."""
import json
import math
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT     = Path(r"D:\Desktop\HFSS_real")
OUT_ROOT = ROOT / "12GHzdiplexer2" / "derived" / "refine30"
RUNNER   = ROOT / "12GHzdiplexer" / "scripts" / "run_hfss_case.py"
PLOT     = ROOT / "tools" / "plot_s3p.py"
IPY      = r"E:\HFFS\HFSS_2021\Program Files\AnsysEM\AnsysEM21.2\Win64\common\IronPython\ipy64.exe"

MAX_WORKERS = 4
print_lock  = threading.Lock()


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
    fr, s11, s21, s31 = [], [], [], []
    for r in recs:
        if len(r) < 19: continue
        f = r[0] / 1e9 if r[0] > 1e7 else r[0]
        fr.append(f)
        db = lambda v: 20 * math.log10(v) if v > 0 else -100
        if fmt == "DB":
            s11.append(r[1]); s21.append(r[7]); s31.append(r[13])
        elif fmt == "MA":
            s11.append(db(r[1])); s21.append(db(r[7])); s31.append(db(r[13]))
        else:
            s11.append(db(math.hypot(r[1], r[2])))
            s21.append(db(math.hypot(r[7], r[8])))
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


def metrics(fr, s11, s21, s31):
    fc    = crossing_freq(fr, s21, s31)
    s19   = at(fr, s31, 19.0)
    s20   = at(fr, s31, 20.0)
    pb25  = [at(fr, s21, f) for f in [20, 21, 22, 23, 25]]
    rip25 = max(pb25) - min(pb25)
    hil   = min(pb25)
    s11w  = max(at(fr, s11, f) for f in [19, 20, 21, 22, 25])
    return fc, s19, s20, hil, rip25, s11w


def run_one(item):
    name = Path(item["project_path"]).stem
    s3p  = Path(item["output_dir"]) / f"{name}.s3p"
    if s3p.exists():
        with print_lock: print(f"  [cached] {item['case']}")
        return item, True
    with print_lock: print(f"  [start ] {item['case']}")
    ret = subprocess.run(
        [IPY, str(RUNNER), item["project_path"], item["output_dir"]],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    ok = ret.returncode == 0 and s3p.exists()
    with print_lock: print(f"  [{'done ' if ok else 'FAIL '}] {item['case']}")
    if ok:
        subprocess.run(
            ["python", str(PLOT), str(s3p), "--open"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    return item, ok


def main():
    manifest = json.loads((OUT_ROOT / "manifest.json").read_text(encoding="utf-8"))
    todo   = [it for it in manifest
              if not (Path(it["output_dir"]) /
                      f"{Path(it['project_path']).stem}.s3p").exists()]
    cached = [it for it in manifest if it not in todo]
    print(f"\n{len(cached)} cached, {len(todo)} to simulate "
          f"({MAX_WORKERS} parallel workers)\n")

    results = {}
    for it in cached:
        name = Path(it["project_path"]).stem
        s3p  = Path(it["output_dir"]) / f"{name}.s3p"
        results[it["case"]] = parse_s3p(s3p)

    if todo:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futs = {ex.submit(run_one, it): it for it in todo}
            for fut in as_completed(futs):
                item, ok = fut.result()
                if ok:
                    name = Path(item["project_path"]).stem
                    s3p  = Path(item["output_dir"]) / f"{name}.s3p"
                    results[item["case"]] = parse_s3p(s3p)

    # ── Summary table ─────────────────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("REFINE30  (185g non-uniform LPF + k-scaling to reach 18.5 GHz crossing)")
    print(f"  {'Case':<38} {'Cross':>8} {'S31@19':>7} {'S31@20':>7} "
          f"{'rip25':>6} {'IL20':>6} {'S11mx':>6}")
    print("-" * 84)

    rows = []
    for it in manifest:
        case = it["case"]
        if case not in results: continue
        fr, s11, s21, s31 = results[case]
        fc, s19, s20, hil, rip25, s11w = metrics(fr, s11, s21, s31)
        rows.append((case, fc, s19, s20, hil, rip25, s11w, fr, s11, s21, s31))

    rows.sort(key=lambda x: -(x[1] or 0))
    for case, fc, s19, s20, hil, rip25, s11w, *_ in rows:
        ok_c  = "✓" if fc  and fc  >= 18.5 else " "
        ok_19 = "✓" if s19 <= -10.0 else " "
        ok_20 = "✓" if s20 <= -10.0 else " "
        ok_r  = "✓" if rip25 <= 1.0  else " "
        fc_s  = f"{fc:.3f}" if fc else " none"
        print(f"  {case:<38} {fc_s:>8}{ok_c} {s19:>6.1f}{ok_19} {s20:>6.1f}{ok_20} "
              f"{rip25:>5.1f}{ok_r} {hil:>5.1f} {s11w:>5.1f}")

    # ── Pareto detail ──────────────────────────────────────────────────────────
    winners = [(rip25, case, fc, s19, s20, hil, s11w, fr, s11, s21, s31)
               for case, fc, s19, s20, hil, rip25, s11w, fr, s11, s21, s31 in rows
               if fc and fc >= 18.5 and s19 <= -10.0 and s20 <= -10.0]
    winners.sort()

    print(f"\nPrior best: r27_c1y022 — cross=18.552  S31@19=-10.8  S31@20=-15.8  rip25=0.6  IL=-3.1")
    print(f"Ref point:  r29_185lpf_wC145_l2075 — cross=18.347  S31@19=-13.5  rip25=1.2\n")
    if winners:
        print("New Pareto front (all criteria ✓):")
        for rip25, case, fc, s19, s20, hil, s11w, fr, s11, s21, s31 in winners[:5]:
            ok_r = "✓" if rip25 <= 1.0 else " "
            print(f"\n  {case}  cross={fc:.3f}✓  S31@19={s19:.1f}✓  rip25={rip25:.1f}{ok_r}  IL={hil:.1f}  S11={s11w:.1f}")
            print(f"    S21: " + "  ".join(f"@{f}={at(fr,s21,f):.1f}"
                                           for f in [18,19,20,21,22,23,25,28,32]))
            print(f"    S31: " + "  ".join(f"@{f}={at(fr,s31,f):.1f}"
                                           for f in [17,18,19,20,21,22]))
            print(f"    S11: " + "  ".join(f"@{f}={at(fr,s11,f):.1f}"
                                           for f in [18,19,20,21,22,25]))
    else:
        print("  (none — closest cases):")
        for case, fc, s19, s20, hil, rip25, s11w, fr, s11, s21, s31 in rows[:4]:
            print(f"\n  {case}  cross={fc:.3f}  S31@19={s19:.1f}  rip25={rip25:.1f}  IL={hil:.1f}")
            print(f"    S21: " + "  ".join(f"@{f}={at(fr,s21,f):.1f}"
                                           for f in [18,19,20,21,22,23,25,28,32]))
            print(f"    S31: " + "  ".join(f"@{f}={at(fr,s31,f):.1f}"
                                           for f in [17,18,19,20,21,22]))

    print("\nAll done.")


if __name__ == "__main__":
    main()
