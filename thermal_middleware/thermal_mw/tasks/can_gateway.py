from __future__ import annotations

import csv
import os

from thermal_mw.can_codec import (
    BATTERY_ID,
    CMD_ID,
    COOLANT_ID,
    SPECS,
    pack_battery_temp,
    pack_coolant_loop,
    pack_thermal_cmd,
)


class CanGateway:

  def __init__(self):
    self._writer = None
    self._file = None

  def _ensure(self, ctx: dict) -> None:
    if self._writer is not None:
      return
    path = os.path.join(ctx["data_dir"], "raw", "can_bus_log.csv")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    self._file = open(path, "w", newline="", encoding="utf-8")
    self._writer = csv.DictWriter(
        self._file,
        fieldnames=["timestamp_ms", "bus", "can_id", "is_fd", "dlc", "payload_hex"],
    )
    self._writer.writeheader()

  def close(self) -> None:
    if self._file is not None:
      self._file.close()
      self._file = None

  def _emit(self, t_ms: int, can_id: int, payload: bytes, ctx: dict) -> None:
    spec = SPECS[can_id]
    if ctx["rng"].random() < ctx["scenario"]["drop_frame_rate"]:
      return
    jitter = int(ctx["rng"].integers(0, max(1, ctx.get("can_jitter_ms", 1) + 1)))
    self._writer.writerow({
        "timestamp_ms": t_ms + jitter,
        "bus": spec["bus"],
        "can_id": f"0x{can_id:X}",
        "is_fd": int(spec["is_fd"]),
        "dlc": spec["dlc"],
        "payload_hex": payload.hex(),
    })

  def step(self, t_ms: int, inputs: dict, ctx: dict) -> dict:
    self._ensure(ctx)
    batt = inputs.get("battery_in") or {}
    loop = inputs.get("loop_in") or {}
    cmd = inputs.get("cmd_in") or {}

    cycles = ctx["can_cycles_ms"]
    if batt and t_ms % cycles[BATTERY_ID] == 0:
      self._emit(t_ms, BATTERY_ID, pack_battery_temp(float(batt["battery_temp"])), ctx)
    if loop and t_ms % cycles[COOLANT_ID] == 0:
      self._emit(
          t_ms,
          COOLANT_ID,
          pack_coolant_loop(float(loop["coolant_temp"]), float(loop["pump_actual"])),
          ctx,
      )
    if cmd and t_ms % cycles[CMD_ID] == 0:
      self._emit(
          t_ms,
          CMD_ID,
          pack_thermal_cmd(
              float(cmd.get("pump_cmd", 0.0)),
              float(cmd.get("fan_cmd", 0.0)),
              int(cmd.get("thermal_state", 0)),
          ),
          ctx,
      )
    self._file.flush()
    return {}
