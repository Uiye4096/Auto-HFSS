# HFSS_real

Automated HFSS diplexer simulation workspace. Shared tools live under `tools/`; each model has its own folder with scripts, derived runs, and a `final/` directory for accepted designs.

## Workspace Layout

| Folder | Contents |
|--------|----------|
| `12GHzdiplexer/` | Original 12 GHz model + IronPython runner script |
| `12GHzdiplexer2/` | Main optimisation workspace (refine2–30, final design) |
| `18GHzdiplexer2/` | 18 GHz variant project |
| `18Ghzdiplexer/` | Earlier 18 GHz reference copy |
| `0506185GHzmodel - 副本/` | 185 GHz reference model (baseline analysed) |
| `SSL_28.5double/` | Reference model used to verify automation path |
| `tools/` | Shared utilities (`aedt_inspect.py`, `aedt_ping.py`, …) |

## Shared Tools

- **`tools/aedt_inspect.py`** — parses `.aedt` text projects, reads/writes variable values.
- **`tools/aedt_ping.py`** — verifies HFSS can be launched non-graphically.

## diplexer.py — Unified Simulation Entry Point

Single script at workspace root for running parameterised diplexer simulations.

```powershell
# Single run (best known 12g config):
python diplexer.py --wC 1.45 --L4 0.85 --L2 0.75 --k 0.90 --idx 0.60 --c1y 0.22

# Dry run (build project file, skip HFSS):
python diplexer.py --wC 1.45 --dry-run

# Simulate a model as-is (no parameter injection):
python diplexer.py --project "0506185GHzmodel - 副本" --as-is

# Open interactive HTML viewer after simulation:
python diplexer.py --wC 1.45 --open-svg

# Target a different project folder:
python diplexer.py --project 18GHzdiplexer2 --wC 1.30 --k 0.88
```

Each run creates `<project>/runs/run_<params>_<timestamp>/` containing:

| File | Description |
|------|-------------|
| `result.aedt` | Parameterised HFSS project |
| `result.s3p` | Exported S-parameters |
| `plot.svg` | Static S-parameter chart |
| `plot.html` | Interactive viewer (drag cursor to inspect any frequency) |
| `params.json` | Parameters + metrics (crossing freq, S31, ripple, IL, S11) |
| `run.log` | Timestamped execution log |

Parallel sweep (PowerShell):
```powershell
1.30, 1.40, 1.45 | ForEach-Object -Parallel {
    python D:/Desktop/HFSS_real/diplexer.py --wC $_ --L4 0.85 --k 0.90
}
```

## plot_interactive.py — Standalone Interactive Viewer

Generates a self-contained interactive HTML from any `.s3p` file.

```powershell
python plot_interactive.py path\to\result.s3p --open
python plot_interactive.py path\to\result.s3p --title "My Design" --out output.html
```

Features: draggable frequency cursor, SVG-native semi-transparent readout box, Claude-style colour scheme (warm white + orange accent).

## Final Design — 12GHz Diplexer

Best accepted result: **`r27_c1y022`**, stored in `12GHzdiplexer2/final/`.

| Metric | Value | Target |
|--------|-------|--------|
| Crossing frequency | 18.552 GHz | ≥ 18.5 GHz ✓ |
| S31 @ 19 GHz | −10.8 dB | ≤ −10 dB ✓ |
| S31 @ 20 GHz | −15.8 dB | ≤ −10 dB ✓ |
| Passband ripple 20–25 GHz | 0.6 dB | ≤ 1 dB ✓ |
| Min IL (20 GHz+) | −3.1 dB | — |

Key parameters: `wC=1.45 mm`, `L4=0.85 mm`, `L2=0.75 mm`, `k=0.90`, `idx=0.60`, `c1y=0.22 mm`.

## 185 GHz Reference Model Baseline

Simulated `0506185GHzmodel - 副本` with `--as-is`. Results vs final 12g design:

| Metric | 185g baseline | r27_c1y022 |
|--------|--------------|------------|
| Crossing freq | 18.504 GHz ✓ | 18.552 GHz ✓ |
| S31 @ 19 GHz | −7.9 dB ✗ | −10.8 dB ✓ |
| S31 @ 20 GHz | −8.1 dB ✗ | −15.8 dB ✓ |
| Min IL 20+ | −1.6 dB (better) | −3.1 dB |
| S11 worst | −7.0 dB (better) | −3.9 dB |

185g model has better S11 and IL but insufficient LPF stopband suppression due to narrower capacitor widths (1.0/0.9 mm vs 1.45 mm).

