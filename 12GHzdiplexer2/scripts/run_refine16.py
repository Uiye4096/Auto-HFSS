"""Run refine16: idx x c1y 2D sweep."""
import json
import math
import subprocess
from pathlib import Path

ROOT     = Path(r"D:\Desktop\HFSS_real")
OUT_ROOT = ROOT / "12GHzdiplexer2" / "derived" / "refine16"
RUNNER   = ROOT / "12GHzdiplexer" / "scripts" / "run_hfss_case.py"
PLOT     = ROOT / "tools" / "plot_s3p.py"
IPY      = r"E:\HFFS\HFSS_2021\Program Files\AnsysEM\AnsysEM21.2\Win64\common\IronPython\ipy64.exe"


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
    freqs, s11, s21, s31 = [], [], [], []
    for r in recs:
        if len(r) < 19: continue
        f = r[0] / 1e9 if r[0] > 1e7 else r[0]
        freqs.append(f)
        def db(v): return 20 * math.log10(v) if v > 0 else -100
        if fmt == "DB":
            s11.append(r[1]); s21.append(r[7]); s31.append(r[13])
        elif fmt == "MA":
            s11.append(db(r[1])); s21.append(db(r[7])); s31.append(db(r[13]))
        else:
            s11.append(db(math.hypot(r[1], r[2])))
            s21.append(db(math.hypot(r[7], r[8])))
            s31.append(db(math.hypot(r[13], r[14])))
    return freqs, s11, s21, s31


def at(fr, vals, f):
    i = min(range(len(fr)), key=lambda i: abs(fr[i] - f))
    return vals[i]


def crossing(freqs, s21, s31):
    for i in range(len(freqs) - 1):
        d0, d1 = s21[i] - s31[i], s21[i+1] - s31[i+1]
        if d0 * d1 <= 0:
            t = d0 / (d0 - d1) if abs(d0 - d1) > 1e-9 else 0.5
            return freqs[i] + t * (freqs[i+1] - freqs[i])
    return None


def metrics(fr, s11, s21, s31):
    fc   = crossing(fr, s21, s31)
    pts  = [f for f, v in zip(fr, s31) if v >= -3]
    lpf  = max(pts) if pts else None
    chk  = [20, 21, 22, 23, 25, 28, 30, 36]
    vals = [at(fr, s21, f) for f in chk]
    hil  = min(vals)
    rip  = max(vals) - hil
    return fc, lpf, hil, rip


def main():
    manifest = json.loads((OUT_ROOT / "manifest.json").read_text(encoding="utf-8"))
    results  = []
    for item in manifest:
        name = Path(item["project_path"]).stem
        s3p  = Path(item["output_dir"]) / f"{name}.s3p"
        if not s3p.exists():
            ret = subprocess.run(
                [IPY, str(RUNNER), item["project_path"], item["output_dir"]]
            )
            if ret.returncode != 0 or not s3p.exists():
                print(f"  FAIL: {item['case']}"); continue
            subprocess.run(["python", str(PLOT), str(s3p), "--open"])
        fr, s11, s21, s31 = parse_s3p(s3p)
        fc, lpf, hil, rip = metrics(fr, s11, s21, s31)
        upd = item["updates"]
        results.append((upd["index1"], upd["w_C1_y"], fc, lpf, hil, rip, fr, s21, s31, s11))
        ok_c = "✓" if fc  and fc  >= 18.5 else "✗"
        ok_s = "✓" if lpf and lpf >= 18.5 else "✗"
        s21_row = "  ".join(f"@{f}={at(fr,s21,f):.1f}" for f in [19,20,21,22,25,28])
        s11_row = "  ".join(f"@{f}={at(fr,s11,f):.1f}" for f in [20,21,22])
        fc_s = f"{fc:.3f}" if fc else "none"
        print(f"\n[{item['case']}]  idx={upd['index1']}  c1y={upd['w_C1_y']}")
        lpf_s2 = f"{lpf:.2f}" if lpf else "FAIL"
        print(f"  Cross={fc_s} {ok_c}  S31={lpf_s2} {ok_s}"
              f"  worstIL={hil:.1f}  ripple={rip:.1f}")
        print(f"  S21: {s21_row}")
        print(f"  S11: {s11_row}")

    print("\n\n" + "="*70)
    print("SUMMARY TABLE  (w_sub=1.7mm, L4=1.10mm, L2=0.75mm)")
    print(f"  {'Case':<30} {'Cross':>7} {'S31':>6} {'worstIL':>9} {'ripple':>8}")
    print("-"*62)
    for idx, c1y, fc, lpf, hil, rip, *_ in sorted(results, key=lambda x: (x[0], x[1])):
        ok_c = "✓" if fc  and fc  >= 18.5 else " "
        ok_s = "✓" if lpf and lpf >= 18.5 else " "
        fc_s  = f"{fc:.3f}"  if fc  else " none"
        lpf_s = f"{lpf:.2f}" if lpf else " FAIL"
        label = f"idx={idx}  c1y={c1y}"
        print(f"  {label:<30} {fc_s:>7}{ok_c} {lpf_s:>6}{ok_s} {hil:>9.1f} {rip:>8.1f}")
    print("\nAll done.")


if __name__ == "__main__":
    main()
