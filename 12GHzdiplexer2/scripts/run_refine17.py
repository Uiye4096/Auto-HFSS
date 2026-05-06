"""Run refine17: LPF cap width sweep to push S31 up."""
import json
import math
import subprocess
from pathlib import Path

ROOT     = Path(r"D:\Desktop\HFSS_real")
OUT_ROOT = ROOT / "12GHzdiplexer2" / "derived" / "refine17"
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


def main():
    manifest = json.loads((OUT_ROOT / "manifest.json").read_text(encoding="utf-8"))
    results = []
    for item in manifest:
        name = Path(item["project_path"]).stem
        s3p  = Path(item["output_dir"]) / f"{name}.s3p"
        if not s3p.exists():
            ret = subprocess.run([IPY, str(RUNNER), item["project_path"], item["output_dir"]])
            if ret.returncode != 0 or not s3p.exists():
                print(f"  FAIL: {item['case']}"); continue
            subprocess.run(["python", str(PLOT), str(s3p), "--open"])
        fr, s11, s21, s31 = parse_s3p(s3p)
        fc   = crossing(fr, s21, s31)
        pts  = [f for f, v in zip(fr, s31) if v >= -3]
        lpf  = max(pts) if pts else None
        hil  = min(at(fr, s21, f) for f in [20, 21, 22, 23, 25, 28, 30, 36])
        vals = [at(fr, s21, f) for f in [20, 21, 22, 23, 25, 28, 30, 36]]
        rip  = max(vals) - min(vals)
        wc   = item["updates"]["w_C412g"]
        results.append((wc, fc, lpf, hil, rip))
        ok_c = "✓" if fc  and fc  >= 18.5 else "✗"
        ok_s = "✓" if lpf and lpf >= 18.5 else "✗"
        fc_s  = f"{fc:.3f}"  if fc  else "none"
        lpf_s = f"{lpf:.2f}" if lpf else "FAIL"
        s21_str = "  ".join(f"@{f}={at(fr,s21,f):.1f}" for f in [18,19,20,21,22,25,28])
        s31_str = "  ".join(f"@{f}={at(fr,s31,f):.1f}" for f in [16,17,18,19])
        print(f"\n[{item['case']}]  w_C={wc}")
        print(f"  Cross={fc_s} {ok_c}   S31={lpf_s} {ok_s}   worstIL={hil:.1f}   ripple={rip:.1f}")
        print(f"  S21: {s21_str}")
        print(f"  S31: {s31_str}")

    # Summary table
    print("\n\n" + "="*68)
    print("SUMMARY: w_C width sweep  (base: ws17_l4_110_idx06)")
    print(f"  {'w_C':>8}  {'Cross':>9}  {'S31-3dB':>9}  {'worstIL':>9}  {'ripple':>8}")
    print("-"*56)
    for wc, fc, lpf, hil, rip in results:
        ok_c  = "✓" if fc  and fc  >= 18.5 else " "
        ok_s  = "✓" if lpf and lpf >= 18.5 else " "
        fc_s  = f"{fc:.3f}"  if fc  else " none"
        lpf_s = f"{lpf:.2f}" if lpf else " FAIL"
        print(f"  {wc:>8}  {fc_s:>9}{ok_c}  {lpf_s:>9}{ok_s}  {hil:>9.1f}  {rip:>8.1f}")
    print("\nAll done.")


if __name__ == "__main__":
    main()
