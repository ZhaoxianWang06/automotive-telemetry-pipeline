"""Pack/unpack thermal signals as classic CAN and CAN FD frames."""

from __future__ import annotations

import struct

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
