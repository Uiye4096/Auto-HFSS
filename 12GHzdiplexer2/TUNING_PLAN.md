# SSL Diplexer Tuning Plan — Phase 20+

## 1. Current Baseline (r19_best)

| Parameter | Value |
|-----------|-------|
| `w_sub12G` | **1.700 mm** (fixed) |
| `w_line12g` | **0.395 mm** (fixed) |
| `L4_g312g` | 1.100 mm |
| `L2_g312g` | 0.750 mm |
| `index1` | 0.6 m |
| `w_C1_y` | 0.300 mm |
| `w_C412g` / `w_C212g` | 1.100 mm |
| `w_L512g` / `w_L312g` / `w_L112g` | 0.08 / 0.03 / 0.09 mm |
| `l_C412g` / `l_C212g` | 0.616 / 0.506 mm |
| `l_L512g` / `l_L312g` / `l_L112g` | 0.77 / 0.912 / 0.516 mm |

### 1.1 Baseline Performance

| Metric | Value |
|--------|-------|
| S21/S31 crossing | 17.875 GHz |
| S31 −3 dB | 17.68 GHz |
| HPF worst IL (20–36 GHz) | −4.1 dB |
| HPF ripple | 3.6 dB |
| S11 @19–22 GHz | −4.4 to −3.8 dB |

### 1.2 Core Problem: S31 Stopband Bump

Detailed S31 data from 18–20 GHz reveals a **non-monotonic bump**:

```
18.32 GHz  S31 = −10.8 dB  ← local minimum (deepest point)
19.28 GHz  S31 =  −8.1 dB  ← bump peak (+2.7 dB rise!)
20.80 GHz  S31 = −10.6 dB  ← resumes monotonic decay
```

The LPF stopband **rises by 2.7 dB** between 18.3 and 19.5 GHz before resuming
its rolloff. At 19 GHz, 15.5% of input power leaks through the LPF port,
while 35.5% is reflected (S11 = −4.5 dB). This directly caps HPF passband quality.

**Goal:** Flatten S31 to ≤ −10 dB from 18.3 GHz onwards, which should:
- Reduce HPF insertion loss by ~0.5–1.0 dB (energy redistribution)
- Improve T-junction matching (S11 ↓) → further improves HPF passband
- Enable subsequent HPF tuning to push crossing toward 18.5 GHz

---

## 2. Root Cause Analysis

### 2.1 Why the Bump Exists

The SSL quasi-lumped LPF consists of alternating high-Z strips (inductors) and
low-Z strips (capacitors). The stopband attenuation depends on:

1. **Impedance ratio** Z_L / Z_C — higher ratio = deeper stopband
2. **Transmission zeros** — shunt stubs (capacitor sections) resonate at
   their quarter-wave frequency, creating deep nulls in S31
3. **Inter-zero gaps** — between transmission zeros, S31 can rise (the bump)

Current structure: `L5 → C4 → L3 → C2 → L1` (5th-order stepped-impedance LPF)

| Element | Length (mm) | Width (mm) | Role |
|---------|------------|-----------|------|
| L5 (l_L512g) | 0.770 | 0.080 (w_L512g) | Series inductor |
| **C4** (l_C412g) | **0.616** | **1.100** (w_C412g) | Shunt capacitor |
| L3 (l_L312g) | 0.912 | 0.030 (w_L312g) | Series inductor |
| **C2** (l_C212g) | **0.506** | **1.100** (w_C212g) | Shunt capacitor |
| L1 (l_L112g) | 0.516 | 0.090 (w_L112g) | Series inductor |

The two shunt capacitors (C4 and C2) have different lengths → different quarter-wave
resonance frequencies → their transmission zeros are at different frequencies.
Between these two zeros, S31 rises → **the bump**.

### 2.2 Impedance Ratio Analysis

With `w_sub12G = 1.7 mm`:
- Capacitor fill ratio: `w_C / w_sub = 1.1 / 1.7 = 64.7%`
  (Paper Rehner 2009 uses fill ratio ~90%+ for maximum impedance ratio)
- The low fill ratio means **capacitance per unit length is suboptimal**
- The impedance ratio Z_L/Z_C is lower than design optimum → weaker stopband

### 2.3 Energy Budget at 19 GHz (bump peak)

```
|S11|² = 0.355  (35.5% reflected)      ← T-junction mismatch
|S21|² = 0.355  (35.5% HPF output)     ← limited by reflection + leakage
|S31|² = 0.155  (15.5% LPF leakage)    ← the bump
Loss   = 0.135  (13.5% material loss)  ← conductor + dielectric
```

If S31 suppressed to −10 dB (10%) and S11 also improves to −8 dB (16%):
`|S21|² ≈ 1 − 0.16 − 0.10 − 0.13 = 0.61 → S21 = −2.1 dB` (was −4.5 dB!)

---

## 3. Tuning Strategy (4 Phases)

### Phase A: Suppress S31 Stopband Bump (LPF optimization)

**Goal:** S31 ≤ −10 dB from 18 GHz onwards (currently −8.1 dB at 19 GHz).

Three independent knobs affect the stopband without changing `compensation_y_2`:

#### A1. Increase LPF capacitor widths (`w_C412g`, `w_C212g`)
- Increase from 1.1 mm toward `w_sub = 1.7 mm` (e.g., 1.3, 1.4, 1.5, 1.6 mm)
- Higher fill ratio → lower Z_C → higher impedance ratio → deeper stopband
- **Does NOT affect `compensation_y_2`** (only width, not length)
- Key reference: Rehner 2009 §III uses near-full-width shunt stubs
- NOTE: refine17 tested *reducing* w_C (wrong direction); we have NOT tested
  *increasing* w_C beyond 1.1 mm — **this is the most promising unexplored knob**

#### A2. Redistribute capacitor lengths (`l_C412g` ↔ `l_C212g`)
- Current: l_C412g = 0.616 mm, l_C212g = 0.506 mm (ratio = 1.22)
- Their transmission zeros are at different frequencies → gap between zeros = bump
- Equalize the lengths: l_C412g = 0.561, l_C212g = 0.561 (total unchanged = 1.122 mm)
- Merged zeros → single deeper null at ~19 GHz instead of two spaced nulls
- **`compensation_y_2` unchanged** (total l_C412g + l_C212g same)
- Alternative: deliberately split them further to create two zeros straddling the bump

#### A3. Reduce LPF inductor widths (`w_L312g`)
- Current w_L312g = 0.030 mm (already very narrow)
- Making it narrower (0.020 mm) increases Z_L → higher impedance ratio → deeper stopband
- Risk: may hit fabrication limits; diminishing returns at very narrow widths
- Also try `w_L512g` (0.08 → 0.05 mm) and `w_L112g` (0.09 → 0.05 mm)
- **Does NOT affect `compensation_y_2`**

**Simulation plan for Phase A:**
```
Sweep 1 (A1): w_C412g = w_C212g = {1.2, 1.3, 1.4, 1.5, 1.6} mm   (5 cases)
Sweep 2 (A2): l_C412g / l_C212g = {0.561/0.561, 0.58/0.54, 0.65/0.47}  (3 cases)
Sweep 3 (A3): w_L312g = {0.020, 0.025} mm × w_L512g = {0.05, 0.08} mm  (4 cases)
Total: 12 cases, run 4-parallel → ~3 batches
```

### Phase B: Re-tune HPF Crossing Frequency

**Goal:** Push S21/S31 crossing from 17.875 → 18.5 GHz.

After Phase A fixes the S31 bump, we re-tune the HPF to reach the target crossing.
Adjustable HPF parameters:

| Parameter | Current | Role | Effect on crossing |
|-----------|---------|------|-------------------|
| `L4_g312g` | 1.100 mm | HPF series capacitor gap | ↑ raises crossing |
| `L2_g312g` | 0.750 mm | HPF shunt inductor gap | interacts with L4 |
| `index1` | 0.6 m | HPF capacitor gap scaling | ↑ raises crossing |
| `w_C1_y` | 0.300 mm | T-junction shunt capacitor | ↓ raises crossing but worsens flatness |

**Simulation plan for Phase B:**
Take best result from Phase A, then:
```
Sweep 4: L4_g312g = {1.05, 1.10, 1.15, 1.20} mm × index1 = {0.5, 0.6, 0.7} m  (12 cases)
```

### Phase C: Flatten HPF Passband

**Goal:** Minimize HPF insertion loss ripple in 19–36 GHz band.

With S31 bump suppressed and crossing near 18.5 GHz:
- Fine-tune `w_C1_y` to satisfy the complementary admittance condition:
  `Im(Y_LPF) + Im(Y_HPF) = 0` at the transition frequency
- Sweep `w_C1_y` from 0.15 to 0.50 mm in 0.05 mm steps (8 cases)

### Phase D: Final Joint Optimization

**Goal:** Fine-tune all parameters simultaneously for best combined performance.

Take the top 3 candidates from Phases B+C, then run a targeted grid around each:
- ±0.02 mm on L4_g312g
- ±0.02 mm on w_C1_y
- ±0.05 mm on w_C412g/w_C212g
~27 cases total → 7 parallel batches

---

## 4. Constraints

| Constraint | Value | Reason |
|------------|-------|--------|
| `w_sub12G` | 1.700 mm | User specification (fixed) |
| `w_line12g` | 0.395 mm | User specification (fixed) |
| `compensation_y` | formula | Geometric alignment HPF branch |
| `compensation_y_2` | formula | Geometric alignment LPF branch |
| `l_sub_LPF12g` | 4.34 mm | Must NOT change (T-junction sensitivity) |
| LPF inductor width | ≥ 0.020 mm | Fabrication limit |

---

## 5. Success Criteria

| Metric | Target | Stretch |
|--------|--------|---------|
| S21/S31 crossing | ≥ 18.5 GHz | 18.5 ± 0.05 GHz |
| S31 in stopband (18–20 GHz) | ≤ −10 dB | ≤ −15 dB |
| HPF worst IL (20–36 GHz) | ≤ −3 dB | ≤ −2 dB |
| HPF passband ripple | ≤ 2 dB | ≤ 1 dB |
| S11 at crossing | ≤ −10 dB | ≤ −15 dB |

---

## 6. Execution Order

```
Phase A  ──→  pick best S31 suppression
Phase B  ──→  push crossing to 18.5 GHz
Phase C  ──→  flatten HPF passband with w_C1_y
Phase D  ──→  final joint fine-tune
```

Each phase produces SVG plots + summary tables. Results carry forward to next phase.
Total estimated simulations: ~60 cases × ~2 min each ÷ 4 parallel = ~30 minutes wall-clock.
