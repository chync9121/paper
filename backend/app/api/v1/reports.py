from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Experiment, ExperimentRun, GeneratedReport, KGEdge, KGNode, RunMetric
from app.schemas.reports import ReportGenerateRequest, ReportRead
from app.services.llm_service import LLMServiceError, generate_chat_completion

router = APIRouter(prefix="/reports", tags=["reports"])


def _build_context(
    payload: ReportGenerateRequest,
    nodes: list[KGNode],
    edges: list[KGEdge],
    experiments: list[Experiment],
    runs: list[ExperimentRun],
    metrics: list[RunMetric],
) -> dict[str, Any]:
    node_map = {node.id: node for node in nodes}
    run_view = []
    for run in runs:
        model_name = node_map.get(run.model_node_id).name if run.model_node_id in node_map else None
        dataset_name = (
            node_map.get(run.dataset_node_id).name if run.dataset_node_id in node_map else None
        )
        run_view.append(
            {
                "run_id": run.id,
                "run_name": run.run_name,
                "experiment_id": run.experiment_id,
                "model_node_id": run.model_node_id,
                "model_name": model_name,
                "dataset_node_id": run.dataset_node_id,
                "dataset_name": dataset_name,
                "split": run.split,
            }
        )

    metric_view = [
        {
            "run_id": metric.run_id,
            "metric_name": metric.metric_name,
            "metric_value": metric.metric_value,
            "stage": metric.stage,
            "higher_is_better": metric.higher_is_better,
        }
        for metric in metrics
    ]

    return {
        "report_type": payload.report_type,
        "selected_node_count": len(nodes),
        "selected_edge_count": len(edges),
        "selected_experiment_count": len(experiments),
        "selected_run_count": len(runs),
        "selected_metric_count": len(metrics),
        "nodes": [
            {
                "id": node.id,
                "node_type": node.node_type,
                "name": node.name,
                "paper_id": node.paper_id,
                "description": node.description,
            }
            for node in nodes
        ],
        "edges": [
            {
                "id": edge.id,
                "source_node_id": edge.source_node_id,
                "target_node_id": edge.target_node_id,
                "relation_type": edge.relation_type,
            }
            for edge in edges
        ],
        "experiments": [
            {
                "id": exp.id,
                "name": exp.name,
                "description": exp.description,
                "task_name": exp.task_name,
            }
            for exp in experiments
        ],
        "runs": run_view,
        "metrics": metric_view,
    }


def _build_messages(payload: ReportGenerateRequest, context: dict[str, Any]) -> list[dict[str, str]]:
    goal_map = {
        "related_work": "请生成逻辑严密的“相关工作（Related Work）”段落。",
        "experimental_analysis": "请生成逻辑严密的“实验分析（Experimental Analysis）”段落。",
    }
    user_goal = goal_map[payload.report_type]
    extra = payload.prompt or "请强调方法差异、数据集特点、指标变化趋势，并避免空泛描述。"
    context_text = json.dumps(context, ensure_ascii=False, indent=2)

    return [
        {
            "role": "system",
            "content": (
                "你是顶会论文写作助手，擅长 CVPR/NeurIPS/ICLR 风格的技术写作。"
                "输出必须学术、克制、结构清晰，避免编造未给出的事实。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"{user_goal}\n"
                "要求：\n"
                "1) 使用中文，1-3 个自然段。\n"
                "2) 每段都应引用上下文中的具体模型/数据集/指标信息。\n"
                "3) 如果证据不足，需要明确说明局限，不要捏造。\n"
                f"4) 附加要求：{extra}\n\n"
                f"上下文如下：\n{context_text}"
            ),
        },
    ]


@router.post("/generate", response_model=ReportRead)
def generate_report(payload: ReportGenerateRequest, db: Session = Depends(get_db)):
    nodes = (
        db.query(KGNode).filter(KGNode.id.in_(payload.selected_node_ids)).all()
        if payload.selected_node_ids
        else []
    )
    edges = (
        db.query(KGEdge)
        .filter(
            KGEdge.source_node_id.in_(payload.selected_node_ids),
            KGEdge.target_node_id.in_(payload.selected_node_ids),
        )
        .all()
        if payload.selected_node_ids
        else []
    )
    experiments = (
        db.query(Experiment).filter(Experiment.id.in_(payload.selected_experiment_ids)).all()
        if payload.selected_experiment_ids
        else []
    )

    runs = (
        db.query(ExperimentRun)
        .filter(ExperimentRun.experiment_id.in_(payload.selected_experiment_ids))
        .order_by(ExperimentRun.created_at.desc())
        .limit(payload.max_runs)
        .all()
        if payload.selected_experiment_ids
        else []
    )
    run_ids = [run.id for run in runs]

    metrics = (
        db.query(RunMetric)
        .filter(RunMetric.run_id.in_(run_ids))
        .order_by(RunMetric.created_at.desc())
        .limit(payload.max_metrics)
        .all()
        if run_ids
        else []
    )

    context_snapshot = _build_context(payload, nodes, edges, experiments, runs, metrics)
    messages = _build_messages(payload, context_snapshot)

    try:
        output_text, used_model, _raw = generate_chat_completion(
            messages=messages,
            model=payload.model_name,
            temperature=payload.temperature,
        )
    except LLMServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    item = GeneratedReport(
        report_type=payload.report_type,
        title=payload.title,
        selected_node_ids=payload.selected_node_ids,
        selected_run_ids=run_ids,
        prompt=payload.prompt,
        context_snapshot=context_snapshot,
        model_name=used_model,
        output_markdown=output_text,
        output_text=output_text,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=list[ReportRead])
def list_reports(limit: int = 30, db: Session = Depends(get_db)):
    return db.query(GeneratedReport).order_by(GeneratedReport.created_at.desc()).limit(limit).all()


@router.get("/{report_id}", response_model=ReportRead)
def get_report(report_id: int, db: Session = Depends(get_db)):
    item = db.query(GeneratedReport).filter(GeneratedReport.id == report_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Report not found.")
    return item
