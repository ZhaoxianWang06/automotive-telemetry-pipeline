"""Cyclic runnables: last-value COM on each scheduler tick."""

from __future__ import annotations

import csv
import math
import os


class BatteryTempSensor:

  def step(self, t_ms: int, inputs: dict, ctx: dict) -> dict:
    t = t_ms / 1000.0
    rng = ctx["rng"]
    battery_temp = (
        42.0
        + 0.55 * t
        + 3.5 * math.sin(t / 2.5)
        + float(rng.normal(0, 0.15))
    )
    return {"output": {"battery_temp": battery_temp}}


class CoolantPlant:

  def __init__(self):
    self.coolant_temp = 38.0

  def step(self, t_ms: int, inputs: dict, ctx: dict) -> dict:
    cmd = inputs.get("pump_cmd_in") or {}
    pump_cmd = float(cmd.get("pump_cmd", 20.0))
    rng = ctx["rng"]
    dt = ctx["tick_ms"] / 1000.0

    pump_actual = pump_cmd + float(rng.normal(0, 1.2))
    # Stuck pump: command not followed (thermal loop fault injection)
    if 1600 <= t_ms < 1820:
      pump_actual = 8.0

    pump_actual = max(0.0, min(100.0, pump_actual))
    heat = 2.2
    cooling = 0.045 * pump_actual
    self.coolant_temp += dt * (heat - cooling) + float(rng.normal(0, 0.02))

    return {
        "output": {
            "coolant_temp": self.coolant_temp,
            "pump_actual": pump_actual,
        }
    }


class ThermalController:

  def __init__(self):
    self._tel_path = None
    self._tel_writer = None
    self._tel_file = None

  def _ensure_tel(self, ctx: dict) -> None:
    if self._tel_writer is not None:
      return
    path = os.path.join(ctx["data_dir"], "raw", "firmware_telemetry.csv")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    self._tel_path = path
    self._tel_file = open(path, "w", newline="", encoding="utf-8")
    self._tel_writer = csv.DictWriter(
        self._tel_file,
        fieldnames=["timestamp", "battery_temp", "thermal_state"],
    )
    self._tel_writer.writeheader()

  def close(self) -> None:
    if self._tel_file is not None:
      self._tel_file.close()
      self._tel_file = None

  def step(self, t_ms: int, inputs: dict, ctx: dict) -> dict:
    batt = inputs.get("battery_in") or {}
    battery_temp = float(batt.get("battery_temp", 40.0))

    if battery_temp < 46.0:
      pump_cmd, fan_cmd, thermal_state = 25.0, 20.0, 0
    elif battery_temp < 54.0:
      pump_cmd, fan_cmd, thermal_state = 65.0, 55.0, 1
    else:
      pump_cmd, fan_cmd, thermal_state = 100.0, 90.0, 2

    self._ensure_tel(ctx)
    self._tel_writer.writerow({
        "timestamp": t_ms,
        "battery_temp": battery_temp,
        "thermal_state": thermal_state,
    })
    self._tel_file.flush()

    return {
        "output": {
            "pump_cmd": pump_cmd,
            "fan_cmd": fan_cmd,
            "thermal_state": thermal_state,
        }
    }


class CanGateway:

  def __init__(self):
    self._path = None
    self._writer = None
    self._file = None

  def _ensure(self, ctx: dict) -> None:
    if self._writer is not None:
      return
    path = os.path.join(ctx["data_dir"], "raw", "can_bus_log.csv")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    self._path = path
    self._file = open(path, "w", newline="", encoding="utf-8")
    self._writer = csv.DictWriter(
        self._file,
        fieldnames=[
            "timestamp",
            "pump_cmd",
            "pump_actual",
            "coolant_temp",
            "fan_cmd",
        ],
    )
    self._writer.writeheader()

  def close(self) -> None:
    if self._file is not None:
      self._file.close()
      self._file = None

  def step(self, t_ms: int, inputs: dict, ctx: dict) -> dict:
    cmd = inputs.get("cmd_in") or {}
    loop = inputs.get("loop_in") or {}
    self._ensure(ctx)
    self._writer.writerow({
        "timestamp": t_ms,
        "pump_cmd": float(cmd.get("pump_cmd", 0.0)),
        "pump_actual": float(loop.get("pump_actual", 0.0)),
        "coolant_temp": float(loop.get("coolant_temp", 0.0)),
        "fan_cmd": float(cmd.get("fan_cmd", 0.0)),
    })
    self._file.flush()
    return {}


RUNNABLE_TYPES = {
    "BatteryTempSensor": BatteryTempSensor,
    "CoolantPlant": CoolantPlant,
    "ThermalController": ThermalController,
    "CanGateway": CanGateway,
}
