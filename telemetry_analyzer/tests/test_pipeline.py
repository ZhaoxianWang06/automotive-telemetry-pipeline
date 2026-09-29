import os

import pandas as pd
import pytest

from src.anomaly_detector import FirmwareAnomalyDetector
from src.parser import TelemetryParser
from src.physics_engine import VehiclePhysicsEngine
from src.reporter import AnalysisReporter


def _write_fixture_csvs(raw_dir: str) -> None:
  can = pd.DataFrame(
      {
          "timestamp": [0, 20, 40, 60, 80, 100],
          "pump_cmd": [20.0, 25.0, 65.0, 100.0, 100.0, 65.0],
          "pump_actual": [19.0, 24.0, 8.0, 98.0, 97.0, 64.0],
          "coolant_temp": [38.0, 38.2, 38.5, 39.0, 39.1, 39.0],
          "fan_cmd": [20.0, 20.0, 55.0, 90.0, 90.0, 55.0],
      }
  )
  tel = pd.DataFrame(
      {
          "timestamp": [0, 40, 80],
          "battery_temp": [43.0, 55.0, 52.0],
          "thermal_state": [0, 2, 1],
      }
  )
  can.to_csv(os.path.join(raw_dir, "can_bus_log.csv"), index=False)
  tel.to_csv(os.path.join(raw_dir, "firmware_telemetry.csv"), index=False)


def test_parser_requires_input_files(tmp_path):
  parser = TelemetryParser(
      str(tmp_path / "missing_can.csv"),
      str(tmp_path / "missing_tel.csv"),
  )
  with pytest.raises(FileNotFoundError):
    parser.process()


def test_pipeline_aligns_physics_and_detects(tmp_path):
  raw_dir = tmp_path / "raw"
  raw_dir.mkdir()
  _write_fixture_csvs(str(raw_dir))

  parser = TelemetryParser(
      str(raw_dir / "can_bus_log.csv"),
      str(raw_dir / "firmware_telemetry.csv"),
  )
  df_aligned = parser.process()
  assert not df_aligned.empty
  assert {"time", "pump_cmd", "pump_actual", "battery_temp"}.issubset(
      df_aligned.columns
  )

  df_enriched = VehiclePhysicsEngine(df_aligned).compute_metrics()
  assert "control_latency_proxy" in df_enriched.columns
  assert "temp_rate_of_change" in df_enriched.columns

  df_anomalies, summary = FirmwareAnomalyDetector(df_enriched).detect()
  assert "is_anomaly" in df_anomalies.columns
  assert "root_cause_tag" in df_anomalies.columns
  assert summary["total_samples"] == len(df_anomalies)
  assert summary["anomaly_count"] >= 0

  output_dir = tmp_path / "output"
  output_dir.mkdir()
  AnalysisReporter(df_anomalies, summary).generate_report(str(output_dir))
  assert (output_dir / "firmware_anomaly_report.png").is_file()
  assert (output_dir / "summary_report.txt").is_file()
