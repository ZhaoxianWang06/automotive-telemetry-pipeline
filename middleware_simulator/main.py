"""Thermal middleware entry: load deployment and run the cyclic COM scheduler."""

import os

from src.runtime import MiddlewareRuntime


def main() -> None:
  config_path = os.environ.get(
      "DEPLOY_CONFIG",
      "config/deployment/Thermal.deploy.yaml",
  )
  MiddlewareRuntime(config_path).execute()


if __name__ == "__main__":
  main()
