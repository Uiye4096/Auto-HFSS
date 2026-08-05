# Configurable HFSS Core

本目录说明第一阶段代码通用化。现有 `diplexer.py` 和历史 sweep 脚本保持不变，新接口用于把同一套自动化流程迁移到其他 HFSS 工程。

## 已实现范围

- JSON 配置 HFSS 安装路径、IronPython、Design、Setup、Sweep 和端口数；
- 支持环境变量覆盖机器相关路径；
- 从基准 `.aedt` 复制生成独立 case；
- 可选地调用 `tools/aedt_inspect.py` 注入变量；
- 若任何配置变量在 AEDT 中不存在，case 立即终止；
- 通过通用 IronPython runner 无界面求解并导出 Touchstone、profile 和 convergence；
- 保存 `provenance.json`，记录基准工程、配置、变量和完整运行命令；
- 通用 Touchstone v1 解析，支持任意 N 端口及 RI、MA、DB 格式；
- 显式使用 `S(output_port, input_port)`，避免依赖硬编码列号。

尚未实现通用指标插件、批量 DOE 调度、收敛文件判定和场数据导出。这些属于后续阶段。

## 文件结构

```text
hfss_automation/
├── config.py          # 配置模型与校验
└── touchstone.py      # 通用 N-port Touchstone 读取
scripts/
└── run_hfss_generic.py # AEDT IronPython 执行器
run_configured.py       # 单 case 编排入口
examples/
└── hfss_config.example.json
tests/
├── test_config.py
└── test_touchstone.py
```

## 1. 准备配置

复制示例：

```powershell
Copy-Item examples\hfss_config.example.json my_project.json
```

修改：

```json
{
  "hfss": {
    "aedt_root": "C:/Program Files/AnsysEM/AnsysEM21.2/Win64",
    "ironpython": "C:/Program Files/AnsysEM/AnsysEM21.2/Win64/common/IronPython/ipy64.exe",
    "non_graphical": true,
    "max_parallel": 1
  },
  "project": {
    "project_file": "D:/models/baseline.aedt",
    "design": "HFSSDesign1",
    "setup": "Setup1",
    "sweep": "Sweep",
    "ports": 3,
    "output_root": "D:/models/runs",
    "variables": {
      "length": "1.20mm",
      "width": "0.40mm"
    }
  }
}
```

`project_file` 和 `output_root` 可以使用相对于配置文件的路径。路径支持 `~` 和环境变量展开。

机器相关路径也可以通过环境变量覆盖：

```powershell
$env:HFSS_AEDT_ROOT = "E:\AnsysEM\AnsysEM21.2\Win64"
$env:HFSS_IRONPYTHON = "E:\AnsysEM\AnsysEM21.2\Win64\common\IronPython\ipy64.exe"
```

## 2. 先执行 dry-run

```powershell
python run_configured.py my_project.json --dry-run --case-name smoke_test
```

该命令会：

1. 创建独立 case 目录；
2. 复制基准工程；
3. 注入并校验变量；
4. 生成 `provenance.json`；
5. 打印即将执行的 HFSS 命令；
6. 不启动 HFSS。

配置变量不存在时，命令直接失败，不会使用旧值继续求解。

## 3. 执行真实仿真

```powershell
python run_configured.py my_project.json --case-name baseline_001
```

预期输出：

```text
baseline_001/
├── project.aedt
├── updates.json
├── update_result.json
├── provenance.json
├── run.log
├── result.s3p
├── result.prof
└── result.conv
```

端口数为 N 时，Touchstone 文件名为 `result.sNp`。

## 4. 读取 Touchstone

```python
from hfss_automation import read_touchstone

data = read_touchstone("runs/baseline_001/result.s3p")
frequency_ghz = [value / 1e9 for value in data.frequency_hz]
s11_db = data.db(1, 1)
s21_db = data.db(2, 1)
s31_db = data.db(3, 1)
```

端口定义采用：

```text
S(output_port, input_port)
```

因此从端口 1 激励、端口 2 输出为 `S(2, 1)`。

## 5. 测试

基础测试不需要安装 HFSS：

```powershell
python -m unittest discover -s tests -v
```

真实 HFSS 集成测试仍需在有许可证的 Windows 工作站上执行。

## 兼容性

本阶段没有修改：

- `diplexer.py` 的参数和运行方式；
- `12GHzdiplexer/scripts/run_hfss_case.py`；
- 任何 `.aedt` 模型；
- 任何历史调参结果。

旧流程可以继续使用，新项目可以逐步迁移到配置驱动入口。
