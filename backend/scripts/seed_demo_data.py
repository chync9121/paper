from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any

import requests

BASE_URL = "http://127.0.0.1:8000/api/v1"


@dataclass
class Ctx:
    paper_ids: dict[str, int]
    node_ids: dict[str, int]
    experiment_ids: dict[str, int]
    run_ids: dict[str, int]


def api(method: str, path: str, **kwargs: Any) -> requests.Response:
    url = f"{BASE_URL}{path}"
    response = requests.request(method, url, timeout=30, **kwargs)
    return response


def check_backend() -> None:
    health = requests.get("http://127.0.0.1:8000/healthz", timeout=10)
    health.raise_for_status()


def create_paper(payload: dict[str, Any]) -> int:
    resp = api("POST", "/papers", json=payload)
    resp.raise_for_status()
    return resp.json()["id"]


def ensure_paper(payload: dict[str, Any]) -> int:
    resp = api("GET", "/papers")
    resp.raise_for_status()
    for item in resp.json():
        if item["title"] == payload["title"]:
            return item["id"]
    return create_paper(payload)


def find_node(node_type: str, name: str) -> int | None:
    resp = api("GET", "/graph/nodes", params={"node_type": node_type, "q": name})
    resp.raise_for_status()
    items = resp.json()
    for item in items:
        if item["name"] == name and item["node_type"] == node_type:
            return item["id"]
    return None


def ensure_node(payload: dict[str, Any]) -> int:
    existing = find_node(payload["node_type"], payload["name"])
    if existing is not None:
        return existing
    resp = api("POST", "/graph/nodes", json=payload)
    if resp.status_code == 409:
        existing = find_node(payload["node_type"], payload["name"])
        if existing is not None:
            return existing
    resp.raise_for_status()
    return resp.json()["id"]


def ensure_edge(payload: dict[str, Any]) -> None:
    resp = api("POST", "/graph/edges", json=payload)
    if resp.status_code in (200, 201, 409):
        return
    resp.raise_for_status()


def create_experiment(payload: dict[str, Any]) -> int:
    resp = api("POST", "/experiments", json=payload)
    resp.raise_for_status()
    return resp.json()["id"]


def ensure_experiment(payload: dict[str, Any]) -> int:
    resp = api("GET", "/experiments")
    resp.raise_for_status()
    for item in resp.json():
        if item["name"] == payload["name"]:
            return item["id"]
    return create_experiment(payload)


def create_run(experiment_id: int, payload: dict[str, Any]) -> int:
    resp = api("POST", f"/experiments/{experiment_id}/runs", json=payload)
    resp.raise_for_status()
    return resp.json()["id"]


def ensure_run(experiment_id: int, payload: dict[str, Any]) -> tuple[int, bool]:
    resp = api("GET", f"/experiments/{experiment_id}/runs")
    resp.raise_for_status()
    for item in resp.json():
        if item.get("run_name") == payload.get("run_name"):
            return item["id"], False
    return create_run(experiment_id, payload), True


def add_metrics(run_id: int, metrics: list[dict[str, Any]]) -> None:
    resp = api("POST", f"/experiments/runs/{run_id}/metrics/batch", json={"metrics": metrics})
    resp.raise_for_status()


def seed() -> Ctx:
    ctx = Ctx(paper_ids={}, node_ids={}, experiment_ids={}, run_ids={})

    papers = [
        {
            "key": "resnet",
            "title": "Deep Residual Learning for Image Recognition",
            "venue": "CVPR",
            "year": 2016,
            "url": "https://arxiv.org/abs/1512.03385",
            "abstract": "Residual connections enable training very deep convolutional networks.",
        },
        {
            "key": "vit",
            "title": "An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale",
            "venue": "ICLR",
            "year": 2021,
            "url": "https://arxiv.org/abs/2010.11929",
            "abstract": "Vision Transformer applies pure transformer architectures to image classification.",
        },
        {
            "key": "convnext",
            "title": "A ConvNet for the 2020s",
            "venue": "CVPR",
            "year": 2022,
            "url": "https://arxiv.org/abs/2201.03545",
            "abstract": "ConvNeXt modernizes ConvNet design and matches transformer-style performance.",
        },
    ]
    for paper in papers:
        paper_id = ensure_paper({k: v for k, v in paper.items() if k != "key"})
        ctx.paper_ids[paper["key"]] = paper_id

    nodes = [
        {"key": "task_cls", "node_type": "task", "name": "Image Classification"},
        {"key": "dset_c10", "node_type": "dataset", "name": "CIFAR-10"},
        {"key": "dset_c100", "node_type": "dataset", "name": "CIFAR-100"},
        {"key": "dset_imagenet", "node_type": "dataset", "name": "ImageNet-1K"},
        {"key": "metric_acc1", "node_type": "metric", "name": "Top-1 Accuracy"},
        {"key": "metric_f1", "node_type": "metric", "name": "Macro-F1"},
        {
            "key": "model_resnet50",
            "node_type": "model",
            "name": "ResNet-50",
            "paper_id": ctx.paper_ids["resnet"],
        },
        {
            "key": "model_vitb16",
            "node_type": "model",
            "name": "ViT-B/16",
            "paper_id": ctx.paper_ids["vit"],
        },
        {
            "key": "model_convnext",
            "node_type": "model",
            "name": "ConvNeXt-Tiny",
            "paper_id": ctx.paper_ids["convnext"],
        },
    ]

    for node in nodes:
        payload = {
            "node_type": node["node_type"],
            "name": node["name"],
            "paper_id": node.get("paper_id"),
            "extra": {},
        }
        ctx.node_ids[node["key"]] = ensure_node(payload)

    edges = [
        {
            "source_node_id": ctx.node_ids["model_resnet50"],
            "target_node_id": ctx.node_ids["task_cls"],
            "relation_type": "applies_to",
            "paper_id": ctx.paper_ids["resnet"],
        },
        {
            "source_node_id": ctx.node_ids["model_vitb16"],
            "target_node_id": ctx.node_ids["task_cls"],
            "relation_type": "applies_to",
            "paper_id": ctx.paper_ids["vit"],
        },
        {
            "source_node_id": ctx.node_ids["model_convnext"],
            "target_node_id": ctx.node_ids["task_cls"],
            "relation_type": "applies_to",
            "paper_id": ctx.paper_ids["convnext"],
        },
        {
            "source_node_id": ctx.node_ids["model_resnet50"],
            "target_node_id": ctx.node_ids["dset_c10"],
            "relation_type": "evaluated_on",
        },
        {
            "source_node_id": ctx.node_ids["model_vitb16"],
            "target_node_id": ctx.node_ids["dset_imagenet"],
            "relation_type": "evaluated_on",
        },
        {
            "source_node_id": ctx.node_ids["model_convnext"],
            "target_node_id": ctx.node_ids["dset_imagenet"],
            "relation_type": "evaluated_on",
        },
        {
            "source_node_id": ctx.node_ids["model_convnext"],
            "target_node_id": ctx.node_ids["model_resnet50"],
            "relation_type": "compares_with",
        },
    ]

    for edge in edges:
        ensure_edge(edge)

    exp1 = ensure_experiment(
        {
            "name": "CIFAR Bench Baselines",
            "description": "Baseline comparison on CIFAR-10 and CIFAR-100",
            "task_name": "Image Classification",
            "owner": "demo-seed",
        }
    )
    ctx.experiment_ids["exp_cifar"] = exp1

    exp2 = ensure_experiment(
        {
            "name": "ImageNet Transfer Study",
            "description": "Model transfer and scaling comparison on ImageNet-1K",
            "task_name": "Image Classification",
            "owner": "demo-seed",
        }
    )
    ctx.experiment_ids["exp_imagenet"] = exp2

    run_specs = [
        {
            "key": "run_resnet_c10",
            "experiment_id": exp1,
            "run_name": "ResNet50-CIFAR10",
            "model_node_id": ctx.node_ids["model_resnet50"],
            "dataset_node_id": ctx.node_ids["dset_c10"],
            "metrics": [
                {
                    "metric_node_id": ctx.node_ids["metric_acc1"],
                    "metric_name": "Top-1 Accuracy",
                    "metric_value": 95.2,
                    "higher_is_better": True,
                    "stage": "best",
                },
                {
                    "metric_node_id": ctx.node_ids["metric_f1"],
                    "metric_name": "Macro-F1",
                    "metric_value": 94.7,
                    "higher_is_better": True,
                    "stage": "best",
                },
            ],
        },
        {
            "key": "run_vit_c10",
            "experiment_id": exp1,
            "run_name": "ViTB16-CIFAR10",
            "model_node_id": ctx.node_ids["model_vitb16"],
            "dataset_node_id": ctx.node_ids["dset_c10"],
            "metrics": [
                {
                    "metric_node_id": ctx.node_ids["metric_acc1"],
                    "metric_name": "Top-1 Accuracy",
                    "metric_value": 97.1,
                    "higher_is_better": True,
                    "stage": "best",
                },
                {
                    "metric_node_id": ctx.node_ids["metric_f1"],
                    "metric_name": "Macro-F1",
                    "metric_value": 96.8,
                    "higher_is_better": True,
                    "stage": "best",
                },
            ],
        },
        {
            "key": "run_convnext_imgnet",
            "experiment_id": exp2,
            "run_name": "ConvNeXtTiny-ImageNet1K",
            "model_node_id": ctx.node_ids["model_convnext"],
            "dataset_node_id": ctx.node_ids["dset_imagenet"],
            "metrics": [
                {
                    "metric_node_id": ctx.node_ids["metric_acc1"],
                    "metric_name": "Top-1 Accuracy",
                    "metric_value": 82.7,
                    "higher_is_better": True,
                    "stage": "best",
                },
                {
                    "metric_node_id": ctx.node_ids["metric_f1"],
                    "metric_name": "Macro-F1",
                    "metric_value": 81.5,
                    "higher_is_better": True,
                    "stage": "best",
                },
            ],
        },
    ]

    for spec in run_specs:
        run_payload = {
            "run_name": spec["run_name"],
            "model_node_id": spec["model_node_id"],
            "dataset_node_id": spec["dataset_node_id"],
            "split": "test",
            "seed": 42,
            "params": {"batch_size": 128, "epochs": 300},
        }
        run_id, created = ensure_run(spec["experiment_id"], run_payload)
        if created:
            add_metrics(run_id, spec["metrics"])
        else:
            print(f"skip_existing_run={spec['run_name']}")

        ctx.run_ids[spec["key"]] = run_id

    return ctx


def print_summary(ctx: Ctx) -> None:
    papers = api("GET", "/papers").json()
    nodes = api("GET", "/graph/nodes").json()
    exp_list = api("GET", "/experiments").json()

    print("=== Seed Completed ===")
    print(f"papers_total={len(papers)}")
    print(f"nodes_total={len(nodes)}")
    print(f"experiments_total={len(exp_list)}")
    print(f"created_paper_ids={ctx.paper_ids}")
    print(f"created_node_ids={ctx.node_ids}")
    print(f"created_experiment_ids={ctx.experiment_ids}")
    print(f"created_run_ids={ctx.run_ids}")

    for exp in exp_list[:3]:
        exp_id = exp["id"]
        rows = api("GET", f"/experiments/{exp_id}/metrics").json()
        print(f"experiment_{exp_id}_metric_rows={len(rows)}")


if __name__ == "__main__":
    try:
        check_backend()
        context = seed()
        print_summary(context)
    except Exception as exc:  # noqa: BLE001
        print(f"seed_failed={exc}")
        sys.exit(1)
