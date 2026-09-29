import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


class AnalysisReporter:

  def __init__(self, df: pd.DataFrame, summary: dict):
    self.df = df
    self.summary = summary

  def generate_report(self, output_dir: str):
    print("--> 正在生成热管理诊断报告...")

    fig, axes = plt.subplots(3, 1, figsize=(12, 11), sharex=True)

    axes[0].plot(self.df["time"], self.df["pump_cmd"], label="Pump Cmd", color="blue", alpha=0.7)
    axes[0].plot(
        self.df["time"],
        self.df["pump_actual"],
        label="Pump Actual",
        color="green",
        alpha=0.8,
    )
    anomalies = self.df[self.df["is_anomaly"]]
    if not anomalies.empty:
      axes[0].scatter(
          anomalies["time"],
          anomalies["pump_actual"],
          color="red",
          s=12,
          label="Tracking anomaly",
          zorder=5,
      )
    axes[0].set_ylabel("Pump (%)")
    axes[0].legend(loc="upper right")
    axes[0].grid(True, linestyle="--", alpha=0.5)

    axes[1].plot(self.df["time"], self.df["battery_temp"], label="Battery Temp", color="tab:orange")
    axes[1].plot(self.df["time"], self.df["coolant_temp"], label="Coolant Temp", color="tab:cyan")
    axes[1].set_ylabel("Temp (degC)")
    axes[1].legend(loc="upper left")
    axes[1].grid(True, linestyle="--", alpha=0.5)

    axes[2].step(self.df["time"], self.df["thermal_state"], where="post", color="tab:purple")
    axes[2].set_yticks([0, 1, 2])
    axes[2].set_yticklabels(["NORMAL", "ELEVATED", "DERATE"])
    axes[2].set_ylabel("Firmware state")
    axes[2].set_xlabel("Time (s)")
    axes[2].grid(True, linestyle="--", alpha=0.5)

    fig.suptitle("Thermal logs: features, actuator faults, firmware fallback")
    chart_path = f"{output_dir}/firmware_anomaly_report.png"
    fig.savefig(chart_path, dpi=160, bbox_inches="tight")
    plt.close(fig)

    feature_cols = [
        c
        for c in [
            "time",
            "pump_cmd",
            "pump_actual",
            "pump_tracking_error",
            "temp_rate_of_change",
            "thermal_inertia",
            "thermal_state",
            "state_name",
            "is_anomaly",
            "root_cause_tag",
            "fault_type",
        ]
        if c in self.df.columns
    ]
    self.df[feature_cols].to_csv(f"{output_dir}/dynamic_features.csv", index=False)

    report_txt_path = f"{output_dir}/summary_report.txt"
    with open(report_txt_path, "w", encoding="utf-8") as f:
      f.write("=== THERMAL MANAGEMENT ANALYSIS REPORT ===\n")
      f.write(f"Total samples (100 Hz grid): {self.summary['total_samples']}\n")
      f.write(f"Detected anomalies: {self.summary['anomaly_count']}\n")
      f.write(f"Fallback state entries: {self.summary['degraded_events']}\n")
      f.write(f"Fallback dwell samples: {self.summary['fallback_dwell_samples']}\n")
      f.write(f"Intermittent actuator clusters: {self.summary['intermittent_clusters']}\n")
      f.write(f"Illegal state skips: {self.summary['illegal_transitions']}\n")
      if self.summary["anomaly_count"] == 0:
        conclusion = "No pump-tracking anomalies vs robust threshold."
      elif self.summary["degraded_events"] > 0 and self.summary["intermittent_clusters"] > 0:
        conclusion = (
            "Intermittent pump tracking faults and DERATE_FALLBACK both present."
        )
      elif self.summary["degraded_events"] > 0:
        conclusion = "Firmware entered DERATE_FALLBACK (battery temp policy)."
      else:
        conclusion = (
            "Pump cmd/actual mismatch without derate; "
            "stuck or intermittent actuator."
        )
      f.write(f"Conclusion: {conclusion}\n")

    print(f"--> 报告已成功输出至: {chart_path} 与 {report_txt_path}")
