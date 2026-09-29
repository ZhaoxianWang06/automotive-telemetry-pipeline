# 遥测分析器 / Telemetry analyzer

本目录**只读** `DATA_DIR/raw` 中的日志，写出 `OUTPUT_DIR` 报告。不仿真车辆。  
Reads logs only; no vehicle simulation.

入口 / Entry: `python main.py`。环境变量：`DATA_DIR`、`OUTPUT_DIR`。  
测试 / Tests: `python -m pytest`（须在本目录执行）。

---

## 源码 / Source

| 文件 | 中文 | English |
|------|------|---------|
| `main.py` | 流水线编排 | Orchestrates parse → physics → detect → report |
| `src/can_codec.py` | `unpack_frame`，与模拟器编码一致 | Decode only (duplicate of simulator codec for a separate image) |
| `src/parser.py` | 帧或旧宽表 → 100 Hz 网格；合并固件与 `fault_ground_truth.csv` | Multi-rate align via `merge_asof` |
| `src/physics_engine.py` | 窗口 5 的中值滤波；跟踪误差、温升、热惯性 | Feature columns |
| `src/anomaly_detector.py` | 跟踪误差 ≥ 12% 且指令 ≥ 20% 为异常；状态机进入/非法跳变；偶发簇 | Threshold detector + state reconstruction |
| `src/reporter.py` | 三子图 PNG、摘要 txt、特征 CSV | Artifacts |
| `src/__init__.py` | 包标记 | Package marker |
| `tests/test_pipeline.py` | 缺文件、编解码、遗留 CSV、帧日志卡泵 | Unit tests |
| `pytest.ini` | pytest 路径 | pytest config |
| `Dockerfile` | 分析镜像；可覆盖 CMD 为 `pytest` | Image |
| `requirements.txt` | 含 matplotlib、pytest | Pins |

解码后的固件状态：`0 NORMAL`，`1 ELEVATED`，`2 DERATE_FALLBACK`。
