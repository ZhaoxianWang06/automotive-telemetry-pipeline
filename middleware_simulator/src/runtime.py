"""Tick scheduler: cyclic activities publish last-value samples on a software COM bus."""

from __future__ import annotations

import os

import numpy as np

from src.loader import load_deployment
from src.runnables import RUNNABLE_TYPES


class MiddlewareRuntime:

  def __init__(self, deploy_path: str):
    self.model = load_deployment(deploy_path)

  def _print_architecture(self) -> None:
    graph = self.model["graph"]
    print(f"=== [Thermal Middleware] {graph.get('project')} ===")
    print("=== [Deployment] ===")
    for row in self.model["deploy"].get("activity_deployment", []):
      print(
          f"    {row['activity_instance']} -> {row.get('deploy_to')} "
          f"(importance {row.get('importance')})"
      )
    print("=== [Activity Graph] COM wiring ===")
    for inst in graph.get("activity_instances", []):
      for conn in inst.get("connections") or []:
        print(f"    {conn['from']} --> {inst['name']}.{conn['to']}")

  def execute(self) -> None:
    self._print_architecture()
    graph = self.model["graph"]
    sim = graph.get("simulation", {})
    duration_ms = int(float(sim.get("duration_sec", 10)) * 1000)
    tick_ms = int(sim.get("tick_ms", 10))
    rng = np.random.default_rng(int(sim.get("seed", 42)))
    data_dir = os.environ.get("DATA_DIR", "data")

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
      if r_type not in RUNNABLE_TYPES:
        raise KeyError(f"no Python runnable: {r_type}")
      runnables[inst["name"]] = RUNNABLE_TYPES[r_type]()

    bus = {}
    ctx = {"rng": rng, "data_dir": data_dir, "tick_ms": tick_ms}

    print(
        f"=== [Scheduler] tick={tick_ms} ms, duration={duration_ms} ms, "
        "last-value COM ==="
    )

    t = 0
    while t <= duration_ms:
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

    for r in runnables.values():
      close = getattr(r, "close", None)
      if close:
        close()

    print("=== [Thermal Middleware] CAN log + telemetry written to DATA_DIR ===")
