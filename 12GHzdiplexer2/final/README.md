# Diplexer HPF — Final Design

**Source case:** `r27_c1y022`  **Date:** 2026-04-28

## Files
| 文件 | 说明 |
|------|------|
| `diplexer_HPF_final.aedt` | HFSS 项目文件（可直接打开仿真） |
| `diplexer_HPF_final.s3p` | 仿真 S 参数结果（0–40 GHz） |
| `diplexer_HPF_final.svg` | S 参数曲线图 |
| `parameters.json` | 完整参数表与性能指标 |

## Key Parameters

| 参数 | 值 | 说明 |
|------|----|------|
| `w_sub12G` | 1.700 mm | 基板宽度（固定） |
| `w_line12g` | 0.395 mm | 主线宽（固定） |
| LPF 缩放因子 k | **0.90** | 均匀缩放 LPF 各元件长度 |
| `w_C412g = w_C212g` | **1.450 mm** | LPF 并联电容宽度 |
| `L4_g312g` | **0.850 mm** | HPF stub L4 耦合间隙位置 |
| `L2_g312g` | **0.750 mm** | HPF stub L2 耦合间隙位置 |
| `index1` | **0.600** | HPF 耦合系数 |
| `w_C1_y` | **0.220 mm** | HPF 输入电容 y 方向尺寸 |

## Performance vs Targets

| 指标 | 结果 | 目标 | 达标 |
|------|------|------|------|
| 交叉频率 | **18.552 GHz** | ≥ 18.5 GHz | ✓ |
| S31 @ 19 GHz | **−10.8 dB** | ≤ −10 dB | ✓ |
| S31 @ 20 GHz | **−15.8 dB** | ≤ −10 dB | ✓ |
| 通带波纹 20–25 GHz | **0.6 dB** | ≤ 1 dB | ✓ |
| 通带波纹 20–28 GHz | **1.1 dB** | ~1 dB | ✓ |
| 最小插损（20 GHz+） | −3.1 dB | — | — |

## Design Notes
- LPF 采用均匀 k=0.90 缩短方案（相较 185g 非均匀分布更稳定）
- w_C=1.45 mm 提供足够 S31 带外抑制，消除 18–20 GHz 阻带隆起
- w_C1_y=0.22 mm 平衡通带波纹与交叉频率
- L4/L2 不对称（0.85/0.75）微调交叉点位置
