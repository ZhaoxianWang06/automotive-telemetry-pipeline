"""
Author: [你的名字]
Description: 模拟特斯拉车辆固件与遥测数据的全链路分析系统，打通日志解析、物理对齐、异常诊断。
"""

import os

from src.anomaly_detector import FirmwareAnomalyDetector
from src.parser import TelemetryParser
from src.physics_engine import VehiclePhysicsEngine
from src.reporter import AnalysisReporter


def _data_paths():
  data_dir = os.environ.get("DATA_DIR", "data")
  output_dir = os.environ.get("OUTPUT_DIR", "output")
  return {
      "can": os.path.join(data_dir, "raw", "can_bus_log.csv"),
      "telemetry": os.path.join(data_dir, "raw", "firmware_telemetry.csv"),
      "output": output_dir,
  }


def run_pipeline():
  print("=== [Step 0] 初始化 Tesla 固件遥测数据分析全链路流水线 ===")
  paths = _data_paths()

  parser = TelemetryParser(
      can_log_path=paths["can"],
      telemetry_path=paths["telemetry"],
  )
  df_aligned = parser.process()

  physics = VehiclePhysicsEngine(df_aligned)
  df_enriched = physics.compute_metrics()

  detector = FirmwareAnomalyDetector(df_enriched)
  df_anomalies, summary_stats = detector.detect()

  os.makedirs(paths["output"], exist_ok=True)
  reporter = AnalysisReporter(df_anomalies, summary_stats)
  reporter.generate_report(output_dir=paths["output"])
  print("=== [Pipeline Success] 全链路分析完成，报告已生成！ ===")
  return summary_stats


if __name__ == "__main__":
  run_pipeline()
