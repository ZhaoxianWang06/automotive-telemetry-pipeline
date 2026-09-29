"""Offline diagnosis: parse CAN/FD + firmware logs, extract thermal dynamics, locate fallback faults."""

import os

from thermal_diag.bus_log_parser import BusLogParser
from thermal_diag.diagnosis_report import DiagnosisReport
from thermal_diag.firmware_fault_detector import FirmwareFaultDetector
from thermal_diag.thermal_features import ThermalFeatureExtractor


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

  parser = BusLogParser(
      can_log_path=paths["can"],
      telemetry_path=paths["telemetry"],
      truth_path=paths["truth"],
  )
  df_aligned = parser.process()

  features = ThermalFeatureExtractor(df_aligned)
  df_enriched = features.compute_metrics()

  detector = FirmwareFaultDetector(df_enriched)
  df_anomalies, summary_stats = detector.detect()

  os.makedirs(paths["output"], exist_ok=True)
  reporter = DiagnosisReport(df_anomalies, summary_stats)
  reporter.generate_report(output_dir=paths["output"])
  print("=== [Pipeline Success] 全链路分析完成，报告已生成！ ===")
  return summary_stats


if __name__ == "__main__":
  run_pipeline()
