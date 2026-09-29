"""Named fault campaigns for generating labeled high-rate logs."""

from __future__ import annotations


def resolve_scenario(name: str) -> dict:
  presets = {
      "nominal": {
          "battery_rise": 0.12,
          "plant_heat": 1.4,
          "stuck_windows_ms": [],
          "sensor_spikes_ms": [],
          "drop_frame_rate": 0.01,
      },
      "intermittent_pump": {
          "battery_rise": 0.18,
          "plant_heat": 1.8,
          "stuck_windows_ms": [(4200, 4480), (11100, 11440), (19800, 20120)],
          "sensor_spikes_ms": [7600, 15200],
          "drop_frame_rate": 0.02,
      },
      "stuck_pump": {
          "battery_rise": 0.2,
          "plant_heat": 2.0,
          "stuck_windows_ms": [(8000, 16000)],
          "sensor_spikes_ms": [],
          "drop_frame_rate": 0.015,
      },
      "thermal_derate": {
          "battery_rise": 0.85,
          "plant_heat": 3.2,
          "stuck_windows_ms": [],
          "sensor_spikes_ms": [9000],
          "drop_frame_rate": 0.02,
      },
      "mixed": {
          "battery_rise": 0.72,
          "plant_heat": 2.8,
          "stuck_windows_ms": [(5000, 5280), (14000, 14360)],
          "sensor_spikes_ms": [8200, 17500],
          "drop_frame_rate": 0.03,
      },
  }
  if name not in presets:
    raise KeyError(f"unknown scenario '{name}', expected one of {sorted(presets)}")
  cfg = dict(presets[name])
  cfg["name"] = name
  return cfg


def fault_type_at(t_ms: int, scenario: dict) -> str:
  for start, end in scenario.get("stuck_windows_ms") or []:
    if start <= t_ms < end:
      return "stuck_pump"
  spikes = scenario.get("sensor_spikes_ms") or []
  if any(abs(t_ms - spike) <= 20 for spike in spikes):
    return "sensor_spike"
  return "none"
