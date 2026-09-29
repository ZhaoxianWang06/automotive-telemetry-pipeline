"""Pack/unpack thermal signals as classic CAN and CAN FD frames."""

from __future__ import annotations

import struct

# Scaled integers keep payloads deterministic and easy to decode offline.
TEMP_SCALE = 100.0
PCT_SCALE = 100.0

BATTERY_ID = 0x310
COOLANT_ID = 0x320
CMD_ID = 0x330

SPECS = {
    BATTERY_ID: {"bus": "can0", "is_fd": False, "dlc": 8, "name": "BatteryTempMsg"},
    COOLANT_ID: {"bus": "can1", "is_fd": True, "dlc": 16, "name": "CoolantLoopMsg"},
    CMD_ID: {"bus": "can0", "is_fd": False, "dlc": 8, "name": "ThermalMgrCmdMsg"},
}


def _clamp_i16(value: float) -> int:
  return max(-32768, min(32767, int(round(value))))


def _clamp_u16(value: float) -> int:
  return max(0, min(65535, int(round(value))))


def pack_battery_temp(battery_temp: float) -> bytes:
  raw = _clamp_i16(battery_temp * TEMP_SCALE)
  return struct.pack("<h6x", raw)


def pack_coolant_loop(coolant_temp: float, pump_actual: float) -> bytes:
  t_raw = _clamp_i16(coolant_temp * TEMP_SCALE)
  p_raw = _clamp_u16(pump_actual * PCT_SCALE)
  return struct.pack("<hH12x", t_raw, p_raw)


def pack_thermal_cmd(pump_cmd: float, fan_cmd: float, thermal_state: int) -> bytes:
  p_raw = _clamp_u16(pump_cmd * PCT_SCALE)
  f_raw = _clamp_u16(fan_cmd * PCT_SCALE)
  state = max(0, min(255, int(thermal_state)))
  return struct.pack("<HHB3x", p_raw, f_raw, state)


def unpack_frame(can_id: int, payload_hex: str) -> dict:
  data = bytes.fromhex(payload_hex)
  if can_id == BATTERY_ID:
    (raw,) = struct.unpack_from("<h", data)
    return {"battery_temp": raw / TEMP_SCALE}
  if can_id == COOLANT_ID:
    t_raw, p_raw = struct.unpack_from("<hH", data)
    return {
        "coolant_temp": t_raw / TEMP_SCALE,
        "pump_actual": p_raw / PCT_SCALE,
    }
  if can_id == CMD_ID:
    p_raw, f_raw, state = struct.unpack_from("<HHB", data)
    return {
        "pump_cmd": p_raw / PCT_SCALE,
        "fan_cmd": f_raw / PCT_SCALE,
        "thermal_state": int(state),
    }
  raise ValueError(f"unknown CAN id: 0x{can_id:X}")
