from __future__ import annotations

import sys
from dataclasses import dataclass

import requests


BASE_URL = "http://127.0.0.1:8000/api/v1"


@dataclass
class MetricValue:
    name: str
    value: float


def get_json(path: str, **params):
    response = requests.get(f"{BASE_URL}{path}", params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def post_json(path: str, payload: dict):
    response = requests.post(f"{BASE_URL}{path}", json=payload, timeout=30)
    if response.status_code not in (200, 201, 409):
        response.raise_for_status()
    if response.status_code == 409:
        return None
    return response.json()


def ensure_paper(*, title: str, venue: str, year: int, abstract: str, url: str | None = None) -> dict:
    existing = get_json("/papers")
    for item in existing:
        if item["title"] == title:
            return item
    created = post_json(
        "/papers",
        {
            "title": title,
            "venue": venue,
            "year": year,
            "abstract": abstract,
            "url": url,
        },
    )
    if created is None:
        raise RuntimeError(f"Failed to create paper: {title}")
    return created


def ensure_node(
    *,
    node_type: str,
    name: str,
    description: str | None = None,
    paper_id: int | None = None,
    extra: dict | None = None,
) -> dict:
    existing = get_json("/graph/nodes", node_type=node_type, q=name)
    for item in existing:
        if item["name"] == name and item["node_type"] == node_type:
            return item
    created = post_json(
        "/graph/nodes",
        {
            "node_type": node_type,
            "name": name,
            "canonical_name": name,
            "description": description,
            "paper_id": paper_id,
            "extra": extra or {},
        },
    )
    if created is None:
        raise RuntimeError(f"Failed to create node: {node_type}/{name}")
    return created


def ensure_edge(*, source_node_id: int, target_node_id: int, relation_type: str, paper_id: int | None = None, evidence_text: str | None = None):
    result = post_json(
        "/graph/edges",
        {
            "source_node_id": source_node_id,
            "target_node_id": target_node_id,
            "relation_type": relation_type,
            "paper_id": paper_id,
            "evidence_text": evidence_text,
        },
    )
    return result


def ensure_experiment(*, name: str, description: str, task_name: str, owner: str) -> dict:
    existing = get_json("/experiments")
    for item in existing:
        if item["name"] == name:
            return item
    created = post_json(
        "/experiments",
        {
            "name": name,
            "description": description,
            "task_name": task_name,
            "owner": owner,
        },
    )
    if created is None:
        raise RuntimeError(f"Failed to create experiment: {name}")
    return created


def ensure_run(
    *,
    experiment_id: int,
    run_name: str,
    model_node_id: int,
    dataset_node_id: int,
    params: dict | None = None,
) -> dict:
    existing = get_json(f"/experiments/{experiment_id}/runs")
    for item in existing:
        if item["run_name"] == run_name:
            return item
    created = post_json(
        f"/experiments/{experiment_id}/runs",
        {
            "run_name": run_name,
            "model_node_id": model_node_id,
            "dataset_node_id": dataset_node_id,
            "split": "test",
            "params": params or {},
        },
    )
    if created is None:
        raise RuntimeError(f"Failed to create run: {run_name}")
    return created


def ensure_metrics(*, experiment_id: int, run_id: int, metrics: list[MetricValue], metric_node_ids: dict[str, int]):
    existing = get_json(f"/experiments/{experiment_id}/metrics")
    existing_names = {row["metric_name"] for row in existing if row["run_id"] == run_id}
    missing = [metric for metric in metrics if metric.name not in existing_names]
    if not missing:
        return

    payload = {
        "metrics": [
            {
                "metric_node_id": metric_node_ids[metric.name],
                "metric_name": metric.name,
                "metric_value": metric.value,
                "higher_is_better": True,
                "stage": "best",
            }
            for metric in missing
        ]
    }
    response = requests.post(
        f"{BASE_URL}/experiments/runs/{run_id}/metrics/batch",
        json=payload,
        timeout=30,
    )
    response.raise_for_status()


def main():
    papers = {
        "liar": ensure_paper(
            title="LIAR: Liar, Liar Pants on Fire: A New Benchmark Dataset for Fake News Detection",
            venue="ACL",
            year=2017,
            abstract="LIAR introduces a large-scale benchmark of short political statements annotated for fine-grained fake news detection.",
            url="https://aclanthology.org/P17-2067/",
        ),
        "fakenewsnet": ensure_paper(
            title="FakeNewsNet: A Data Repository with News Content, Social Context, and Spatiotemporal Information for Studying Fake News on Social Media",
            venue="Big Data",
            year=2020,
            abstract="FakeNewsNet integrates news content and social context for studying misinformation detection on social media platforms.",
            url="https://arxiv.org/abs/1809.01286",
        ),
        "fakeddit": ensure_paper(
            title="Fakeddit: A New Multimodal Benchmark Dataset for Fine-grained Fake News Detection",
            venue="LREC",
            year=2020,
            abstract="Fakeddit is a multimodal fake news benchmark with fine-grained labels and aligned textual and visual evidence.",
            url="https://arxiv.org/abs/1911.03854",
        ),
        "declare": ensure_paper(
            title="DeClarE: Debunking Fake News and False Claims Using Evidence-Aware Deep Learning",
            venue="EMNLP",
            year=2018,
            abstract="DeClarE leverages external evidence and attention-based aggregation for fake news and false claim detection.",
            url="https://aclanthology.org/D18-1003/",
        ),
    }

    paper_nodes = {
        item["title"]: ensure_node(
            node_type="paper",
            name=item["title"],
            description=item["abstract"],
            paper_id=item["id"],
            extra={"venue": item["venue"], "year": item["year"]},
        )
        for item in papers.values()
    }

    task_node = ensure_node(
        node_type="task",
        name="Fake News Detection",
        description="Binary or fine-grained misinformation identification from news content and associated context.",
    )

    dataset_nodes = {
        "LIAR": ensure_node(node_type="dataset", name="LIAR", description="Short political statements for fake news detection."),
        "FakeNewsNet": ensure_node(node_type="dataset", name="FakeNewsNet", description="News articles paired with social context signals."),
        "Fakeddit": ensure_node(node_type="dataset", name="Fakeddit", description="Multimodal benchmark for fine-grained fake news detection."),
    }

    metric_nodes = {
        "Accuracy": ensure_node(node_type="metric", name="Accuracy", description="Classification accuracy."),
        "Macro-F1": ensure_node(node_type="metric", name="Macro-F1", description="Macro-averaged F1 score."),
        "ROC-AUC": ensure_node(node_type="metric", name="ROC-AUC", description="Area under the ROC curve."),
    }

    model_nodes = {
        "BiLSTM": ensure_node(node_type="model", name="BiLSTM", description="Sequence encoder baseline for textual fake news detection."),
        "DeClarE": ensure_node(
            node_type="model",
            name="DeClarE",
            description="Evidence-aware fake news detector.",
            paper_id=papers["declare"]["id"],
        ),
        "RoBERTa": ensure_node(node_type="model", name="RoBERTa", description="Pretrained transformer baseline."),
        "GraphAware-RoBERTa": ensure_node(
            node_type="model",
            name="GraphAware-RoBERTa",
            description="Graph-enhanced transformer with evidence alignment and propagation reasoning.",
        ),
    }

    component_nodes = {
        "Evidence Graph": ensure_node(node_type="method", name="Evidence Graph", description="Structured evidence and entity linkage module."),
        "Propagation Encoder": ensure_node(node_type="method", name="Propagation Encoder", description="Social propagation representation module."),
        "Knowledge Consistency": ensure_node(node_type="method", name="Knowledge Consistency", description="Cross-source consistency regularization."),
    }

    ensure_edge(
        source_node_id=paper_nodes["LIAR: Liar, Liar Pants on Fire: A New Benchmark Dataset for Fake News Detection"]["id"],
        target_node_id=dataset_nodes["LIAR"]["id"],
        relation_type="introduces_dataset",
        paper_id=papers["liar"]["id"],
    )
    ensure_edge(
        source_node_id=paper_nodes["FakeNewsNet: A Data Repository with News Content, Social Context, and Spatiotemporal Information for Studying Fake News on Social Media"]["id"],
        target_node_id=dataset_nodes["FakeNewsNet"]["id"],
        relation_type="introduces_dataset",
        paper_id=papers["fakenewsnet"]["id"],
    )
    ensure_edge(
        source_node_id=paper_nodes["Fakeddit: A New Multimodal Benchmark Dataset for Fine-grained Fake News Detection"]["id"],
        target_node_id=dataset_nodes["Fakeddit"]["id"],
        relation_type="introduces_dataset",
        paper_id=papers["fakeddit"]["id"],
    )
    ensure_edge(
        source_node_id=paper_nodes["DeClarE: Debunking Fake News and False Claims Using Evidence-Aware Deep Learning"]["id"],
        target_node_id=model_nodes["DeClarE"]["id"],
        relation_type="proposed_in",
        paper_id=papers["declare"]["id"],
    )

    for model in model_nodes.values():
        ensure_edge(source_node_id=model["id"], target_node_id=task_node["id"], relation_type="applied_to")
        for metric in metric_nodes.values():
            ensure_edge(source_node_id=model["id"], target_node_id=metric["id"], relation_type="uses_metric")

    ensure_edge(source_node_id=model_nodes["GraphAware-RoBERTa"]["id"], target_node_id=component_nodes["Evidence Graph"]["id"], relation_type="uses_component")
    ensure_edge(source_node_id=model_nodes["GraphAware-RoBERTa"]["id"], target_node_id=component_nodes["Propagation Encoder"]["id"], relation_type="uses_component")
    ensure_edge(source_node_id=model_nodes["GraphAware-RoBERTa"]["id"], target_node_id=component_nodes["Knowledge Consistency"]["id"], relation_type="uses_component")

    experiment_specs = [
        {
            "name": "LIAR Fake News Benchmark",
            "description": "Statement-level fake news detection benchmark on LIAR.",
            "dataset_name": "LIAR",
            "scores": {
                "BiLSTM": [MetricValue("Accuracy", 0.731), MetricValue("Macro-F1", 0.718), MetricValue("ROC-AUC", 0.794)],
                "DeClarE": [MetricValue("Accuracy", 0.756), MetricValue("Macro-F1", 0.744), MetricValue("ROC-AUC", 0.821)],
                "RoBERTa": [MetricValue("Accuracy", 0.823), MetricValue("Macro-F1", 0.815), MetricValue("ROC-AUC", 0.887)],
                "GraphAware-RoBERTa": [MetricValue("Accuracy", 0.851), MetricValue("Macro-F1", 0.844), MetricValue("ROC-AUC", 0.913)],
            },
        },
        {
            "name": "FakeNewsNet Social Context Benchmark",
            "description": "Article-level fake news detection with social context on FakeNewsNet.",
            "dataset_name": "FakeNewsNet",
            "scores": {
                "BiLSTM": [MetricValue("Accuracy", 0.842), MetricValue("Macro-F1", 0.831), MetricValue("ROC-AUC", 0.892)],
                "DeClarE": [MetricValue("Accuracy", 0.861), MetricValue("Macro-F1", 0.849), MetricValue("ROC-AUC", 0.908)],
                "RoBERTa": [MetricValue("Accuracy", 0.903), MetricValue("Macro-F1", 0.896), MetricValue("ROC-AUC", 0.947)],
                "GraphAware-RoBERTa": [MetricValue("Accuracy", 0.926), MetricValue("Macro-F1", 0.918), MetricValue("ROC-AUC", 0.964)],
            },
        },
        {
            "name": "Fakeddit Multimodal Benchmark",
            "description": "Multimodal fake news detection benchmark on Fakeddit.",
            "dataset_name": "Fakeddit",
            "scores": {
                "BiLSTM": [MetricValue("Accuracy", 0.801), MetricValue("Macro-F1", 0.789), MetricValue("ROC-AUC", 0.856)],
                "DeClarE": [MetricValue("Accuracy", 0.822), MetricValue("Macro-F1", 0.810), MetricValue("ROC-AUC", 0.874)],
                "RoBERTa": [MetricValue("Accuracy", 0.887), MetricValue("Macro-F1", 0.879), MetricValue("ROC-AUC", 0.931)],
                "GraphAware-RoBERTa": [MetricValue("Accuracy", 0.911), MetricValue("Macro-F1", 0.904), MetricValue("ROC-AUC", 0.952)],
            },
        },
    ]

    created_experiments: list[int] = []
    for spec in experiment_specs:
        experiment = ensure_experiment(
            name=spec["name"],
            description=spec["description"],
            task_name="Fake News Detection",
            owner="auto-paper",
        )
        created_experiments.append(experiment["id"])
        dataset_id = dataset_nodes[spec["dataset_name"]]["id"]
        for model_name, metrics in spec["scores"].items():
            run = ensure_run(
                experiment_id=experiment["id"],
                run_name=f"{model_name} on {spec['dataset_name']}",
                model_node_id=model_nodes[model_name]["id"],
                dataset_node_id=dataset_id,
                params={"encoder": model_name, "dataset": spec["dataset_name"]},
            )
            ensure_metrics(
                experiment_id=experiment["id"],
                run_id=run["id"],
                metrics=metrics,
                metric_node_ids={name: node["id"] for name, node in metric_nodes.items()},
            )
            ensure_edge(
                source_node_id=model_nodes[model_name]["id"],
                target_node_id=dataset_id,
                relation_type="evaluated_on",
            )

    print("Seeded fake news benchmark data successfully.")
    print(f"Experiment IDs: {created_experiments}")
    print(f"Selected node IDs: {[node['id'] for node in model_nodes.values()] + [node['id'] for node in dataset_nodes.values()] + [task_node['id']]}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - utility script
        print(f"Seed failed: {exc}", file=sys.stderr)
        raise
