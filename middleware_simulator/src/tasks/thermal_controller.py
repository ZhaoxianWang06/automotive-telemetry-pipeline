from __future__ import annotations

import csv
import os

STATE_NAMES = {
    0: "NORMAL",
    1: "ELEVATED",
    2: "DERATE_FALLBACK",
}


class ThermalController:

  def __init__(self):
    self._writer = None
    self._file = None
    self._state = 0

  def _ensure(self, ctx: dict) -> None:
    if self._writer is not None:
      return
    path = os.path.join(ctx["data_dir"], "raw", "firmware_telemetry.csv")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    self._file = open(path, "w", newline="", encoding="utf-8")
    self._writer = csv.DictWriter(
        self._file,
        fieldnames=[
            "timestamp_ms",
            "state_id",
            "state_name",
            "previous_state_name",
            "transition_reason",
            "battery_temp",
            "pump_cmd",
            "fan_cmd",
        ],
    )
    self._writer.writeheader()

  def close(self) -> None:
    if self._file is not None:
      self._file.close()
      self._file = None

  def _policy(self, battery_temp: float) -> tuple[float, float, int, str]:
    if battery_temp < 46.0:
      return 25.0, 20.0, 0, "battery_below_46C"
    if battery_temp < 54.0:
      return 65.0, 55.0, 1, "battery_between_46_54C"
    return 100.0, 90.0, 2, "battery_above_54C_derate"

  def step(self, t_ms: int, inputs: dict, ctx: dict) -> dict:
    batt = inputs.get("battery_in") or {}
    battery_temp = float(batt.get("battery_temp", 40.0))
    pump_cmd, fan_cmd, state, reason = self._policy(battery_temp)
    previous = STATE_NAMES[self._state]
    transition = reason if state != self._state else ""
    self._state = state

    self._ensure(ctx)
    self._writer.writerow({
        "timestamp_ms": t_ms,
        "state_id": state,
        "state_name": STATE_NAMES[state],
        "previous_state_name": previous,
        "transition_reason": transition,
        "battery_temp": f"{battery_temp:.4f}",
        "pump_cmd": pump_cmd,
        "fan_cmd": fan_cmd,
    })
    self._file.flush()

    return {
        "output": {
            "pump_cmd": pump_cmd,
            "fan_cmd": fan_cmd,
            "thermal_state": state,
        }
    }
