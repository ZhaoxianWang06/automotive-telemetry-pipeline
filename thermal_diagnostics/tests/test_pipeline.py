import os
import struct

import pandas as pd
import pytest

from thermal_diag.bus_log_parser import BusLogParser
from thermal_diag.can_codec import BATTERY_ID, unpack_frame
from thermal_diag.diagnosis_report import DiagnosisReport
from thermal_diag.firmware_fault_detector import FirmwareFaultDetector
from thermal_diag.thermal_features import ThermalFeatureExtractor


def _write_legacy_csvs(raw_dir: str) -> None:
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


def _write_frame_csvs(raw_dir: str) -> None:
  batt = struct.pack("<h6x", 4300)
  cool_ok = struct.pack("<hH12x", 3800, 2500)
  cool_stuck = struct.pack("<hH12x", 3850, 800)
  cmd = struct.pack("<HHB3x", 6500, 5500, 1)
  frames = pd.DataFrame(
      [
          {"timestamp_ms": 0, "bus": "can0", "can_id": "0x310", "is_fd": 0, "dlc": 8, "payload_hex": batt.hex()},
          {"timestamp_ms": 0, "bus": "can1", "can_id": "0x320", "is_fd": 1, "dlc": 16, "payload_hex": cool_ok.hex()},
          {"timestamp_ms": 0, "bus": "can0", "can_id": "0x330", "is_fd": 0, "dlc": 8, "payload_hex": cmd.hex()},
          {"timestamp_ms": 40, "bus": "can0", "can_id": "0x310", "is_fd": 0, "dlc": 8, "payload_hex": batt.hex()},
          {"timestamp_ms": 40, "bus": "can1", "can_id": "0x320", "is_fd": 1, "dlc": 16, "payload_hex": cool_stuck.hex()},
          {"timestamp_ms": 40, "bus": "can0", "can_id": "0x330", "is_fd": 0, "dlc": 8, "payload_hex": cmd.hex()},
      ]
  )
  tel = pd.DataFrame(
      {
          "timestamp_ms": [0, 20, 40],
          "state_id": [1, 1, 1],
          "state_name": ["ELEVATED", "ELEVATED", "ELEVATED"],
          "previous_state_name": ["ELEVATED", "ELEVATED", "ELEVATED"],
          "transition_reason": ["", "", ""],
          "battery_temp": [43.0, 43.1, 43.2],
          "pump_cmd": [65.0, 65.0, 65.0],
          "fan_cmd": [55.0, 55.0, 55.0],
      }
  )
  truth = pd.DataFrame(
      {
          "timestamp_ms": [0, 20, 40],
          "fault_type": ["none", "stuck_pump", "stuck_pump"],
          "active": [0, 1, 1],
      }
  )
  frames.to_csv(os.path.join(raw_dir, "can_bus_log.csv"), index=False)
  tel.to_csv(os.path.join(raw_dir, "firmware_telemetry.csv"), index=False)
  truth.to_csv(os.path.join(raw_dir, "fault_ground_truth.csv"), index=False)


def test_parser_requires_input_files(tmp_path):
  parser = BusLogParser(
      str(tmp_path / "missing_can.csv"),
      str(tmp_path / "missing_tel.csv"),
  )
  with pytest.raises(FileNotFoundError):
    parser.process()


def test_can_codec_roundtrip():
  payload = struct.pack("<h6x", 4250)
  decoded = unpack_frame(BATTERY_ID, payload.hex())
  assert decoded["battery_temp"] == pytest.approx(42.5)


def test_pipeline_aligns_physics_and_detects(tmp_path):
  raw_dir = tmp_path / "raw"
  raw_dir.mkdir()
  _write_legacy_csvs(str(raw_dir))

  parser = BusLogParser(
      str(raw_dir / "can_bus_log.csv"),
      str(raw_dir / "firmware_telemetry.csv"),
  )
  df_aligned = parser.process()
  assert not df_aligned.empty
  assert {"time", "pump_cmd", "pump_actual", "battery_temp"}.issubset(df_aligned.columns)

  df_enriched = ThermalFeatureExtractor(df_aligned).compute_metrics()
  assert "control_latency_proxy" in df_enriched.columns
  assert "temp_rate_of_change" in df_enriched.columns

  df_anomalies, summary = FirmwareFaultDetector(df_enriched).detect()
  assert "is_anomaly" in df_anomalies.columns
  assert "root_cause_tag" in df_anomalies.columns
  assert summary["total_samples"] == len(df_anomalies)
  assert summary["anomaly_count"] >= 0
  assert "intermittent_clusters" in summary

  output_dir = tmp_path / "output"
  output_dir.mkdir()
  DiagnosisReport(df_anomalies, summary).generate_report(str(output_dir))
  assert (output_dir / "firmware_anomaly_report.png").is_file()
  assert (output_dir / "summary_report.txt").is_file()
  assert (output_dir / "dynamic_features.csv").is_file()


def test_frame_log_detects_stuck_pump(tmp_path):
  raw_dir = tmp_path / "raw"
  raw_dir.mkdir()
  _write_frame_csvs(str(raw_dir))
  df = BusLogParser(
      str(raw_dir / "can_bus_log.csv"),
      str(raw_dir / "firmware_telemetry.csv"),
      str(raw_dir / "fault_ground_truth.csv"),
  ).process()
  df = ThermalFeatureExtractor(df).compute_metrics()
  df, summary = FirmwareFaultDetector(df).detect()
  assert summary["anomaly_count"] >= 1
  assert (df["root_cause_tag"] == "Actuator_Stuck_Or_Intermittent").any()
