import pandas as pd


class VehiclePhysicsEngine:

  def __init__(self, df: pd.DataFrame):
    self.df = df

  def compute_metrics(self) -> pd.DataFrame:
    print("--> 正在计算热管理回路物理特征...")

    self.df["temp_rate_of_change"] = (
        self.df["battery_temp"].diff() / self.df["time"].diff()
    )
    self.df["coolant_rate_of_change"] = (
        self.df["coolant_temp"].diff() / self.df["time"].diff()
    )
    self.df["pump_tracking_error"] = (
        self.df["pump_cmd"] - self.df["pump_actual"]
    ).abs()
    self.df["control_latency_proxy"] = self.df["pump_tracking_error"]

    print("--> 物理特征工程计算完毕。")
    return self.df
