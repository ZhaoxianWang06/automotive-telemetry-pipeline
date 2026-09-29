# 热管理中间件 / Thermal middleware (ECU application)

本目录对应车载软件里的 **Application SWC + COM 调度**：产生总线与固件日志。  
YAML 声明周期、端口与 ECU 部署；Python 包 `thermal_mw` 实现控制与组帧。

入口：在本目录执行 `python main.py`。  
环境变量：`DATA_DIR`、`DEPLOY_CONFIG`、`SCENARIO`、`DURATION_SEC`。

配置文件说明见下表。运行时读取 `Thermal.deploy.yaml` 及其 import；`config/runnables/*.runnable.yaml` 为端口契约对照，不参与加载。

| 路径 | 作用 |
|------|------|
| `config/deployment/` | 部署与 activity graph |
| `config/interfaces/` | CAN / CAN FD 报文目录 |
| `config/activities/` | 周期活动 |
| `config/runnables/` | runnable 端口类型 |
| `thermal_mw/loader.py` | YAML 加载 |
| `thermal_mw/runtime.py` | 周期调度 |
| `thermal_mw/scenarios.py` | 故障场景 |
| `thermal_mw/can_codec.py` | 组帧 |
| `thermal_mw/tasks/` | 传感器 / 对象 / 控制器 / 网关 |
