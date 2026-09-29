"""Tick scheduler: cyclic tasks publish last-value samples; gateway packs CAN/FD."""

from __future__ import annotations

import csv
import os

import numpy as np

from thermal_mw.can_codec import BATTERY_ID, CMD_ID, COOLANT_ID
from thermal_mw.loader import load_deployment
from thermal_mw.scenarios import fault_type_at, resolve_scenario
from thermal_mw.tasks import TASK_TYPES


class MiddlewareRuntime:

  def __init__(self, deploy_path: str):
    self.model = load_deployment(deploy_path)

  def _print_architecture(self, scenario_name: str) -> None:
    graph = self.model["graph"]
    print(f"=== [Thermal Middleware] {graph.get('project')} ===")
    print(f"=== [Scenario] {scenario_name} ===")
    print("=== [Deployment] ===")
    for row in self.model["deploy"].get("activity_deployment", []):
      print(
          f"    {row['activity_instance']} -> {row.get('deploy_to')} "
          f"(importance {row.get('importance')})"
      )
    print("=== [Activity Graph] last-value COM ===")
    for inst in graph.get("activity_instances", []):
      for conn in inst.get("connections") or []:
        print(f"    {conn['from']} --> {inst['name']}.{conn['to']}")
    print("=== [CAN / CAN FD] ===")
    for name, iface in self.model["interfaces"].items():
      kind = "CAN FD" if iface.get("is_fd") else "CAN"
      print(
          f"    {iface.get('bus')} {iface.get('can_id')} {kind} "
          f"dlc={iface.get('dlc')} {iface.get('cycle_time_ms')}ms ({name})"
      )

  def _write_architecture_dot(self, data_dir: str) -> None:
    graph = self.model["graph"]
    lines = [
        "digraph ThermalMiddleware {",
        "  rankdir=LR;",
        '  node [shape=box, fontname="Helvetica"];',
    ]
    for inst in graph.get("activity_instances", []):
      ecu = self.model["deploy_to"].get(inst["name"], "")
      lines.append(f'  {inst["name"]} [label="{inst["name"]}\\n{inst["type"]}\\n{ecu}"];')
    for inst in graph.get("activity_instances", []):
      for conn in inst.get("connections") or []:
        src = str(conn["from"]).split(".", 1)[0]
        lines.append(f'  {src} -> {inst["name"]} [label="{conn["to"]}"];')
    lines.append("}")
    out_dir = os.path.join(data_dir, "raw")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "architecture.dot")
    with open(path, "w", encoding="utf-8") as f:
      f.write("\n".join(lines) + "\n")
    print(f"=== [Architecture] wrote {path} (Graphviz optional) ===")

  def _open_ground_truth(self, data_dir: str):
    path = os.path.join(data_dir, "raw", "fault_ground_truth.csv")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    handle = open(path, "w", newline="", encoding="utf-8")
    writer = csv.DictWriter(
        handle,
        fieldnames=["timestamp_ms", "fault_type", "active"],
    )
    writer.writeheader()
    return handle, writer

  def _can_cycles(self) -> dict:
    interfaces = self.model["interfaces"]
    defaults = {BATTERY_ID: 10, COOLANT_ID: 10, CMD_ID: 20}
    mapping = {
        "BatteryTempMsg": BATTERY_ID,
        "CoolantLoopMsg": COOLANT_ID,
        "ThermalMgrCmdMsg": CMD_ID,
    }
    cycles = dict(defaults)
    for name, can_id in mapping.items():
      iface = interfaces.get(name) or {}
      if iface.get("cycle_time_ms") is not None:
        cycles[can_id] = int(iface["cycle_time_ms"])
    return cycles

  def execute(self) -> None:
    graph = self.model["graph"]
    sim = graph.get("simulation", {})
    duration_sec = float(os.environ.get("DURATION_SEC", sim.get("duration_sec", 30)))
    duration_ms = int(duration_sec * 1000)
    tick_ms = int(sim.get("tick_ms", 10))
    rng = np.random.default_rng(int(sim.get("seed", 42)))
    data_dir = os.environ.get("DATA_DIR", "data")
    scenario_name = os.environ.get("SCENARIO", sim.get("scenario", "intermittent_pump"))
    scenario = resolve_scenario(scenario_name)

    self._print_architecture(scenario_name)
    self._write_architecture_dot(data_dir)

    instances = list(graph.get("activity_instances", []))
    instances.sort(
        key=lambda i: self.model["importance"].get(i["name"], 0),
        reverse=True,
    )

    runnables = {}
    for inst in instances:
      type_name = inst["type"]
      activity = self.model["activities"][type_name]
      r_type = activity["runnable_instances"][0]["type"]
      if r_type not in TASK_TYPES:
        raise KeyError(f"no Python task: {r_type}")
      runnables[inst["name"]] = TASK_TYPES[r_type]()

    bus = {}
    ctx = {
        "rng": rng,
        "data_dir": data_dir,
        "tick_ms": tick_ms,
        "scenario": scenario,
        "can_jitter_ms": int(sim.get("can_jitter_ms", 1)),
        "can_cycles_ms": self._can_cycles(),
    }
    gt_file, gt_writer = self._open_ground_truth(data_dir)

    print(
        f"=== [Scheduler] tick={tick_ms} ms, duration={duration_ms} ms, "
        f"rate={1000 // tick_ms} Hz grid ==="
    )

    t = 0
    try:
      while t <= duration_ms:
        fault = fault_type_at(t, scenario)
        gt_writer.writerow({
            "timestamp_ms": t,
            "fault_type": fault,
            "active": int(fault != "none"),
        })

        for inst in instances:
          activity = self.model["activities"][inst["type"]]
          stim = activity.get("stimulus", {})
          cycle_ms = int(stim.get("cycle_ms", tick_ms))
          offset_ms = int(stim.get("offset_ms", 0))
          if t < offset_ms or (t - offset_ms) % cycle_ms != 0:
            continue

          inbound = {}
          for conn in inst.get("connections") or []:
            src_name, src_port = str(conn["from"]).split(".", 1)
            inbound[conn["to"]] = bus.get((src_name, src_port))

          outputs = runnables[inst["name"]].step(t, inbound, ctx)
          for port, payload in (outputs or {}).items():
            bus[(inst["name"], port)] = payload
        t += tick_ms
    finally:
      gt_file.close()
      for r in runnables.values():
        close = getattr(r, "close", None)
        if close:
          close()

    print("=== [Thermal Middleware] CAN/FD + firmware + ground truth written to DATA_DIR ===")
