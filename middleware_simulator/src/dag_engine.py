from src.runtime import MiddlewareRuntime


class DAGEngine:
  """Backward-compatible name: deployment-driven thermal runtime."""

  def __init__(self, config_path: str):
    self._runtime = MiddlewareRuntime(config_path)

  def execute(self):
    self._runtime.execute()
