# HFSS_real

This workspace is organized by model. Shared tools live under `tools/`, and model-specific engineering files, derived cases, reports, and probe scripts live under each model folder.

## Layout

- `12GHzdiplexer/`
  Main tuning target.
- `SSL_28.5double/`
  Reference model used to compare parameterization and solver setup.
- `tools/`
  Shared utilities, including `aedt_inspect.py`.
- `12GHzdiplexer.aedtresults/`
  Root-level AEDT temp results that may remain while AEDT is open.
- `SSL_28.5double.aedtresults/`
  Root-level AEDT temp results that may remain while AEDT is open.

## 12GHzdiplexer

- `12GHzdiplexer/12GHzdiplexer.aedt`
  Original project.
- `12GHzdiplexer/archive/12GHzdiplexer.aedt`
  Backup copy.
- `12GHzdiplexer/reports/12g_summary.json`
  Variable extraction result.
- `12GHzdiplexer/derived/`
  All generated candidates and probe outputs.
- `12GHzdiplexer/references/Rehner et al. - 2009 - A quasi-lumped ultra-broadband contiguous SSL-diplexer from DC to 80 GHz(1).pdf`
  Reference paper for the tuning task.

## SSL_28.5double

- `SSL_28.5double/SSL_28.5double.aedt`
  Reference project.
- `SSL_28.5double/archive/SSL_28.5double.aedt`
  Backup copy.
- `SSL_28.5double/reports/aedt_summary.json`
  Parsed variables, setups, and Optimetrics.
- `SSL_28.5double/derived/`
  Test updates and derived copies.

## Shared Tools

- `tools/aedt_inspect.py`
  Parses AEDT text projects and writes safe variable updates to derived copies.

## diplexer.py — Unified Simulation Entry Point

Single script at workspace root for running parameterised diplexer HPF simulations.

```powershell
# Single run (best known config):
python diplexer.py --wC 1.45 --L4 0.85 --L2 0.75 --k 0.90 --idx 0.60 --c1y 0.22

# Dry run (build project, skip HFSS):
python diplexer.py --wC 1.45 --dry-run

# Different project:
python diplexer.py --project 18GHzdiplexer2 --wC 1.30 --k 0.88

# Open SVG after sim:
python diplexer.py --wC 1.45 --open-svg
```

Each run creates `<project>/runs/run_<params>_<timestamp>/` containing:
- `project.aedt`  — parameterised HFSS project
- `result.s3p`    — exported S-parameters
- `plot.svg`      — S-parameter chart
- `params.json`   — parameters + metrics (crossing freq, S31, ripple, IL)
- `run.log`       — timestamped execution log

To sweep in parallel, launch multiple processes externally:
```powershell
1.30, 1.40, 1.45 | ForEach-Object -Parallel {
    python D:/Desktop/HFSS_real/diplexer.py --wC $_ --L4 0.85 --k 0.90
}
```

## What was done today

- Confirmed the `.aedt` files are text-based project files.
- Built an AEDT/IronPython automation path and verified it can launch HFSS, solve, and export `.s3p`.
- Established the baseline response of `12GHzdiplexer` and measured the current channel split around `28.2-28.5 GHz`.
- Ruled out `delta_x_HP12g` as a tuning variable.
- Tested multiple high-frequency parameters and found:
  - `L4_g312g` moves the split in the right direction, but weakly.
  - `d_L412g` is directionally awkward and becomes unstable.
  - `L4_g412g` is sensitive, but moves the split the wrong way.
- The next practical search space is now centered on `L4_g312g`, `d_L412g` alternatives, and `w_line12g` if needed.

## Current Goal

Move the high-frequency channel boundary from roughly `28.5 GHz` down to `18.5 GHz`.

