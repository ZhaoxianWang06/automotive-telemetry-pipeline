import os

import pandas as pd


class TelemetryParser:

  def __init__(self, can_log_path: str, telemetry_path: str):
    self.can_path = can_log_path
    self.telemetry_path = telemetry_path

  def process(self) -> pd.DataFrame:
    print("--> 正在解析热管理 CAN 与控制器遥测...")

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

    required_can = {
        "timestamp",
        "pump_cmd",
        "pump_actual",
        "coolant_temp",
        "fan_cmd",
    }
    required_tel = {"timestamp", "battery_temp", "thermal_state"}
    missing_can = required_can - set(df_can.columns)
    missing_tel = required_tel - set(df_tel.columns)
    if missing_can:
      raise ValueError(f"CAN log missing columns: {sorted(missing_can)}")
    if missing_tel:
      raise ValueError(
          f"Firmware telemetry missing columns: {sorted(missing_tel)}"
      )

    df_can["time"] = df_can["timestamp"] / 1000.0
    df_tel["time"] = df_tel["timestamp"] / 1000.0

    df_can = df_can.sort_values("time").drop_duplicates(subset=["time"])
    df_tel = df_tel.sort_values("time").drop_duplicates(subset=["time"])

    merged_df = pd.merge_asof(
        df_tel,
        df_can,
        on="time",
        direction="nearest",
        tolerance=0.05,
    )

    merged_df = merged_df.interpolate(method="linear").fillna(0)
    print(
        f"--> 日志对齐成功，合并后数据集大小: {merged_df.shape[0]} 行记录"
    )
    return merged_df
