from __future__ import annotations

import math


class BatteryTempSensor:

  def step(self, t_ms: int, inputs: dict, ctx: dict) -> dict:
    t = t_ms / 1000.0
    rng = ctx["rng"]
    scenario = ctx["scenario"]
    battery_temp = (
        41.5
        + scenario["battery_rise"] * t
        + 2.8 * math.sin(t / 2.2)
        + float(rng.normal(0, 0.18))
    )
    if any(abs(t_ms - spike) <= ctx["tick_ms"] for spike in scenario["sensor_spikes_ms"]):
      battery_temp += 7.5 + float(rng.normal(0, 0.4))
    return {"output": {"battery_temp": battery_temp}}
