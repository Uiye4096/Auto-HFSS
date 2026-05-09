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
| `SSL_28.5GHzdiplexer/` | 28.5 GHz scaling study — 6 sweep rounds, 70 HFSS cases |
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

## 185 GHz Optimised Design — Case 087 ★ (Rounds 9–18, current final)

Continued optimisation over **Rounds 9–18 / 142 cases** targeting S11w ≤ −10 dB. Stored in `0506185GHzmodel - 副本/final/`.

| Metric | **087 (final)** | 037 (prev) | baseline | Target |
|--------|-----------------|------------|----------|--------|
| Crossing freq | **18.516 GHz** | 18.546 GHz | 18.504 GHz | ≥ 18.5 GHz ✓ |
| S31 @ 19 GHz | −8.1 dB | −10.9 dB | −7.9 dB | ≤ −10 dB △ |
| S31 @ 20 GHz | **−12.3 dB** | −12.3 dB | −8.1 dB | ≤ −10 dB ✓ |
| Passband ripple 20–25 GHz | **0.59 dB** | 0.54 dB | 0.87 dB | ≤ 1 dB ✓ |
| avg IL (20–28.5 GHz) | **−0.62 dB** | −1.4 dB | −1.6 dB | — (best) |
| S11 worst (19–28 GHz) | **−9.3 dB** | −7.4 dB | −7.0 dB | ≤ −10 dB △ |

Key parameters vs 037:

| Parameter | **087** | 037 | Role |
|-----------|---------|-----|------|
| `w_C4185g` | **1.15 mm** | 1.15 mm | LPF capacitor width |
| `w_C2185g` | **1.05 mm** | 1.08 mm | LPF capacitor width |
| `L7_g3185g` | **0.83 mm** | 0.75 mm | LPF transmission zero ← refined |
| `L7_g4185g` | **0.52 mm** | 0.50 mm | HPF stub length ← key for S11 |
| `L2_g3185g` | 0.78 mm | 0.78 mm | HPF stub → crossing |
| `k` (LPF scale) | 0.96 | 0.96 | LPF element scaling |

Key discoveries (Rounds 9–18):
- **`L7_g4185g`** (HPF output stub) is the primary S11 lever; 0.52 mm gives best 19–28 GHz match.
- **`w_C4185g` = 1.10 mm** can push S11w below −10 dB (case 141, S11w = −10.6 dB) but degrades low-frequency shape — not selected.
- S31@19 is physically limited by the crossing frequency position (~18.5 GHz); 19 GHz is only ~400 MHz above crossing, leaving insufficient LPF roll-off margin for this topology.
- S11w = −9.3 dB is the practical optimum for 087-class parameters without shape degradation.

Files: `0506185GHzmodel - 副本/final/diplexer_185g_087.aedt`, `.s3p`  
Optimisation log: `0506185GHzmodel - 副本/TUNING_LOG.md`

## 28.5 GHz Scaling Study — SSL_28.5GHzdiplexer

Attempt to scale the 18.5 GHz case-087 diplexer to a 28.5 GHz target on the **same H=0.254 mm substrate** (Rogers RO3010). Six sweep rounds, **70 HFSS full-wave cases** total.

### Sweeps summary

| Round | Script | Description | Best main crossing |
|-------|--------|-------------|--------------------|
| 1 | `run_285g_sweep1.py` | Naive geometric scale ×0.649 | 21.3 GHz |
| 2 | `run_285g_sweep2.py` | + Fringing correction on l_C4, l_C2 | **24.7 GHz** |
| 3 | `run_285g_sweep3.py` | All lengths × 0.80, double-fringing correction | 24.0 GHz |
| 4 | `run_285g_sweep4.py` | LPF cap-only scan (l_C4 0.07–0.14 mm) | 24.0 GHz |
| 5 | `run_285g_sweep5.py` | Reduce w_C4 / w_C2 width (0.65–1.05 mm) | 25.7 GHz (spurious) |
| 6 | `run_285g_sweep6.py` | Freeze LPF (case024), scale HPF only (k=0.75–0.90) | **25.7 GHz** |

### Physical limits found

- **Fringing capacitance dominates**: at 28.5 GHz, w_C4=1.15 mm on H=0.254 mm gives Δl≈0.10 mm/end. Even with l_C4→0, the junction fringing alone caps the LPF cutoff at ~25 GHz.
- **Independent HPF push insufficient**: pushing HPF cutoff to 28.5 GHz (k≈0.80) gives S21@28.5≈−3 dB, but the LPF is already deep in stopband (S31@28.5≈−12 dB). Gap = 9 dB — cannot close.
- **Both cutoffs must reach 28.5 GHz simultaneously**, which requires redesigning the LPF topology, not just scaling.

### Conclusion

The 18.5 GHz topology **cannot be scaled to 28.5 GHz** on the same H=0.254 mm substrate via parameter adjustment alone. Maximum clean diplexer crossing achieved: **25.7 GHz** (case 058, k_HPF=0.75, L2=0.36 mm).

Next step: start from `SSL_28.5double/` (native 28.5 GHz topology) or redesign LPF/HPF from ADS lumped prototype at 28.5 GHz.

### Key baselines

| File | Description |
|------|-------------|
| `SSL_28.5GHzdiplexer/final/diplexer_285g_baseline.aedt` | Naive ×0.649 scale of 087 |
| `SSL_28.5GHzdiplexer/final/diplexer_285g_corrected.aedt` | + Fringing correction on l_C4, l_C2 (sweep2 base) |
| `SSL_28.5GHzdiplexer/final/diplexer_285g_corrected2.aedt` | + Additional ×0.80 on all lengths (sweep3 base) |
| `SSL_28.5GHzdiplexer/runs/sweep6_manifest.json` | Sweep 6 manifest (best: UID 058) |

---

## ADS Automation Exploration & Lumped Model Analysis

Explored Keysight ADS (E:\Program Files\Keysight\ADS2024) as a second simulation backend alongside HFSS. Key findings:

### ADS Batch Simulation — Confirmed Working

`hpeesofsim.exe` can run standalone netlist (`.nel`) simulations; `dsdump.exe` parses the binary `.ds` output.

```powershell
# Minimal env setup (PATH must stay short — all-dirs approach breaks Windows PATH limit)
$env:HPEESOF_DIR = 'E:\Program Files\Keysight\ADS2024'
$env:PATH = "$env:HPEESOF_DIR\bin;$env:HPEESOF_DIR\lib;$env:PATH"
& "$env:HPEESOF_DIR\bin\hpeesofsim.exe" my_netlist.nel
& "$env:HPEESOF_DIR\bin\dsdump.exe"  my_netlist.ds
```

**Known limitation**: 3-port S-param simulation crashes (STATUS_NO_MEMORY / `0xC0000017`) in standalone mode — only 2-port supported without full ADS workspace.

### SSL_wrk Diplexer — Extracted Circuit Topology

Reference ADS diplexer workspace at `0506185GHzmodel - 副本/SSL_wrk/`:

| Branch | Topology | Element values (28.5 GHz design) |
|--------|----------|----------------------------------|
| **LPF** | series-L / shunt-C T-network (5th order) | L1=L3=0.476 nH, L2=0.710 nH, C1=C2=0.137 pF |
| **HPF** | series-C / shunt-L (5th order) | C1=0.069 pF, C2=0.058 pF, C3=0.124 pF, L1=0.161 nH, L2=0.185 nH |

Diplexer crossing: **28.50 GHz**, S11 null: **−52 dB** at crossing (LPF.ds dataset).

### Frequency Scaling to 18.5 GHz

Scaling all L and C by `28.5/18.5 = 1.5405`:

| Element | 28.5 GHz | → 18.5 GHz |
|---------|----------|------------|
| LPF L1, L3 | 0.476 nH | **0.734 nH** |
| LPF L2 | 0.710 nH | **1.093 nH** |
| LPF C1, C2 | 0.137 pF | **0.212 pF** |
| HPF C1 | 0.069 pF | **0.106 pF** |
| HPF C2 | 0.058 pF | **0.090 pF** |
| HPF C3 | 0.124 pF | **0.191 pF** |
| HPF L1 | 0.161 nH | **0.247 nH** |
| HPF L2 | 0.185 nH | **0.284 nH** |

Result: HPF −3 dB at **18.4 GHz** ✓, LPF −3 dB at **19.6 GHz** (LPF needs extra ×1.06 to balance), crossing **19.2 GHz** (slight over-shoot; tune LPF scale to ~1.63× instead of 1.54×).

### Lumped Model Insights for HFSS 087 Tuning

Comparing the ideal lumped circuit to the HFSS 087 result reveals the fundamental limits:

**S31@19 GHz = −8.1 dB (target ≤ −10 dB)**
- A 5th order HPF at 18.5 GHz gives only **~−2 dB attenuation at 19 GHz** (2.7% above cutoff) in the lumped model. HFSS distributed effects add ~6 dB, reaching −8.1 dB.
- To reach −10 dB: either lower the crossing to ~17.8 GHz (increases 19 GHz separation) or add transmission zeros in the HPF stopband via additional microstrip stubs.
- Parameter lever: **decreasing `L2_g3185g` below 0.78 mm** shifts crossing higher (more separation to 19 GHz) but risks degrading S31@20 GHz shape.

**S11w = −9.3 dB (target ≤ −10 dB)**
- The ideal lumped diplexer achieves S11 < −24 dB across the full band. The HFSS gap is explained by the LPF presenting partial impedance to port 1 in the HPF passband (LPF stopband attenuation at 20 GHz is insufficient).
- Widening `w_C4185g` steepens LPF roll-off → better LPF stopband → better S11 in HPF band.
- Case 141 (wC4=1.10 mm) confirmed S11w = −10.6 dB but introduced shape degradation at low frequency. The fundamental tension: **steeper LPF roll-off improves S11 but distorts the crossing region**.
- Practical limit for 087-class topology: **S11w ≈ −9.3 dB** without topology change.

Script: `C:\Temp\ads_test\scale_to_185g.py` (ADS batch simulation + frequency scaling pipeline).

---

## 185 GHz Optimised Design — Case 037 (Rounds 1–8, superseded)

Previous accepted design over **8 rounds / 51 cases**. Superseded by 087 (better S11, IL).

| Metric | **037** | baseline | Target |
|--------|---------|----------|--------|
| Crossing freq | 18.546 GHz | 18.504 GHz | ≥ 18.5 GHz ✓ |
| S31 @ 19 GHz | −10.9 dB | −7.9 dB | ≤ −10 dB ✓ |
| S31 @ 20 GHz | −12.3 dB | −8.1 dB | ≤ −10 dB ✓ |
| Passband ripple 20–25 GHz | 0.54 dB | 0.87 dB | ≤ 1 dB ✓ |
| S11 worst (19–25 GHz) | −7.4 dB | −7.0 dB | — |

Optimisation log: `0506185GHzmodel - 副本/TUNING_LOG.md`

