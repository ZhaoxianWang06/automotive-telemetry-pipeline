"""
Parse high-rate CAN/FD + firmware logs, extract thermal dynamics, locate fallback and intermittent faults.
"""

import os

from src.anomaly_detector import FirmwareAnomalyDetector
from src.parser import TelemetryParser
from src.physics_engine import VehiclePhysicsEngine
from src.reporter import AnalysisReporter


def _data_paths():
  data_dir = os.environ.get("DATA_DIR", "data")
  output_dir = os.environ.get("OUTPUT_DIR", "output")
  raw = os.path.join(data_dir, "raw")
  return {
      "can": os.path.join(raw, "can_bus_log.csv"),
      "telemetry": os.path.join(raw, "firmware_telemetry.csv"),
      "truth": os.path.join(raw, "fault_ground_truth.csv"),
      "output": output_dir,
  }


def run_pipeline():
  print("=== [Step 1-3] CAN/FD parse → dynamics → firmware diagnosis ===")
  paths = _data_paths()

  parser = TelemetryParser(
      can_log_path=paths["can"],
      telemetry_path=paths["telemetry"],
      truth_path=paths["truth"],
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
