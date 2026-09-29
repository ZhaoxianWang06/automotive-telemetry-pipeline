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

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    axes[0].plot(
        self.df["time"],
        self.df["pump_cmd"],
        label="Pump Cmd",
        color="blue",
        alpha=0.7,
    )
    axes[0].plot(
        self.df["time"],
        self.df["pump_actual"],
        label="Pump Actual",
        color="green",
        alpha=0.8,
    )
    anomalies = self.df[self.df["is_anomaly"]]
    axes[0].scatter(
        anomalies["time"],
        anomalies["pump_actual"],
        color="red",
        label="Pump tracking anomaly",
        zorder=5,
    )
    axes[0].set_ylabel("Pump (%)")
    axes[0].legend()
    axes[0].grid(True, linestyle="--", alpha=0.5)

    axes[1].plot(
        self.df["time"],
        self.df["battery_temp"],
        label="Battery Temp",
        color="tab:orange",
    )
    axes[1].plot(
        self.df["time"],
        self.df["coolant_temp"],
        label="Coolant Temp",
        color="tab:cyan",
    )
    axes[1].set_xlabel("Time (s)")
    axes[1].set_ylabel("Temp (degC)")
    axes[1].legend()
    axes[1].grid(True, linestyle="--", alpha=0.5)

    fig.suptitle("Thermal Management Middleware Diagnostics")
    chart_path = f"{output_dir}/firmware_anomaly_report.png"
    fig.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    report_txt_path = f"{output_dir}/summary_report.txt"
    with open(report_txt_path, "w", encoding="utf-8") as f:
      f.write("=== THERMAL MANAGEMENT ANALYSIS REPORT ===\n")
      f.write(f"Total Telemetry Samples: {self.summary['total_samples']}\n")
      f.write(f"Detected Anomalies: {self.summary['anomaly_count']}\n")
      f.write(
          "Thermal Derate Protection Events:"
          f" {self.summary['degraded_events']}\n"
      )
      if self.summary["anomaly_count"] == 0:
        conclusion = "No pump-tracking anomalies vs 3-sigma baseline."
      elif self.summary["degraded_events"] > 0:
        conclusion = (
            "Pump tracking faults overlapped thermal derate (state=2)."
        )
      else:
        conclusion = (
            "Pump cmd/actual mismatch without thermal derate; "
            "likely actuator lag or injected stuck-pump."
        )
      f.write(f"Conclusion: {conclusion}\n")

    print(f"--> 报告已成功输出至: {chart_path} 与 {report_txt_path}")
