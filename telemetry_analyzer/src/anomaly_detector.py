import numpy as np
import pandas as pd


class FirmwareAnomalyDetector:

  def __init__(self, df: pd.DataFrame):
    self.df = df

  def detect(self):
    print('--> 正在进行固件行为异常检测与根因关联...')

    # 使用移动窗口统计法（Rolling Z-Score）检测制动压力突变或物理响应异常
    window = 20
    rolling_mean = self.df['control_latency_proxy'].rolling(window=window).mean()
    rolling_std = self.df['control_latency_proxy'].rolling(window=window).std()

    # 判定异常阈值：超过 3 倍标准差
    self.df['is_anomaly'] = (
        (self.df['control_latency_proxy'] - rolling_mean).abs()
        > (3 * rolling_std)
    )

    # 关联固件状态（例如 firmware_state == 2 代表固件进入降级保护/限功率模式）
    self.df['root_cause_tag'] = 'Normal'
    self.df.loc[
        self.df['is_anomaly'] & (self.df['thermal_state'] == 2),
        'root_cause_tag',
    ] = 'Firmware_Degraded_Protection'
    self.df.loc[
        self.df['is_anomaly'] & (self.df['thermal_state'] != 2),
        'root_cause_tag',
    ] = 'Sensor_Noise_Or_Transient_Lag'

    anomaly_count = self.df['is_anomaly'].sum()
    summary = {
        'total_samples': len(self.df),
        'anomaly_count': anomaly_count,
        'degraded_events': len(
            self.df[
                self.df['root_cause_tag'] == 'Firmware_Degraded_Protection'
            ]
        ),
    }

    print(
        f'--> 诊断完成：发现异常点 {anomaly_count} 个，其中固件降级触发事件'
        f" {summary['degraded_events']} 起。"
    )
    return self.df, summary