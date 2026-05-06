"""Run refine10: solve + SVG + full dip analysis."""
import json
import math
import subprocess
from pathlib import Path

ROOT     = Path(r"D:\Desktop\HFSS_real")
OUT_ROOT = ROOT / "12GHzdiplexer2" / "derived" / "refine10"
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


def report(name, fr, s11, s21, s31):
    fc  = crossing(fr, s21, s31)
    pts = [f for f, v in zip(fr, s31) if v >= -3]
    lpf = max(pts) if pts else None
    hpf_pts = [f for f, v in zip(fr, s21) if f > 5 and v >= -3]
    hpf = min(hpf_pts) if hpf_pts else None
    fc_s  = f"{fc:.3f}" if fc else "none"
    lpf_s = f"{lpf:.2f}" if lpf else "FAIL"
    hpf_s = f"{hpf:.2f}" if hpf else "FAIL"
    print(f"\n  [RESULT] {name}")
    print(f"  Crossing : {fc_s} GHz")
    print(f"  S31 -3dB : {lpf_s} GHz  |  S21 first -3dB : {hpf_s} GHz")
    print(f"  S11 @19={at(fr,s11,19):.1f}  @20={at(fr,s11,20):.1f}  @21={at(fr,s11,21):.1f}  @22={at(fr,s11,22):.1f}")
    print(f"  S21 @19={at(fr,s21,19):.1f}  @20={at(fr,s21,20):.1f}  @21={at(fr,s21,21):.1f}  @22={at(fr,s21,22):.1f}  @25={at(fr,s21,25):.1f}  @30={at(fr,s21,30):.1f}")
    print(f"  S31 @16={at(fr,s31,16):.1f}  @17={at(fr,s31,17):.1f}  @18={at(fr,s31,18):.1f}  @19={at(fr,s31,19):.1f}")


def main():
    manifest = json.loads((OUT_ROOT / "manifest.json").read_text(encoding="utf-8"))
    for item in manifest:
        print(f"\n{'='*60}\nCase: {item['case']}")
        name = Path(item["project_path"]).stem
        s3p  = Path(item["output_dir"]) / f"{name}.s3p"
        if s3p.exists():
            print("  (cached)")
            report(name, *parse_s3p(s3p))
            continue
        ret = subprocess.run([IPY, str(RUNNER), item["project_path"], item["output_dir"]])
        if ret.returncode != 0:
            print("  HFSS FAILED"); continue
        if s3p.exists():
            subprocess.run(["python", str(PLOT), str(s3p), "--open"])
            report(name, *parse_s3p(s3p))
        else:
            print("  No .s3p")
    print("\nAll done.")


if __name__ == "__main__":
    main()
