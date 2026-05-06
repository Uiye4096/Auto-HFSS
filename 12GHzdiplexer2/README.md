# 12GHz SSL Diplexer — HFSS Automated Tuning Project

## Overview

This project automates the parametric tuning of a **Suspended Stripline (SSL)
quasi-lumped contiguous diplexer** modeled in ANSYS HFSS 2021 R2. The design
is based on the Rehner et al. 2009 paper ("A quasi-lumped ultra-broadband
contiguous SSL-diplexer from DC to 80 GHz").

The diplexer is a 3-port network:
- **Port 1**: Common input
- **Port 2**: High-pass filter (HPF) output
- **Port 3**: Low-pass filter (LPF) output

The HPF and LPF are complementary filters sharing a T-junction. When properly
tuned, the complementary admittance condition `Im(Y_LPF) + Im(Y_HPF) = 0`
is satisfied at the transition frequency fT, yielding low reflection (S11)
and flat insertion loss in both passbands.

---

## Directory Structure

```
12GHzdiplexer2/
├── 12GHzdiplexer.aedt          # Base HFSS project (DO NOT modify directly)
├── inspect.json                # Variable dump from base project (reference)
├── TUNING_PLAN.md              # Current tuning strategy document
├── README.md                   # This file
├── scripts/
│   ├── build_refineNN.py       # Build simulation cases for round NN
│   └── run_refineNN.py         # Run simulations + analyze results for round NN
└── derived/
    ├── refineNN/               # Output directory for round NN
    │   ├── manifest.json       # Case list with paths and parameters
    │   ├── case_name/
    │   │   ├── updates.json    # Parameter overrides for this case
    │   │   ├── case_name.aedt  # Modified HFSS project
    │   │   ├── update_result.json  # Confirmation of applied parameters
    │   │   └── sim/
    │   │       ├── case_name.s3p   # Touchstone 3-port S-parameter output
    │   │       └── case_name.svg   # S-parameter plot
    └── ...
```

### External Tools (shared across projects)

```
D:\Desktop\HFSS_real\tools/
├── aedt_inspect.py             # Read/modify HFSS .aedt variable values
├── plot_s3p.py                 # Generate SVG plots from .s3p files
└── run_and_plot.ps1            # PowerShell helper (legacy)

D:\Desktop\HFSS_real\12GHzdiplexer\scripts/
└── run_hfss_case.py            # IronPython script: open project → solve → export s3p
```

---

## Simulation Scaffold — How It Works

The workflow has two steps per round: **Build** then **Run**.

### Step 1: Build Cases (`build_refineNN.py`)

Each build script:
1. Defines a parameter sweep (e.g., varying `w_C412g` and `w_C1_y`)
2. For each combination, writes an `updates.json` with the overrides
3. Calls `aedt_inspect.py` to clone the base `.aedt` and patch variables
4. Outputs a `manifest.json` listing all cases

**Usage:**
```powershell
cd D:\Desktop\HFSS_real
python 12GHzdiplexer2\scripts\build_refineNN.py
```

**Template for a new build script:**
```python
import json, subprocess
from pathlib import Path

ROOT         = Path(r"D:\Desktop\HFSS_real")
MODEL        = ROOT / "12GHzdiplexer2"
BASE_PROJECT = MODEL / "12GHzdiplexer.aedt"
OUT_ROOT     = MODEL / "derived" / "refineNN"
INSPECT      = ROOT / "tools" / "aedt_inspect.py"

# These formulas MUST be included in every case to maintain geometry alignment
ALIGNMENT = {
    "compensation_y":
        "L2_g212g + cover_HPF_out12g + l_line212g + 1.426mm - l_sub12g",
    "compensation_y_2":
        "l_line312g + l_L512g + l_C412g + l_L312g + l_C212g + "
        "l_L112g + l_line412g - l_sub_LPF12g",
}

CASES = {
    "case_name": {
        "w_sub12G":  "1.700000mm",   # fixed
        "w_line12g": "0.395000mm",   # fixed
        "param1":    "value1",
        "param2":    "value2",
    },
}

def main():
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for case, base_upd in CASES.items():
        case_dir = OUT_ROOT / case
        case_dir.mkdir(parents=True, exist_ok=True)
        updates = dict(base_upd)
        updates.update(ALIGNMENT)
        up_path   = case_dir / "updates.json"
        proj_path = case_dir / f"{case}.aedt"
        up_path.write_text(json.dumps(updates, indent=2), encoding="utf-8")
        subprocess.run(
            ["python", str(INSPECT), str(BASE_PROJECT),
             "--set", str(up_path),
             "--write-to", str(proj_path),
             "--out", str(case_dir / "update_result.json")],
            check=True,
        )
        manifest.append({
            "case": case, "updates": base_upd,
            "project_path": str(proj_path),
            "output_dir": str(case_dir / "sim"),
        })
    (OUT_ROOT / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

if __name__ == "__main__":
    main()
```

### Step 2: Run Simulations (`run_refineNN.py`)

Each run script:
1. Reads `manifest.json`
2. For each case, launches HFSS via IronPython (`run_hfss_case.py`)
3. Generates SVG plots from the `.s3p` output
4. Parses S-parameters and computes metrics (crossing frequency, S31 −3 dB,
   worst insertion loss, passband ripple)
5. Prints a summary table

**Usage:**
```powershell
cd D:\Desktop\HFSS_real
python 12GHzdiplexer2\scripts\run_refineNN.py
```

**Parallel execution** (recommended for multiple cases):
```python
from concurrent.futures import ThreadPoolExecutor
MAX_WORKERS = 4  # match your HFSS license count

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
    futs = {ex.submit(run_one, item): item for item in todo}
    for fut in as_completed(futs):
        item, ok = fut.result()
```

See `run_refine18.py` for a complete parallel implementation.

### IronPython Runner (`run_hfss_case.py`)

This script is executed by IronPython (not CPython):
```
E:\HFFS\HFSS_2021\...\ipy64.exe  run_hfss_case.py  <project.aedt>  <output_dir>
```

It performs:
1. Opens the `.aedt` project in HFSS
2. Runs the frequency sweep (Setup1: 0–40 GHz, 501 points)
3. Exports `.s3p` Touchstone file to `<output_dir>/`
4. Closes the project

### `aedt_inspect.py` — Parameter Manipulation Tool

**Read all variables:**
```powershell
python tools\aedt_inspect.py  project.aedt  --out inspect.json
```

**Set variables and write new project:**
```powershell
python tools\aedt_inspect.py  base.aedt  --set updates.json  --write-to new.aedt  --out result.json
```

The `updates.json` format:
```json
{
  "w_sub12G": "1.700000mm",
  "w_line12g": "0.395000mm",
  "compensation_y": "L2_g212g + cover_HPF_out12g + l_line212g + 1.426mm - l_sub12g"
}
```

Values can be numeric (`"1.7mm"`) or expressions referencing other variables.

### `plot_s3p.py` — S-Parameter Plotting

```powershell
python tools\plot_s3p.py  output.s3p  --open
```

Generates an SVG file in the same directory as the `.s3p` file, showing:
- S11 (dB), S21 (dB), S31 (dB) vs Frequency
- Crossing frequency marker
- S31 −3 dB point
- S21 first −3 dB point

---

## Key Design Variables

### Fixed Parameters (do not change)

| Variable | Value | Description |
|----------|-------|-------------|
| `w_sub12G` | 1.700 mm | SSL channel width |
| `w_line12g` | 0.395 mm | Main transmission line width |
| `h_sub12G` | 0.254 mm | Substrate thickness |
| `l_sub_LPF12g` | 4.340 mm | LPF substrate length (T-junction sensitive) |
| `copper` | 0.035 mm | Conductor thickness |

### HPF Tuning Variables

| Variable | Baseline | Description |
|----------|----------|-------------|
| `L4_g312g` | 1.100 mm | HPF series capacitor gap (Y-direction) |
| `L2_g312g` | 0.750 mm | HPF shunt inductor gap (Y-direction) |
| `index1` | 0.6 m | HPF capacitor gap scaling factor |
| `w_C1_y` | 0.300 mm | T-junction shunt compensation capacitor (Y-size) |

### LPF Tuning Variables

| Variable | Baseline | Description |
|----------|----------|-------------|
| `w_C412g` | 1.100 mm | LPF shunt capacitor 4 width (X-direction) |
| `w_C212g` | 1.100 mm | LPF shunt capacitor 2 width (X-direction) |
| `l_C412g` | 0.616 mm | LPF shunt capacitor 4 length (Y-direction) |
| `l_C212g` | 0.506 mm | LPF shunt capacitor 2 length (Y-direction) |
| `w_L512g` | 0.080 mm | LPF series inductor 5 width |
| `w_L312g` | 0.030 mm | LPF series inductor 3 width |
| `w_L112g` | 0.090 mm | LPF series inductor 1 width |

### Geometric Alignment (auto-computed)

These MUST be set to their formula expressions in every case:

```
compensation_y   = L2_g212g + cover_HPF_out12g + l_line212g + 1.426mm - l_sub12g
compensation_y_2 = l_line312g + l_L512g + l_C412g + l_L312g + l_C212g + l_L112g + l_line412g - l_sub_LPF12g
```

**WARNING:** If `l_C412g` or `l_C212g` or any `l_L*` length changes,
`compensation_y_2` auto-updates. But the total of these lengths must NOT
exceed `l_sub_LPF12g + ~0.1 mm` to avoid geometric conflicts.

---

## S-Parameter Conventions

- **S11**: Reflection at port 1 (common input). Target: ≤ −10 dB in both passbands
- **S21**: Transmission port 1 → port 2 (HPF). Target: ≥ −1 dB in HPF passband
- **S31**: Transmission port 1 → port 3 (LPF). Target: ≥ −1 dB in LPF passband
- **Crossing frequency**: Where |S21| = |S31| (transition frequency fT)
- **S31 −3 dB**: Highest frequency where S31 ≥ −3 dB

### Energy Balance

At any frequency: `|S11|² + |S21|² + |S31|² + Loss = 1`

Where `Loss` represents conductor + dielectric dissipation (~13–17% in this model).

---

## Quick Start

```powershell
# 1. Build a new sweep round
cd D:\Desktop\HFSS_real
python 12GHzdiplexer2\scripts\build_refine20.py

# 2. Run simulations (parallel)
python 12GHzdiplexer2\scripts\run_refine20.py

# 3. View SVG plots (auto-opened, or manually)
Start-Process path\to\case\sim\case.svg

# 4. Compare with baseline
Start-Process 12GHzdiplexer2\derived\refine19_best\sim\r19_best.svg
```

---

## Tuning History Summary

| Round | Focus | Key Finding |
|-------|-------|-------------|
| r2–r9 | HPF gap tuning (w_sub=1.5) | Baseline established |
| r10 | w_sub=1.7mm exploration | Crossing improved to 18.4 GHz |
| r11–r12 | L4/L2/idx fine-tuning | Best: L4=1.10, L2=0.75, idx=0.6 |
| r13 | w_line12g scaling attempt | Abandoned (user constraint) |
| r14 | LPF element length scaling | Disrupts T-junction (l_sub_LPF sensitivity) |
| r15 | w_C1_y sweep | Maps crossing vs flatness trade-off |
| r16 | index1 × w_C1_y 2D sweep | Higher idx → better flatness but lower crossing |
| r17 | w_C412g/w_C212g reduction | Worsens LPF; w_C=0.85 pushes crossing but ruins passband |
| r18 | w_C × w_C1_y 2D sweep | Confirms Pareto frontier: crossing ↔ flatness |
| r19 | w_line12g=0.395mm baseline | New fixed constraint; S31 bump identified |
| **r20+** | **TUNING_PLAN.md** | **Suppress S31 bump → fix matching → re-tune** |

See `TUNING_PLAN.md` for the detailed Phase A–D strategy.
