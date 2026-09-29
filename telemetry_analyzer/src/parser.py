import os

import pandas as pd

from src.can_codec import BATTERY_ID, CMD_ID, COOLANT_ID, unpack_frame

STATE_NAMES = {
    0: "NORMAL",
    1: "ELEVATED",
    2: "DERATE_FALLBACK",
}


class TelemetryParser:

  def __init__(self, can_log_path: str, telemetry_path: str, truth_path: str | None = None):
    self.can_path = can_log_path
    self.telemetry_path = telemetry_path
    if truth_path is None:
      truth_path = os.path.join(os.path.dirname(can_log_path), "fault_ground_truth.csv")
    self.truth_path = truth_path

  def process(self) -> pd.DataFrame:
    print("--> 正在解析 CAN/CAN FD 帧与固件状态机日志...")

    if not os.path.isfile(self.can_path):
      raise FileNotFoundError(
          f"CAN log not found: {self.can_path}. Run the middleware simulator first."
      )
    if not os.path.isfile(self.telemetry_path):
      raise FileNotFoundError(
          f"Firmware telemetry not found: {self.telemetry_path}. "
          "Run the middleware simulator first."
      )

    df_can = pd.read_csv(self.can_path)
    df_tel = pd.read_csv(self.telemetry_path)
    streams = self._streams_from_can(df_can)
    firmware = self._normalize_firmware(df_tel)
    merged = self._resample_align(streams, firmware)

    if os.path.isfile(self.truth_path):
      truth = pd.read_csv(self.truth_path)
      tcol = "timestamp_ms" if "timestamp_ms" in truth.columns else "timestamp"
      truth = truth.rename(columns={tcol: "timestamp_ms"})
      truth["time"] = truth["timestamp_ms"] / 1000.0
      truth = truth.sort_values("time")
      merged = pd.merge_asof(
          merged.sort_values("time"),
          truth[["time", "fault_type", "active"]].sort_values("time"),
          on="time",
          direction="nearest",
          tolerance=0.02,
      )
      merged["fault_type"] = merged["fault_type"].fillna("none")
      merged["active"] = merged["active"].fillna(0).astype(int)
    else:
      merged["fault_type"] = "none"
      merged["active"] = 0

    numeric = merged.select_dtypes(include="number")
    merged[numeric.columns] = numeric.interpolate(method="linear")
    merged = merged.ffill()
    needed = [c for c in ("pump_cmd", "pump_actual", "battery_temp", "coolant_temp") if c in merged.columns]
    merged = merged.dropna(subset=needed)
    print(f"--> 日志对齐成功，{merged.shape[0]} 行 @ 100 Hz 网格")
    return merged

  def _parse_can_id(self, value) -> int:
    if isinstance(value, str):
      return int(value, 16)
    return int(value)

  def _asof(self, left: pd.DataFrame, right: pd.DataFrame) -> pd.DataFrame:
    if right is None or right.empty:
      return left
    return pd.merge_asof(
        left.sort_values("time"),
        right.sort_values("time"),
        on="time",
        direction="nearest",
        tolerance=0.05,
    )

  def _streams_from_can(self, df_can: pd.DataFrame) -> dict:
    if "payload_hex" not in df_can.columns:
      tcol = "timestamp_ms" if "timestamp_ms" in df_can.columns else "timestamp"
      required = {"pump_cmd", "pump_actual", "coolant_temp", "fan_cmd"}
      missing = required - set(df_can.columns)
      if missing:
        raise ValueError(f"CAN log missing columns: {sorted(missing)}")
      out = df_can.copy()
      out["time"] = out[tcol].astype(int) / 1000.0
      batt = None
      if "battery_temp" in out.columns:
        batt = out[["time", "battery_temp"]].copy()
      loop = out[["time", "coolant_temp", "pump_actual"]].copy()
      cmd = out[["time", "pump_cmd", "fan_cmd"]].copy()
      if "thermal_state" in out.columns:
        cmd["thermal_state"] = out["thermal_state"]
      return {"battery": batt, "coolant": loop, "cmd": cmd}

    tcol = "timestamp_ms" if "timestamp_ms" in df_can.columns else "timestamp"
    buckets = {BATTERY_ID: [], COOLANT_ID: [], CMD_ID: []}
    for _, row in df_can.iterrows():
      can_id = self._parse_can_id(row["can_id"])
      decoded = unpack_frame(can_id, str(row["payload_hex"]))
      decoded["time"] = int(row[tcol]) / 1000.0
      buckets[can_id].append(decoded)
    return {
        "battery": pd.DataFrame(buckets[BATTERY_ID]),
        "coolant": pd.DataFrame(buckets[COOLANT_ID]),
        "cmd": pd.DataFrame(buckets[CMD_ID]),
    }

  def _normalize_firmware(self, df_tel: pd.DataFrame) -> pd.DataFrame:
    tcol = "timestamp_ms" if "timestamp_ms" in df_tel.columns else "timestamp"
    out = df_tel.copy()
    out["time"] = out[tcol].astype(int) / 1000.0
    if "state_id" in out.columns:
      out["thermal_state"] = out["state_id"].astype(int)
    elif "thermal_state" in out.columns:
      out["thermal_state"] = out["thermal_state"].astype(int)
    else:
      raise ValueError("firmware log needs state_id or thermal_state")
    if "state_name" not in out.columns:
      out["state_name"] = out["thermal_state"].map(STATE_NAMES).fillna("UNKNOWN")
    for col in ("previous_state_name", "transition_reason"):
      if col not in out.columns:
        out[col] = ""
    cols = [
        "time",
        "thermal_state",
        "state_name",
        "previous_state_name",
        "transition_reason",
    ]
    if "battery_temp" in out.columns:
      cols.append("battery_temp")
    return out[cols].sort_values("time").drop_duplicates("time")

  def _resample_align(self, streams: dict, firmware: pd.DataFrame) -> pd.DataFrame:
    times = [firmware["time"].min(), firmware["time"].max()]
    for df in streams.values():
      if df is not None and not df.empty:
        times.extend([df["time"].min(), df["time"].max()])
    t0 = int(round(min(times) * 1000))
    t1 = int(round(max(times) * 1000))
    grid = pd.DataFrame({"timestamp_ms": range(t0, t1 + 1, 10)})
    grid["time"] = grid["timestamp_ms"] / 1000.0

    merged = grid
    cmd = streams.get("cmd")
    if cmd is not None and not cmd.empty and "thermal_state" in cmd.columns:
      cmd = cmd.drop(columns=["thermal_state"])
    merged = self._asof(merged, streams.get("battery"))
    merged = self._asof(merged, streams.get("coolant"))
    merged = self._asof(merged, cmd)
    fw = firmware.rename(columns={"battery_temp": "battery_temp_fw"})
    merged = self._asof(merged, fw)
    if "battery_temp" not in merged.columns and "battery_temp_fw" in merged.columns:
      merged["battery_temp"] = merged["battery_temp_fw"]
    elif "battery_temp_fw" in merged.columns:
      merged["battery_temp"] = merged["battery_temp"].combine_first(merged["battery_temp_fw"])
    return merged
