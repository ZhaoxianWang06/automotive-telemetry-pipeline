from __future__ import annotations


class CoolantPlant:

  def __init__(self):
    self.coolant_temp = 38.0

  def step(self, t_ms: int, inputs: dict, ctx: dict) -> dict:
    cmd = inputs.get("pump_cmd_in") or {}
    pump_cmd = float(cmd.get("pump_cmd", 20.0))
    rng = ctx["rng"]
    dt = ctx["tick_ms"] / 1000.0
    scenario = ctx["scenario"]

    pump_actual = pump_cmd + float(rng.normal(0, 1.4))
    for start, end in scenario["stuck_windows_ms"]:
      if start <= t_ms < end:
        pump_actual = 8.0
        break

    pump_actual = max(0.0, min(100.0, pump_actual))
    cooling = 0.05 * pump_actual
    self.coolant_temp += dt * (scenario["plant_heat"] - cooling) + float(
        rng.normal(0, 0.03)
    )

    return {
        "output": {
            "coolant_temp": self.coolant_temp,
            "pump_actual": pump_actual,
        }
    }
