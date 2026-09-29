# 热管理离线诊断 / Thermal offline diagnostics

本目录对应产线/试验场的 **离线日志分析**（不跑 ECU 仿真）。Python 包名为 `thermal_diag`。

入口：`python main.py`。环境变量：`DATA_DIR`、`OUTPUT_DIR`。  
测试：在本目录 `python -m pytest`。

| 路径 | 作用 |
|------|------|
| `thermal_diag/bus_log_parser.py` | 总线帧与固件日志对齐 |
| `thermal_diag/thermal_features.py` | 热动态特征 |
| `thermal_diag/firmware_fault_detector.py` | 卡泵/降级/偶发簇 |
| `thermal_diag/diagnosis_report.py` | 报告产物 |
| `thermal_diag/can_codec.py` | 与中间件一致的解码 |
| `tests/test_pipeline.py` | 组件测试 |

固件状态：`0 NORMAL`，`1 ELEVATED`，`2 DERATE_FALLBACK`。
