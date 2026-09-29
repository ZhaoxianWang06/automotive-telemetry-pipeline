import pandas as pd


class ThermalFeatureExtractor:

  def __init__(self, df: pd.DataFrame):
    self.df = df

  def compute_metrics(self) -> pd.DataFrame:
    print("--> 正在从含噪声的原始信号提取热管理动态特征...")

    for col in ("battery_temp", "coolant_temp", "pump_cmd", "pump_actual"):
      if col in self.df.columns:
        self.df[f"{col}_filt"] = self.df[col].rolling(window=5, min_periods=1).median()

    dt = self.df["time"].diff()
    dt = dt.mask(dt == 0).bfill().fillna(0.01)
    self.df["temp_rate_of_change"] = self.df["battery_temp_filt"].diff() / dt
    self.df["coolant_rate_of_change"] = self.df["coolant_temp_filt"].diff() / dt
    self.df["pump_tracking_error"] = (
        self.df["pump_cmd_filt"] - self.df["pump_actual_filt"]
    ).abs()
    self.df["control_latency_proxy"] = self.df["pump_tracking_error"]
    self.df["thermal_inertia"] = (
        self.df["temp_rate_of_change"] - self.df["coolant_rate_of_change"]
    ).abs()
    self.df["pump_error_short"] = self.df["pump_tracking_error"].rolling(
        window=8, min_periods=3
    ).median()

    print("--> 物理特征工程计算完毕。")
    return self.df
