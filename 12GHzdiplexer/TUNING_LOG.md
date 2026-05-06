# 12GHzdiplexer Tuning Log

Date: 2026-04-27

## Target

Move the diplexer split / crossover region from about 28.5 GHz toward 18.5 GHz.

Working interpretation:
- `S31` is the low-frequency channel.
- `S21` is the high-frequency channel.
- Baseline `S31` right 3 dB point: 28.214 GHz.
- Baseline `S21` first rising 3 dB entry: 28.446 GHz.
- Do not tune `delta_x_HP12g`.

## Constraints Observed

- Y-direction geometry changes can leave ports or air boxes inconsistent.
- `w_L212g`, `d_L212g`, `d_L412g`, `cover_HPF_out12g`, and `l_line212g` are risky or have failed in prior/probe runs.
- Width parameters on the LPF side (`w_L512g`, `w_C412g`, `w_L312g`, `w_C212g`, `w_L112g`) only appear in X position/size expressions and solved reliably in this round.

## New Runs

All runs were created under `12GHzdiplexer/derived/` from `derived/12GHzdiplexer_analysiscopy.aedt`.

| Case | Main changes | Solve | S21 first 3 dB | S31 right 3 dB | Notes |
| --- | --- | --- | ---: | ---: | --- |
| `aggressive_combo/combo_g312_1p5_wline_1p05_g212_1p05` | `L4_g312g=0.6mm`, `w_line12g=0.3885mm`, `L4_g212g=0.063mm` | pass | 27.142 GHz | 26.910 GHz | Similar to `L4_g312g` alone; combo does not add much. |
| `l2_gap_aggressive/L2_g112g_1p5` | `L2_g112g=0.06mm` | pass | 28.629 GHz | not primary | Wrong direction / negligible. |
| `l2_gap_aggressive/L2_g312g_1p5` | `L2_g312g=0.6mm` | pass | 31.694 GHz | not primary | Wrong direction. |
| `l2_gap_aggressive/L2_g112g_0p5` | `L2_g112g=0.02mm` | pass | 28.517 GHz | not primary | Negligible. |
| `l2_gap_aggressive/L2_g312g_0p5` | `L2_g312g=0.2mm` | pass | 30.910 GHz | not primary | Wrong direction. |
| `l2_gap_aggressive/L2_g412g_0p5` | `L2_g412g=0.15mm` | pass | 34.640 GHz | not primary | Wrong direction. |
| `l2_gap_aggressive/L2_g212g_0p5` | `L2_g212g=0.025mm` | fail | - | - | `AnalyzeAll()` failed. |
| `l2_gap_aggressive/L2_g212g_1p5` | `L2_g212g=0.075mm` | fail | - | - | `AnalyzeAll()` failed. |
| `l2_gap_aggressive/L2_g412g_1p5` | `L2_g412g=0.45mm` | fail | - | - | `AnalyzeAll()` failed. |
| `hpf_aggressive_physical/w_L412g_0p5` | `w_L412g=0.028mm` | pass | 28.518 GHz | not primary | Negligible. |
| `hpf_aggressive_physical/w_L412g_2p0` | `w_L412g=0.112mm` | pass | 37.482 GHz | not primary | Strongly wrong direction. |
| `hpf_aggressive_physical/l_line212g_1p54` | `l_line212g=1.54mm` | fail | - | - | `AnalyzeAll()` failed. |
| `split_down_aggressive/lpf_widths_1p5` | LPF widths 1.5x | pass | 28.334 GHz | 26.638 GHz | LPF side moves down; HPF nearly unchanged. |
| `split_down_aggressive/lpf_widths_1p5_hpf_g312_1p5` | LPF widths 1.5x + `L4_g312g=0.6mm` | pass | 27.021 GHz | 26.373 GHz | Best balanced safe case so far, still far from 18.5. |
| `split_down_aggressive/lpf_widths_3p0_hpf_g312_1p5` | LPF widths 3x + `L4_g312g=0.6mm` | pass | 26.868 GHz | 20.957 GHz | LPF close; HPF still stuck high. Equal S21/S31 crossing around 25.915 GHz at -10.22 dB. |
| `split_down_aggressive/lpf_widths_4p0_hpf_g312_1p5` | LPF widths 4x + `L4_g312g=0.6mm` | pass | 26.800 GHz | 17.867 GHz | LPF overshoots below 18.5; HPF still stuck high. Equal crossing around 25.270 GHz at -14.40 dB. |

## Current Conclusion

LPF right edge can be moved near 18.5 GHz using X-width scaling. Interpolating between 3x and 4x LPF widths suggests the LPF width scale for `S31` right 3 dB near 18.5 GHz is roughly 3.8x.

HPF lower edge is the blocking issue. The best safe HPF-only parameter found remains `L4_g312g=0.6mm` with `S21` first 3 dB around 27.1 GHz. Other tested HPF gap/width changes either move the edge upward, distort the response, or fail the solve.

Next useful step is not another blind scalar sweep of the tested safe HPF gaps. To reach 18.5 GHz, the HPF branch likely needs a length/topology-level scaling, which requires first parameterizing the affected ports and air box so Y-direction geometry changes do not leave terminals floating.
