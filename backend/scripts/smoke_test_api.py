from __future__ import annotations

import sys
from typing import Any

import requests

BASE = "http://127.0.0.1:8000"
API = f"{BASE}/api/v1"


def must_ok(resp: requests.Response, label: str) -> Any:
    if not (200 <= resp.status_code < 300):
        raise RuntimeError(f"{label} failed: status={resp.status_code}, body={resp.text}")
    return resp.json()


def run() -> None:
    print("=== Smoke Test Start ===")
    health = must_ok(requests.get(f"{BASE}/healthz", timeout=10), "healthz")
    assert health.get("status") == "ok"
    print("healthz=ok")

    papers = must_ok(requests.get(f"{API}/papers", timeout=10), "list papers")
    print(f"papers_count={len(papers)}")

    nodes = must_ok(requests.get(f"{API}/graph/nodes", timeout=10), "list graph nodes")
    print(f"graph_nodes_count={len(nodes)}")
    if not nodes:
        raise RuntimeError("graph nodes empty, run seed_demo_data.py first")

    node_ids = [n["id"] for n in nodes[:8]]
    subgraph = must_ok(
        requests.get(f"{API}/graph/subgraph", params=[("node_ids", n) for n in node_ids], timeout=10),
        "subgraph",
    )
    print(f"subgraph_nodes={len(subgraph['nodes'])}")
    print(f"subgraph_edges={len(subgraph['edges'])}")

    experiments = must_ok(requests.get(f"{API}/experiments", timeout=10), "list experiments")
    print(f"experiments_count={len(experiments)}")
    if not experiments:
        raise RuntimeError("experiments empty, run seed_demo_data.py first")

    experiment_metric_counts: list[tuple[int, int]] = []
    for experiment in experiments:
        exp_id = experiment["id"]
        metric_rows = must_ok(
            requests.get(f"{API}/experiments/{exp_id}/metrics", timeout=10),
            "experiment metrics",
        )
        experiment_metric_counts.append((exp_id, len(metric_rows)))

    non_empty_experiments = [exp_id for exp_id, count in experiment_metric_counts if count > 0]
    if not non_empty_experiments:
        raise RuntimeError("all experiments are empty, run seed_demo_data.py first")

    first_exp_id = non_empty_experiments[0]
    print(f"experiment_{first_exp_id}_metrics={dict(experiment_metric_counts)[first_exp_id]}")

    latex_payload = {
        "experiment_ids": non_empty_experiments[:2],
        "caption": "Smoke test table.",
        "label": "tab:smoke-test",
        "precision": 2,
    }
    latex = must_ok(
        requests.post(f"{API}/latex/generate", json=latex_payload, timeout=10),
        "latex generate",
    )
    print(f"latex_models={len(latex['model_names'])}")
    print(f"latex_metrics={len(latex['metric_names'])}")
    print("=== Smoke Test Passed ===")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:  # noqa: BLE001
        print(f"smoke_test_failed={exc}")
        sys.exit(1)
