# 车载热管理时序日志与固件诊断流水线

**Vehicle thermal time-series logs and firmware diagnosis pipeline**

本仓库是一个汽车软件演示项目。它用软件模拟电池热管理闭环，生成高频 **CAN / CAN FD** 总线帧和底层固件状态机日志，再从带噪声的原始信号中提取动态特征，定位执行器偶发故障与固件降级（fallback）状态。

This is a automotive demo: a thermal-control loop emits high-rate bus and firmware logs; an offline analyzer recovers dynamics and flags actuator glitches and derate states.

---

## 它做什么 / What it does

1. **生成大规模、高频时序** — 默认 10 ms 网格（100 Hz），CAN 信号 50–100 Hz；可配置时长（如 30 s / 120 s）与多种故障场景。  
2. **从混沌信号提取车辆/热动态特征** — 解码帧、多速率对齐、中值滤波、泵跟踪误差、温升率、热惯性。  
3. **定位固件异常与偶发故障** — 重建 `NORMAL → ELEVATED → DERATE_FALLBACK`，用跟踪误差阈值标出卡泵/间歇卡泵。  
4. **热管理中间件外形** — 周期任务 + last-value 软件总线 + 双 ECU 部署 YAML，用来**产数并展示框架**，不是某家量产中间件的再实现。

数据流：

```text
thermal_middleware  →  data/raw/*.csv  →  thermal_diagnostics  →  output/
     周期调度与组帧              总线+固件+标签              解码 / 特征 / 诊断
```

---

## 快速开始 / Quick start

需要 Git 与 Docker Compose。克隆后在仓库根目录：

```bash
docker compose up --build
```

默认场景 `intermittent_pump`、时长 30 秒。覆盖方式（会传入 compose）：

```bash
# Linux / macOS
SCENARIO=mixed DURATION_SEC=120 docker compose up --build

# Windows PowerShell
$env:SCENARIO="thermal_derate"
$env:DURATION_SEC="60"
docker compose up --build
```

成功后查看：

- `data/raw/can_bus_log.csv` — 总线帧  
- `data/raw/firmware_telemetry.csv` — 固件状态机  
- `data/raw/fault_ground_truth.csv` — 仿真注入标签（评估用）  
- `data/raw/architecture.dot` — Graphviz 源（可选：`dot -Tpng ...`）  
- `output/summary_report.txt`、`firmware_anomaly_report.png`、`dynamic_features.csv`

本机 Python 3.11 复现见下文「不使用 Docker」。更细的模拟器/分析器说明见各自目录 README。

---

## 仓库结构 / Repository layout

```text
.
├── docker-compose.yml          # 先跑 thermal_middleware，成功后再跑 thermal_diagnostics
├── .github/workflows/ci.yml
├── data/raw/                   # 运行时日志（csv 不入库）
├── output/                     # 报告（png 不入库）
├── thermal_middleware/         # ECU 侧：调度 + 热闭环任务 + 组帧
└── thermal_diagnostics/        # 离线：解析、特征、诊断
```

### 根目录文件

| 文件 | 作用 |
|------|------|
| `README.md` | 本说明 |
| `docker-compose.yml` | 编排 `thermal_middleware` 与 `thermal_diagnostics`；挂载 `./data`、`./output`；环境变量 `SCENARIO`、`DURATION_SEC` |
| `.gitignore` | 忽略缓存、虚拟环境、生成的 csv/png；保留目录占位 `.gitkeep` |
| `.github/workflows/ci.yml` | CI：诊断镜像内 `pytest`，再端到端跑中间件与诊断 |

### `thermal_middleware/` — ECU 热管理中间件

详见 [`thermal_middleware/README.md`](thermal_middleware/README.md)。

| 路径 | 作用 |
|------|------|
| `main.py` | 入口：读 `DEPLOY_CONFIG`，启动 `MiddlewareRuntime` |
| `Dockerfile` | Python 3.11 镜像，非 root 运行 `python main.py` |
| `.dockerignore` | 减小构建上下文 |
| `requirements.txt` | PyYAML、NumPy、pandas |
| `config/deployment/Thermal.deploy.yaml` | 活动实例映射到两个模拟 ECU，同 tick 优先级 `importance` |
| `config/deployment/Thermal.activity_graph.yaml` | 工程名、仿真步长/时长/场景、活动实例与端口连线 |
| `config/interfaces/ThermalInterfaces.interfaces.yaml` | 报文：CAN ID、CAN FD、DLC、周期、信号名 |
| `config/activities/*.activity.yaml` | 周期、端口、内部 runnable 实例 |
| `config/runnables/*.runnable.yaml` | runnable 端口契约（无算法） |
| `thermal_mw/loader.py` | 加载部署 YAML → activity graph → activities / interfaces |
| `thermal_mw/runtime.py` | 周期调度、last-value COM、ground truth 与 `architecture.dot` |
| `thermal_mw/scenarios.py` | 场景：升温、卡泵窗、传感器尖峰、丢帧率 |
| `thermal_mw/can_codec.py` | 热管理信号 ↔ CAN/FD payload |
| `thermal_mw/tasks/` | 四个 SWC 的 Python 实现 |
| `thermal_mw/tasks/battery_temp_sensor.py` | 合成电池温度 |
| `thermal_mw/tasks/coolant_plant.py` | 冷却对象与卡泵 |
| `thermal_mw/tasks/thermal_controller.py` | 阈值策略与固件状态日志 |
| `thermal_mw/tasks/can_gateway.py` | 组帧、抖动、丢帧 |
| `thermal_mw/tasks/__init__.py` | 类型名 → 任务类 |
| `thermal_mw/__init__.py` | Python 包 |

### `thermal_diagnostics/` — 离线诊断

详见 [`thermal_diagnostics/README.md`](thermal_diagnostics/README.md)。

| 路径 | 作用 |
|------|------|
| `main.py` | 解析 → 特征 → 检测 → 报告 |
| `Dockerfile` | 含 matplotlib；默认证诊断，CI 可 `pytest` |
| `requirements.txt` | pandas、numpy、matplotlib、pytest |
| `pytest.ini` | `pythonpath = .` |
| `thermal_diag/can_codec.py` | 解码（与中间件编码一致，镜像独立） |
| `thermal_diag/bus_log_parser.py` | 帧或宽表 → 100 Hz 网格 |
| `thermal_diag/thermal_features.py` | 中值滤波与差分特征 |
| `thermal_diag/firmware_fault_detector.py` | 跟踪误差、状态机、偶发簇 |
| `thermal_diag/diagnosis_report.py` | PNG、摘要、特征 CSV |
| `tests/test_pipeline.py` | 编解码、遗留 CSV、帧日志卡泵 |

---

## 中间件如何工作 / Middleware (bonus)

YAML **只声明**周期、端口和部署；算法在 `thermal_mw/tasks/`。

运行时：按 `importance` 排序同一 tick 内的活动；每个活动按 `cycle_ms` / `offset_ms` 触发；输入来自软件总线上游端口的**最新样本**（last-value COM）。热闭环允许反馈，调度按周期触发而非 DAG 拓扑排序。

两路 ECU 仅用于展示部署视图：`thermal_ecu`（传感/对象/策略）、`gateway_ecu`（组帧落盘）。

总线映射（见 interfaces YAML 与 `can_codec.py`）：

| CAN ID | 总线 | 类型 | 周期 | 内容 |
|--------|------|------|------|------|
| 0x310 | can0 | Classic CAN | 10 ms | 电池温度 |
| 0x320 | can1 | CAN FD | 10 ms | 冷却液温度、泵实际开度 |
| 0x330 | can0 | Classic CAN | 20 ms | 泵/风扇指令、热状态枚举 |

载荷为定点整数（温度/百分比 ×100），便于离线确定性解码。

### 场景 `SCENARIO`

| 名称 | 含义 |
|------|------|
| `nominal` | 弱故障、低丢帧 |
| `intermittent_pump` | 默认：多段短时卡泵 + 温度尖峰 |
| `stuck_pump` | 较长窗口卡泵 |
| `thermal_derate` | 升温更快，便于进入 `DERATE_FALLBACK` |
| `mixed` | 间歇卡泵 + 较强热负荷 |

`DURATION_SEC` 覆盖 YAML 里的 `simulation.duration_sec`。

---

## 分析管线 / Analyzer pipeline

1. **Parse** — 按 CAN ID 解码，对齐到 10 ms 网格；固件日志提供状态名与跳变原因。  
2. **Features** — `pump_tracking_error`、`temp_rate_of_change`、`thermal_inertia` 等。  
3. **Detect** — 指令开度较高且跟踪误差 ≥ 12% 视为执行器异常；统计进入 state 2 的次数与异常时间簇。  
4. **Report** — 泵、温度、状态机三图 + 文字结论。

固件策略阈值（控制器）：&lt;46 °C → `NORMAL`；46–54 °C → `ELEVATED`；≥54 °C → `DERATE_FALLBACK`。

---

## 不使用 Docker / Run without Docker

在仓库根目录创建 `data/raw` 与 `output`（若尚未存在）。

```bash
cd thermal_middleware
python -m pip install -r requirements.txt
set DATA_DIR=..\data
set SCENARIO=intermittent_pump
set DURATION_SEC=30
python main.py
```

Linux/macOS 使用 `export DATA_DIR=...`。然后：

```bash
cd ../thermal_diagnostics
python -m pip install -r requirements.txt
set DATA_DIR=..\data
set OUTPUT_DIR=..\output
python main.py
python -m pytest
```

必须在**各组件目录**执行，保证 `from thermal_mw...` / `from thermal_diag...` 与相对路径 `config/` 正确。

---

## 设计边界 / Non-goals

- 不是真实 ECU、SocketCAN 或某商用 AUTOSAR / 中间件栈的替代品。  
- 不包含任何主机厂专有标定、商标或内部工具链。  
- YAML 形态参考了业界常见的「接口 / 周期任务 / 部署」分层，算法与物理模型是本项目自己的热管理仿真。

---


