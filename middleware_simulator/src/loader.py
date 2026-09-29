import os

import yaml


def _load_yaml(path: str) -> dict:
  with open(path, "r", encoding="utf-8") as f:
    return yaml.safe_load(f)


def _resolve(base_dir: str, rel: str) -> str:
  if os.path.isabs(rel):
    return rel
  return os.path.normpath(os.path.join(base_dir, rel))


def load_deployment(deploy_path: str) -> dict:
  deploy_path = os.path.abspath(deploy_path)
  deploy_dir = os.path.dirname(deploy_path)
  deploy = _load_yaml(deploy_path)

  graph_rel = None
  for rel in deploy.get("imports", []):
    if str(rel).endswith("activity_graph.yaml"):
      graph_rel = rel
      break
  if not graph_rel:
    raise ValueError("deployment YAML must import an activity_graph")

  graph_path = _resolve(deploy_dir, graph_rel)
  graph_dir = os.path.dirname(graph_path)
  graph = _load_yaml(graph_path)

  activities = {}
  for rel in graph.get("imports", []):
    if not str(rel).endswith(".activity.yaml"):
      continue
    path = _resolve(graph_dir, rel)
    name = os.path.basename(path).replace(".activity.yaml", "")
    activities[name] = _load_yaml(path)

  importance = {}
  deploy_to = {}
  for row in deploy.get("activity_deployment", []):
    importance[row["activity_instance"]] = int(row.get("importance", 0))
    deploy_to[row["activity_instance"]] = row.get("deploy_to")

  return {
      "deploy": deploy,
      "graph": graph,
      "activities": activities,
      "importance": importance,
      "deploy_to": deploy_to,
      "graph_path": graph_path,
      "deploy_path": deploy_path,
  }
