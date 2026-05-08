# 28.5 GHz Diplexer Tuning Log

Diplexer scaled from the 18.5 GHz final design (case 087).
Scale method: all LENGTH parameters × (18.5/28.5 = 0.6491); WIDTH and k_LPF unchanged.

## Design Targets

| Metric | Target | Analogous 18.5 GHz metric |
|--------|--------|---------------------------|
| Crossing frequency | ≥ 28.5 GHz | ≥ 18.5 GHz |
| S31 @ 29 GHz | ≤ −10 dB | S31 @ 19 GHz |
| S31 @ 30 GHz | ≤ −10 dB | S31 @ 20 GHz |
| Ripple 30–38 GHz | ≤ 1 dB | Ripple 20–25 GHz |
| S11 worst (29–43 GHz) | ≤ −10 dB | S11 worst 19–28 GHz |

## Baseline Parameters (Scaled from 087)

| Parameter | 18.5 GHz (087) | → 28.5 GHz (×0.6491) | Role |
|-----------|---------------|----------------------|------|
| `L2_g3185g` | 0.780 mm | **0.506 mm** | HPF stub → crossing |
| `L4_g3185g` | 0.850 mm | **0.552 mm** | HPF stub |
| `L7_g3185g` | 0.830 mm | **0.539 mm** | HPF resonator / S11 lever |
| `L7_g4185g` | 0.520 mm | **0.338 mm** | HPF output stub |
| `l_line2185g` | 0.600 mm | **0.389 mm** | Junction line |
| `l_L5185g` | 0.696 mm | **0.452 mm** | LPF element |
| `l_C4185g` | 0.446 mm | **0.290 mm** | LPF element |
| `l_L3185g` | 0.899 mm | **0.583 mm** | LPF element |
| `l_C2185g` | 0.504 mm | **0.327 mm** | LPF element |
| `l_L1185g` | 0.667 mm | **0.433 mm** | LPF element |
| `w_C4185g` | 1.15 mm | **1.15 mm** | LPF cap width (unchanged) |
| `w_C2185g` | 1.05 mm | **1.05 mm** | LPF cap width (unchanged) |
| `k_LPF` | 0.96 | **0.96** | LPF scale factor (unchanged) |

Baseline AEDT: `final/diplexer_285g_baseline.aedt`

---

## Round 1 — sweep1：L2_g3185g sweep (2026-05-__)

### 动机
验证频率缩放是否正确，确定交叉频率位置，以及 L2_g3185g 的灵敏度。
理论预期：交叉频率应落在约 28.5 GHz 附近（若缩放正确）。

### 参数设置
- 基础：baseline (087 × 0.6491)
- `L2_g3185g`：0.45 / 0.47 / 0.49 / 0.51 / 0.53 / 0.55 / 0.57 mm

### 结果汇总

| UID | L2_g3 mm | 交叉 GHz | S31@29 dB | S31@30 dB | 波纹 dB | S11w dB | 状态 |
|-----|----------|---------|-----------|-----------|---------|---------|------|
| — | — | — | — | — | — | — | pending |

### 反思

_待填写_

---
