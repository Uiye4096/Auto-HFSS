"""Run refine30_patch — close the 9 MHz gap in 185g-LPF approach."""
import json, math, subprocess, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT    = Path(r"D:\Desktop\HFSS_real")
OUT     = ROOT / "12GHzdiplexer2" / "derived" / "refine30_patch"
RUNNER  = ROOT / "12GHzdiplexer" / "scripts" / "run_hfss_case.py"
IPY     = r"E:\HFFS\HFSS_2021\Program Files\AnsysEM\AnsysEM21.2\Win64\common\IronPython\ipy64.exe"
lock    = threading.Lock()


def parse(path):
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
    db = lambda v: 20 * math.log10(v) if v > 0 else -100
    fr, s21, s31 = [], [], []
    for r in recs:
        if len(r) < 19: continue
        f = r[0] / 1e9 if r[0] > 1e7 else r[0]; fr.append(f)
        if fmt == "DB":   s21.append(r[7]);                    s31.append(r[13])
        elif fmt == "MA": s21.append(db(r[7]));               s31.append(db(r[13]))
        else:             s21.append(db(math.hypot(r[7], r[8]))); s31.append(db(math.hypot(r[13], r[14])))
    return fr, s21, s31


def at(fr, v, f):
    return v[min(range(len(fr)), key=lambda i: abs(fr[i] - f))]


def crossing(fr, s21, s31):
    for i in range(len(fr) - 1):
        d0, d1 = s21[i] - s31[i], s21[i+1] - s31[i+1]
        if d0 * d1 <= 0:
            t = d0 / (d0 - d1) if abs(d0 - d1) > 1e-9 else 0.5
            return fr[i] + t * (fr[i+1] - fr[i])
    return None


def run_one(it):
    name = Path(it["project_path"]).stem
    s3p  = Path(it["output_dir"]) / f"{name}.s3p"
    if s3p.exists():
        with lock: print(f"  [cached] {it['case']}")
        return it, True
    with lock: print(f"  [start ] {it['case']}")
    ret = subprocess.run([IPY, str(RUNNER), it["project_path"], it["output_dir"]],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ok = ret.returncode == 0 and s3p.exists()
    with lock: print(f"  [{'done ' if ok else 'FAIL '}] {it['case']}")
    return it, ok


def main():
    manifest = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
    results  = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(run_one, it): it for it in manifest}
        for fut in as_completed(futs):
            it, ok = fut.result()
            if ok:
                name = Path(it["project_path"]).stem
                s3p  = Path(it["output_dir"]) / f"{name}.s3p"
                results[it["case"]] = parse(s3p)

    print("\nRefine30_patch results:")
    print(f"  Prior best r27_c1y022: cross=18.552✓ S31@19=-10.8✓ rip25=0.6✓ IL=-3.1")
    print()
    for it in manifest:
        c = it["case"]
        if c not in results: print(f"  {c}: FAIL"); continue
        fr, s21, s31 = results[c]
        fc = crossing(fr, s21, s31)
        s19  = at(fr, s31, 19)
        s20  = at(fr, s31, 20)
        pb   = [at(fr, s21, f) for f in [20, 21, 22, 23, 25]]
        rip  = max(pb) - min(pb)
        hil  = min(pb)
        oc   = "✓" if fc  and fc  >= 18.5 else " "
        o19  = "✓" if s19 <= -10 else " "
        or_  = "✓" if rip <= 1.0  else " "
        fcs  = f"{fc:.3f}" if fc else "none"
        print(f"  {c:<36} cross={fcs}{oc} S31@19={s19:.1f}{o19} S31@20={s20:.1f} rip25={rip:.1f}{or_} IL={hil:.1f}")
        print(f"    S21: " + "  ".join(f"@{f}={at(fr,s21,f):.1f}" for f in [18,19,20,21,22,23,25,28]))
        print(f"    S31: " + "  ".join(f"@{f}={at(fr,s31,f):.1f}" for f in [17,18,19,20,21,22]))
    print("\nAll done.")


if __name__ == "__main__":
    main()
