import pandas as pd


STATE_NAMES = {
    0: "NORMAL",
    1: "ELEVATED",
    2: "DERATE_FALLBACK",
}


class FirmwareAnomalyDetector:

  def __init__(self, df: pd.DataFrame):
    self.df = df

  def detect(self):
    print("--> 正在定位执行器偶发故障与固件降级状态机...")

    err = self.df["pump_tracking_error"].fillna(0)
    if "thermal_state" in self.df.columns:
      self.df["thermal_state"] = pd.to_numeric(
          self.df["thermal_state"], errors="coerce"
      ).fillna(0).round().astype(int)
    abs_hit = (err >= 12.0) & (self.df["pump_cmd"].fillna(0) >= 20.0)
    self.df["is_anomaly"] = abs_hit.astype(bool)

    if "state_name" not in self.df.columns:
      self.df["state_name"] = self.df["thermal_state"].map(STATE_NAMES)
    self.df["state_name"] = self.df["state_name"].fillna(
        self.df["thermal_state"].map(STATE_NAMES)
    )

    prev_state = self.df["thermal_state"].shift(1)
    self.df["state_entered"] = (
        self.df["thermal_state"].notna()
        & prev_state.notna()
        & (self.df["thermal_state"] != prev_state)
    )
    self.df["illegal_transition"] = (
        self.df["state_entered"]
        & (prev_state == 0)
        & (self.df["thermal_state"] == 2)
    )

    fallback = self.df["thermal_state"] == 2
    self.df["root_cause_tag"] = "Normal"
    self.df.loc[self.df["is_anomaly"] & fallback, "root_cause_tag"] = (
        "Firmware_Degraded_Protection"
    )
    self.df.loc[self.df["is_anomaly"] & ~fallback, "root_cause_tag"] = (
        "Actuator_Stuck_Or_Intermittent"
    )
    self.df.loc[self.df["illegal_transition"], "root_cause_tag"] = (
        "Illegal_State_Skip"
    )

    truth = self.df["fault_type"] if "fault_type" in self.df.columns else "none"
    if isinstance(truth, str):
      self.df["detection_match"] = False
    else:
      self.df["detection_match"] = self.df["is_anomaly"] & truth.isin(
          ["stuck_pump", "sensor_spike"]
      )

    fallback_entries = int(
        (self.df["state_entered"] & (self.df["thermal_state"] == 2)).sum()
    )
    intermittent_clusters = self._count_clusters(self.df["is_anomaly"] & ~fallback)

    summary = {
        "total_samples": len(self.df),
        "anomaly_count": int(self.df["is_anomaly"].sum()),
        "degraded_events": fallback_entries,
        "intermittent_clusters": intermittent_clusters,
        "illegal_transitions": int(self.df["illegal_transition"].sum()),
        "fallback_dwell_samples": int(fallback.sum()),
    }

    print(
        f"--> 诊断完成：异常点 {summary['anomaly_count']}，"
        f"降级进入 {summary['degraded_events']} 次，"
        f"偶发簇 {summary['intermittent_clusters']} 个。"
    )
    return self.df, summary

  def _count_clusters(self, mask: pd.Series) -> int:
    if mask.empty:
      return 0
    values = mask.fillna(False).astype(int)
    started = values.astype(bool) & ~values.shift(1, fill_value=0).astype(bool)
    return int(started.sum())
