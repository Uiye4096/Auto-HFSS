"""Run refine24 — BOLD: LPF uniform length scaling. Parallel execution."""
import json
import math
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT     = Path(r"D:\Desktop\HFSS_real")
OUT_ROOT = ROOT / "12GHzdiplexer2" / "derived" / "refine24"
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


def bump_peak(fr, s31):
    region = [(f, v) for f, v in zip(fr, s31) if 18.0 <= f <= 22.0]
    if not region: return None, None
    return max(region, key=lambda x: x[1])


def metrics(fr, s11, s21, s31):
    fc   = crossing_freq(fr, s21, s31)
    pts  = [f for f, v in zip(fr, s31) if v >= -3]
    lpf  = max(pts) if pts else None
    chk  = [19, 20, 21, 22, 23, 25, 28, 32, 36]
    vals = [at(fr, s21, f) for f in chk]
    hil  = min(vals)
    rip  = max(vals) - hil
    f_bk, v_bk = bump_peak(fr, s31)
    return fc, lpf, hil, rip, f_bk, v_bk


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

    # ── Results table ─────────────────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("REFINE24 — LPF SCALING RESULTS  (bold: all LPF lengths × k)")
    print(f"  {'Case':<34} {'wC':>5} {'k':>5} {'Cross':>8} {'S31-3dB':>8} "
          f"{'Bump':>8} {'wrstIL':>8} {'rip':>6}")
    print("-" * 86)

    rows = []
    for it in manifest:
        case = it["case"]
        if case not in results: continue
        fr, s11, s21, s31 = results[case]
        fc, lpf, hil, rip, f_bk, v_bk = metrics(fr, s11, s21, s31)
        wc_raw = it["updates"].get("w_C412g", "0mm")
        wc  = float(wc_raw.replace("mm", ""))
        ll5 = float(it["updates"].get("l_L512g", "0mm").replace("mm", ""))
        k   = round(ll5 / 0.770, 3)
        rows.append((k, wc, case, fc, lpf, hil, rip, f_bk, v_bk,
                     fr, s11, s21, s31))

    rows.sort(key=lambda x: (x[1], x[0]))  # sort by wC then k
    for k, wc, case, fc, lpf, hil, rip, f_bk, v_bk, *_ in rows:
        ok_c = "✓" if fc  and fc  >= 18.5 else " "
        ok_b = "✓" if v_bk is not None and v_bk <= -10.0 else " "
        fc_s  = f"{fc:.3f}"   if fc  else " none"
        lpf_s = f"{lpf:.2f}"  if lpf else " FAIL"
        bk_s  = f"{v_bk:.1f}" if v_bk is not None else " ---"
        print(f"  {case:<34} {wc:>5.1f}  {k:.2f}  {fc_s:>8}{ok_c} {lpf_s:>8} "
              f"{bk_s:>8}{ok_b} {hil:>8.1f} {rip:>6.1f}")

    # ── Top picks ──────────────────────────────────────────────────────────────
    print("\n\nTop picks (crossing≥18.5 GHz):")
    good = sorted(
        [(abs((fc or 0) - 18.5), hil, case, fc, lpf, v_bk, k, wc, fr, s21, s31, s11)
         for k, wc, case, fc, lpf, hil, rip, f_bk, v_bk, fr, s11, s21, s31 in rows
         if fc and fc >= 18.0],
        key=lambda x: (x[0], -x[1])
    )
    if not good:
        print("  (none reached 18.0 GHz — closest cases below:)")
        good = sorted(
            [(abs((fc or 0) - 18.5), hil, case, fc, lpf, v_bk, k, wc, fr, s21, s31, s11)
             for k, wc, case, fc, lpf, hil, rip, f_bk, v_bk, fr, s11, s21, s31 in rows
             if fc],
            key=lambda x: x[0]
        )
    for _, hil, case, fc, lpf, v_bk, k, wc, fr, s21, s31, s11 in good[:6]:
        ok_c  = "✓" if fc >= 18.5 else " "
        ok_b  = "✓" if v_bk is not None and v_bk <= -10 else " "
        lpf_s = f"{lpf:.2f}" if lpf else "FAIL"
        bk_s  = f"{v_bk:.1f}" if v_bk is not None else "---"
        print(f"\n  {case}  k={k:.2f}  wC={wc}  cross={fc:.3f}{ok_c}")
        print(f"    S31-3dB={lpf_s}  bump={bk_s}{ok_b}  IL={hil:.1f}")
        print(f"    S21: " + "  ".join(f"@{f}={at(fr,s21,f):.1f}"
                                       for f in [17, 18, 19, 20, 21, 22, 25, 28]))
        print(f"    S31: " + "  ".join(f"@{f}={at(fr,s31,f):.1f}"
                                       for f in [17, 18, 19, 20, 21, 22]))
        print(f"    S11: " + "  ".join(f"@{f}={at(fr,s11,f):.1f}"
                                       for f in [18, 19, 20, 21, 22]))

    print("\nAll done.")


if __name__ == "__main__":
    main()
