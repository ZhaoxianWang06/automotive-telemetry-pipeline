"""Thermal middleware entry: cyclic COM scheduler that emits CAN/FD and firmware logs."""

import os

from thermal_mw.runtime import MiddlewareRuntime


def main() -> None:
  config_path = os.environ.get(
      "DEPLOY_CONFIG",
      "config/deployment/Thermal.deploy.yaml",
  )
  MiddlewareRuntime(config_path).execute()


if __name__ == "__main__":
  main()
