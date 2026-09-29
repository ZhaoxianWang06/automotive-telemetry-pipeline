# 热管理中间件模拟器 / Thermal middleware simulator

本目录负责**产生**总线与固件日志，并用一份 YAML 展示「周期任务 + 端口 + 部署」框架。  
This package **generates** logs. YAML names cycles, ports, and ECU mapping; Python implements the plant and policy.

入口 / Entry: `python main.py`（工作目录必须是本目录）。  
环境变量 / Env: `DATA_DIR`、`DEPLOY_CONFIG`、`SCENARIO`、`DURATION_SEC`。

---

## 配置文件 / Config YAML

| 文件 | 中文 | English |
|------|------|---------|
| `config/deployment/Thermal.deploy.yaml` | 把四个活动实例放到 `thermal_ecu` / `gateway_ecu`，`importance` 越大越先在同一 tick 执行 | Maps instances to two simulated ECUs; higher `importance` runs first in a tick |
| `config/deployment/Thermal.activity_graph.yaml` | 仿真参数（时长、tick、默认场景）、实例名、COM 连线 | Simulation settings and last-value COM wiring |
| `config/interfaces/ThermalInterfaces.interfaces.yaml` | 三种报文的 CAN ID、CAN/FD、DLC、周期、信号列表 | Message catalog used by the gateway codec |
| `config/activities/BatteryTempSensor.activity.yaml` | 100 Hz 电池温度活动，无输入 | 10 ms cyclic sensor activity |
| `config/activities/CoolantPlant.activity.yaml` | 100 Hz 冷却对象，输入泵指令 | Plant activity, pump command in |
| `config/activities/ThermalController.activity.yaml` | 50 Hz 热管理策略 | 20 ms controller activity |
| `config/activities/CanGateway.activity.yaml` | 100 Hz 网关，汇合三路采样后组帧 | Gateway activity, three inbound ports |
| `config/runnables/*.runnable.yaml` | 仅端口类型契约，与 activity 对应 | Port contracts only; no physics |

运行时**真正读取**的是 `Thermal.deploy.yaml` 及其 import 的 graph / activity / interfaces。runnable YAML 目前不参与加载，保留是为了让「类型/端口」与活动文件对照阅读。

---

## Python 源码 / Source

| 文件 | 中文 | English |
|------|------|---------|
| `main.py` | 解析 `DEPLOY_CONFIG` 并 `execute()` | CLI entry |
| `src/loader.py` | 解析部署与活动图，收集 interfaces | YAML loader |
| `src/runtime.py` | 调度循环、打印架构、写 `architecture.dot` 与 ground truth | Scheduler and artifacts |
| `src/scenarios.py` | 五种故障/热负荷预设；`fault_type_at` 打时间标签 | Scenario table and labels |
| `src/can_codec.py` | `pack_*` 组帧 | Encode payloads |
| `src/tasks/battery_temp_sensor.py` | 缓升正弦 + 高斯噪声 + 尖峰 | Synthetic battery temperature |
| `src/tasks/coolant_plant.py` | 一阶热平衡；卡泵时强制低开度 | Coolant plant + stuck pump |
| `src/tasks/thermal_controller.py` | 46/54 °C 分段；写 `firmware_telemetry.csv` | Policy and firmware CSV |
| `src/tasks/can_gateway.py` | 按报文周期发帧、抖动、丢帧；写 `can_bus_log.csv` | CAN/FD logger |
| `src/tasks/__init__.py` | `TASK_TYPES` 注册表 | Class registry |
| `src/runnables.py` | `RUNNABLE_TYPES = TASK_TYPES` | Alias |
| `src/dag_engine.py` | 旧名包装 `MiddlewareRuntime` | Legacy wrapper |
| `Dockerfile` | 镜像构建 | Image |
| `requirements.txt` | 依赖锁定 | Pins |

---

## 输出 / Outputs (`DATA_DIR/raw`)

与仓库根 README 中的 CSV 列说明一致。`architecture.dot` 可用 Graphviz 渲染，本仓库不捆绑 Graphviz。
