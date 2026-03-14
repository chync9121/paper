from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Experiment, ExperimentRun, KGEdge, KGNode, RunMetric
from app.schemas.paper_generation import PaperGenerationRequest
from app.services.llm_service import LLMServiceError, generate_chat_completion
from app.services.plot_service import generate_metric_scatter_chart, generate_performance_bar_chart
from app.services.top_tier_table_generator import TopTierTableGenerator, escape_latex


class TopTierPaperGenerator:
    def __init__(self) -> None:
        template_dir = Path(__file__).resolve().parent.parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False,
        )
        self.table_generator = TopTierTableGenerator(template_dir=template_dir)

    def generate(self, db: Session, payload: PaperGenerationRequest) -> dict[str, Any]:
        dataset = self._collect_dataset(db, payload)
        output_dir = self._prepare_output_dir(payload.title)
        figures_dir = output_dir / "figures"
        tables_dir = output_dir / "tables"

        main_metric = payload.main_metric_names[0] if payload.main_metric_names else self._pick_metric(dataset["metrics_df"], 0)
        aux_metric = payload.main_metric_names[1] if len(payload.main_metric_names) > 1 else self._pick_metric(dataset["metrics_df"], 1)

        performance_fig = generate_performance_bar_chart(
            dataset["metrics_df"],
            figures_dir / "performance_bar.png",
            metric_name=main_metric,
        )
        scatter_fig = generate_metric_scatter_chart(
            dataset["metrics_df"],
            figures_dir / "metric_scatter.png",
            x_metric=main_metric,
            y_metric=aux_metric,
        )

        tables = self._generate_tables(dataset, tables_dir, main_metric_names=payload.main_metric_names)
        sections, used_llm = self._generate_sections(dataset, payload)

        tex_content = self.env.get_template("paper_main.tex.j2").render(
            title=escape_latex(payload.title),
            sections={name: text for name, text in sections.items()},
            performance_figure_relpath="figures/performance_bar.png",
            calibration_figure_relpath="figures/metric_scatter.png",
            main_table_relpath="tables/main_results.tex",
            ablation_table_relpath="tables/ablation.tex",
        )
        tex_path = output_dir / "main.tex"
        tex_path.write_text(tex_content, encoding="utf-8")

        refs_path = output_dir / "refs.bib"
        refs_path.write_text(self._build_minimal_bib(dataset["nodes"]), encoding="utf-8")

        summary_path = output_dir / "context_snapshot.json"
        summary_path.write_text(json.dumps(dataset["context"], ensure_ascii=False, indent=2), encoding="utf-8")

        compile_result = self.compile_project(output_dir) if payload.try_compile_pdf else {
            "success": False,
            "pdf_path": None,
            "log": "PDF compilation skipped.",
        }

        return {
            "title": payload.title,
            "target_venue": payload.target_venue,
            "output_dir": str(output_dir),
            "tex_path": str(tex_path),
            "figure_paths": [str(performance_fig), str(scatter_fig)],
            "table_paths": [str(tables_dir / "main_results.tex"), str(tables_dir / "ablation.tex")],
            "used_llm": used_llm,
            "pdf_compiled": bool(compile_result["success"]),
            "pdf_path": str(compile_result["pdf_path"]) if compile_result["pdf_path"] else None,
            "compile_log": compile_result["log"],
            "sections": sections,
        }

    def _collect_dataset(self, db: Session, payload: PaperGenerationRequest) -> dict[str, Any]:
        experiments = db.query(Experiment).filter(Experiment.id.in_(payload.experiment_ids)).all()
        runs = (
            db.query(ExperimentRun)
            .filter(ExperimentRun.experiment_id.in_(payload.experiment_ids))
            .order_by(ExperimentRun.created_at.desc())
            .all()
        )
        run_ids = [run.id for run in runs]
        metrics = (
            db.query(RunMetric)
            .filter(RunMetric.run_id.in_(run_ids))
            .order_by(RunMetric.created_at.desc())
            .all()
            if run_ids
            else []
        )

        involved_node_ids = set(payload.selected_node_ids)
        for run in runs:
            if run.model_node_id is not None:
                involved_node_ids.add(run.model_node_id)
            if run.dataset_node_id is not None:
                involved_node_ids.add(run.dataset_node_id)

        nodes = db.query(KGNode).filter(KGNode.id.in_(list(involved_node_ids))).all() if involved_node_ids else []
        edges = (
            db.query(KGEdge)
            .filter(KGEdge.source_node_id.in_(list(involved_node_ids)), KGEdge.target_node_id.in_(list(involved_node_ids)))
            .all()
            if involved_node_ids
            else []
        )
        node_map = {node.id: node for node in nodes}
        run_map = {run.id: run for run in runs}

        metric_rows = []
        for metric in metrics:
            run = run_map.get(metric.run_id)
            if run is None:
                continue
            metric_rows.append(
                {
                    "run_id": run.id,
                    "experiment_id": run.experiment_id,
                    "run_name": run.run_name or f"run-{run.id}",
                    "model_name": node_map.get(run.model_node_id).name if run.model_node_id in node_map else f"model-{run.model_node_id}",
                    "dataset_name": node_map.get(run.dataset_node_id).name if run.dataset_node_id in node_map else f"dataset-{run.dataset_node_id}",
                    "metric_name": metric.metric_name,
                    "metric_value": metric.metric_value,
                    "higher_is_better": metric.higher_is_better,
                }
            )
        metrics_df = pd.DataFrame(metric_rows)
        if metrics_df.empty:
            raise ValueError("No metric rows found for the selected experiments.")

        context = {
            "experiments": [
                {"id": exp.id, "name": exp.name, "description": exp.description, "task_name": exp.task_name}
                for exp in experiments
            ],
            "nodes": [
                {"id": node.id, "name": node.name, "node_type": node.node_type, "description": node.description}
                for node in nodes
            ],
            "edges": [
                {"source": edge.source_node_id, "target": edge.target_node_id, "relation_type": edge.relation_type}
                for edge in edges
            ],
            "metrics_preview": metric_rows[:50],
        }

        return {
            "experiments": experiments,
            "runs": runs,
            "metrics": metrics,
            "nodes": nodes,
            "edges": edges,
            "metrics_df": metrics_df,
            "context": context,
        }

    def _prepare_output_dir(self, title: str) -> Path:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", title).strip("-").lower() or "paper-draft"
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_dir = Path(settings.generated_papers_dir) / f"{slug}-{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def _pick_metric(self, metrics_df: pd.DataFrame, index: int) -> str:
        metric_names = list(dict.fromkeys(metrics_df["metric_name"].tolist()))
        if not metric_names:
            raise ValueError("No metric names available.")
        return metric_names[min(index, len(metric_names) - 1)]

    def _generate_tables(self, dataset: dict[str, Any], tables_dir: Path, main_metric_names: list[str]) -> None:
        tables_dir.mkdir(parents=True, exist_ok=True)
        df = dataset["metrics_df"]
        metric_order = main_metric_names or list(dict.fromkeys(df["metric_name"].tolist()))[:3]
        dataset_order = list(dict.fromkeys(df["dataset_name"].tolist()))
        directions = {
            metric_name: ("max" if bool(group["higher_is_better"].iloc[0]) else "min")
            for metric_name, group in df.groupby("metric_name")
        }

        model_scores = []
        model_order = list(dict.fromkeys(df["model_name"].tolist()))
        for model_name in model_order:
            scores: dict[str, dict[str, float]] = {}
            model_df = df[df["model_name"] == model_name]
            for dataset_name in dataset_order:
                scores[dataset_name] = {}
                cell_df = model_df[model_df["dataset_name"] == dataset_name]
                for metric_name in metric_order:
                    metric_df = cell_df[cell_df["metric_name"] == metric_name]
                    if metric_df.empty:
                        continue
                    scores[dataset_name][metric_name] = float(metric_df["metric_value"].mean())
            model_scores.append({"model": model_name, "scores": scores})

        benchmark_payload = {
            "benchmark_table": {
                "caption": "Comparison with representative baselines on selected benchmarks.",
                "label": "tab:main-results",
                "note": "Best results are bold and second-best results are underlined. Metric directions are automatically inferred from experiment metadata.",
                "precision": 2,
                "dataset_order": dataset_order,
                "metric_order": metric_order,
                "metric_directions": directions,
                "model_order": model_order,
                "models": model_scores,
            },
            "ablation_table": self._build_ablation_payload(df=df, dataset_order=dataset_order, metric_order=metric_order, directions=directions),
        }

        rendered = self.table_generator.generate_tables(benchmark_payload)
        (tables_dir / "main_results.tex").write_text(rendered["benchmark_latex"], encoding="utf-8")
        (tables_dir / "ablation.tex").write_text(rendered["ablation_latex"], encoding="utf-8")

    def _build_ablation_payload(
        self,
        *,
        df: pd.DataFrame,
        dataset_order: list[str],
        metric_order: list[str],
        directions: dict[str, str],
    ) -> dict[str, Any]:
        model_order = list(dict.fromkeys(df["model_name"].tolist()))
        base_model = model_order[-1]
        variant_order: list[str] = []
        variants: list[dict[str, Any]] = []
        component_names = ["Knowledge Graph", "LLM Reports", "Table Engine"]

        for idx, model_name in enumerate(model_order[-4:]):
            variant_name = "Full System" if model_name == base_model else f"Variant-{idx + 1}"
            variant_order.append(variant_name)
            model_df = df[df["model_name"] == model_name]
            scores: dict[str, dict[str, float]] = {}
            for dataset_name in dataset_order:
                scores[dataset_name] = {}
                cell_df = model_df[model_df["dataset_name"] == dataset_name]
                for metric_name in metric_order[:2]:
                    metric_df = cell_df[cell_df["metric_name"] == metric_name]
                    if metric_df.empty:
                        continue
                    scores[dataset_name][metric_name] = float(metric_df["metric_value"].mean())

            variants.append(
                {
                    "variant": variant_name,
                    "components": {
                        "Knowledge Graph": model_name != model_order[0],
                        "LLM Reports": model_name != model_order[1] if len(model_order) > 1 else True,
                        "Table Engine": model_name != model_order[2] if len(model_order) > 2 else True,
                    },
                    "scores": scores,
                }
            )

        return {
            "caption": "Ablation-style view synthesized from selected model variants.",
            "label": "tab:ablation",
            "note": "The full system row keeps all components enabled. Other rows suppress one capability to mimic an ablation presentation.",
            "precision": 2,
            "dataset_order": dataset_order,
            "metric_order": metric_order[:2],
            "metric_directions": {key: directions[key] for key in metric_order[:2]},
            "component_order": component_names,
            "variant_order": variant_order,
            "variants": variants,
        }

    def _generate_sections(self, dataset: dict[str, Any], payload: PaperGenerationRequest) -> tuple[dict[str, str], bool]:
        context_text = json.dumps(dataset["context"], ensure_ascii=False, indent=2)
        if payload.use_llm:
            try:
                sections = self._generate_sections_with_llm(payload=payload, context_text=context_text)
                return sections, True
            except LLMServiceError:
                pass

        sections = self._generate_fallback_sections(dataset=dataset, payload=payload)
        return sections, False

    def _generate_sections_with_llm(self, *, payload: PaperGenerationRequest, context_text: str) -> dict[str, str]:
        prompts = {
            "abstract": "Write an academic abstract in English for a top-tier conference paper.",
            "introduction": "Write the introduction section in English, with motivation and contributions.",
            "related_work": "Write the related work section in English, grounded in the provided graph context.",
            "method": "Write a method section that frames the system as a knowledge-driven evaluation and report generation pipeline.",
            "experiments": "Write the experiments section in English, citing the provided metrics and figures/tables.",
            "conclusion": "Write a short conclusion section in English.",
        }
        sections: dict[str, str] = {}
        for section_name, instruction in prompts.items():
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an experienced CVPR/NeurIPS/ACL paper writer. "
                        "Produce concise, factual LaTeX-ready prose without bullet lists."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Paper title: {payload.title}\n"
                        f"Venue target: {payload.target_venue}\n"
                        f"Instruction: {instruction}\n"
                        f"Additional author request: {payload.prompt or 'Emphasize the interaction between knowledge graph analysis, automatic tables, and figures.'}\n\n"
                        f"Context:\n{context_text}"
                    ),
                },
            ]
            generated, _, _ = generate_chat_completion(
                messages=messages,
                model=payload.model_name,
                temperature=0.35,
                max_tokens=900,
            )
            sections[section_name] = generated.strip()
        return sections

    def _generate_fallback_sections(self, *, dataset: dict[str, Any], payload: PaperGenerationRequest) -> dict[str, str]:
        experiments = dataset["experiments"]
        metrics_df = dataset["metrics_df"]
        model_names = list(dict.fromkeys(metrics_df["model_name"].tolist()))
        dataset_names = list(dict.fromkeys(metrics_df["dataset_name"].tolist()))
        metric_names = list(dict.fromkeys(metrics_df["metric_name"].tolist()))
        task_names = [exp.task_name for exp in experiments if exp.task_name]
        task_hint = task_names[0] if task_names else payload.target_venue
        is_fake_news = any("fake news" in (name or "").lower() for name in task_names) or (
            "fake news" in payload.title.lower() or "misinformation" in payload.title.lower()
        )
        best_rows = (
            metrics_df.sort_values("metric_value", ascending=False)
            .groupby(["dataset_name", "metric_name"], as_index=False)
            .first()
        )
        best_summary = "; ".join(
            f"on {row.dataset_name}, {row.model_name} reaches {row.metric_value:.2f} for {row.metric_name}"
            for row in best_rows.itertuples()
        )

        if is_fake_news:
            return {
                "abstract": (
                    f"We present an automated manuscript generation pipeline for fake news detection research. "
                    f"The system unifies knowledge graph curation, experiment aggregation, publication-grade plotting, "
                    f"and top-tier LaTeX table synthesis into a single workflow. Across {len(experiments)} benchmark "
                    f"settings spanning {', '.join(dataset_names)}, the generated draft summarizes comparative evidence "
                    f"for {', '.join(model_names)} and turns structured evaluation metadata into a submission-ready paper skeleton."
                ),
                "introduction": (
                    "Fake news detection remains challenging because misleading claims often mix linguistic ambiguity, "
                    "topic drift, and rapidly evolving social context. In practice, researchers spend substantial effort "
                    "synchronizing related work notes, benchmark results, figures, and final LaTeX tables. Our system "
                    "treats paper writing as a reproducible downstream artifact of the evaluation pipeline, enabling "
                    "automatic coordination between evidence collection, visualization, and manuscript assembly."
                ),
                "related_work": (
                    "Recent fake news detection studies typically combine textual encoders with auxiliary signals such as "
                    "publisher patterns, user propagation traces, or structured knowledge. The knowledge graph in our platform "
                    "organizes papers, models, datasets, and metrics into a connected research substrate, which helps the drafting "
                    "engine retrieve stronger baselines and keeps the generated discussion grounded in actual benchmark evidence."
                ),
                "method": (
                    "The proposed framework contains four stages: graph-based literature organization, structured benchmark ingestion, "
                    "publication-grade figure and table rendering, and section-level manuscript composition. For fake news detection, "
                    "this design is especially useful because it aligns dataset-specific comparisons with model families and evaluation "
                    "criteria, while the table engine preserves top-tier formatting conventions such as booktabs rules and best/second-best highlighting."
                ),
                "experiments": (
                    f"We aggregate {len(metrics_df)} metric records over {len(model_names)} models, {len(dataset_names)} datasets, "
                    f"and {len(metric_names)} metrics for the task of {task_hint}. The generated figures summarize performance trends across "
                    f"benchmarks, while the main and ablation tables expose ranking structure in a publication-ready format. "
                    f"Representative results include {best_summary}."
                ),
                "conclusion": (
                    "This draft demonstrates that fake news detection studies can benefit from a tightly coupled evaluation-and-writing workflow. "
                    "By connecting graph-structured literature evidence, benchmark dashboards, figure generation, and LaTeX assembly, the system "
                    "reduces manual overhead and improves the consistency of submission materials."
                ),
            }

        return {
            "abstract": (
                f"We present an automated manuscript generation pipeline for {payload.target_venue}-style submissions. "
                f"The system integrates knowledge graph curation, experiment aggregation, publication-grade plots, and "
                f"LaTeX table synthesis. Across {len(experiments)} experiment groups covering {', '.join(dataset_names)}, "
                f"the pipeline summarizes results for models such as {', '.join(model_names)} and automatically composes a paper draft."
            ),
            "introduction": (
                "Preparing a top-tier paper often requires repeated manual synchronization between related work notes, "
                "evaluation dashboards, plots, and LaTeX tables. Our system reduces this burden by treating the paper as "
                "a generated artifact grounded in structured experiment metadata and a lightweight knowledge graph. "
                "The resulting workflow keeps quantitative evidence, textual analysis, and visual assets aligned."
            ),
            "related_work": (
                "The knowledge graph component organizes papers, models, datasets, and metrics into a connected research map. "
                "This representation enables the drafting pipeline to retrieve baseline families and evaluation relations before "
                "writing the manuscript, which helps the generated text stay closer to the actual experimental context."
            ),
            "method": (
                "The proposed pipeline contains four stages: structured experiment ingestion, graph-aware baseline retrieval, "
                "publication-grade figure and table synthesis, and section-level manuscript composition. "
                "The table engine enforces booktabs-style formatting and ranking-aware highlighting, while the figure engine renders "
                "comparison charts directly from metric records."
            ),
            "experiments": (
                f"We aggregate {len(metrics_df)} metric records over {len(model_names)} models, {len(dataset_names)} datasets, "
                f"and {len(metric_names)} metrics. The automatically generated figures summarize performance distributions, and the "
                f"LaTeX tables expose ranking structure with best/runner-up highlighting. Representative findings include {best_summary}."
            ),
            "conclusion": (
                "This draft demonstrates that a knowledge-driven experiment platform can automate a substantial portion of the "
                "paper-writing workflow. Future work can further improve citation grounding, significance testing, and venue-specific formatting."
            ),
        }

    def _build_minimal_bib(self, nodes: list[KGNode]) -> str:
        paper_nodes = [node for node in nodes if node.node_type == "paper"]
        if not paper_nodes:
            return "@misc{autogen2026,\n  title={Auto-generated references placeholder}\n}\n"

        entries = []
        for idx, node in enumerate(paper_nodes, start=1):
            key = f"ref{idx}"
            title = escape_latex(node.name)
            entries.append(f"@misc{{{key},\n  title={{ {title} }},\n  note={{Imported from knowledge graph}}\n}}\n")
        return "\n".join(entries)

    def compile_project(self, output_dir: Path) -> dict[str, Any]:
        pdflatex = self._find_executable("pdflatex")
        bibtex = self._find_executable("bibtex")
        if not pdflatex:
            return {
                "success": False,
                "pdf_path": None,
                "log": "pdflatex was not found. Install a TeX distribution such as MiKTeX or TeX Live.",
            }

        logs: list[str] = []
        try:
            first_pass = subprocess.run(
                [pdflatex, "-interaction=nonstopmode", "main.tex"],
                cwd=output_dir,
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
            logs.extend([first_pass.stdout, first_pass.stderr])
            if bibtex and (output_dir / "main.aux").exists():
                bibtex_pass = subprocess.run(
                    [bibtex, "main"],
                    cwd=output_dir,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                logs.extend([bibtex_pass.stdout, bibtex_pass.stderr])
            for _ in range(2):
                pass_result = subprocess.run(
                    [pdflatex, "-interaction=nonstopmode", "main.tex"],
                    cwd=output_dir,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                logs.extend([pass_result.stdout, pass_result.stderr])
            pdf_path = output_dir / "main.pdf"
            if pdf_path.exists():
                return {
                    "success": True,
                    "pdf_path": pdf_path,
                    "log": "\n".join(item for item in logs if item).strip(),
                }
        except subprocess.CalledProcessError as exc:
            logs.extend([exc.stdout or "", exc.stderr or ""])
            return {
                "success": False,
                "pdf_path": None,
                "log": "\n".join(item for item in logs if item).strip() or str(exc),
            }
        except (subprocess.SubprocessError, OSError) as exc:
            return {
                "success": False,
                "pdf_path": None,
                "log": str(exc),
            }
        return {
            "success": False,
            "pdf_path": None,
            "log": "\n".join(item for item in logs if item).strip() or "PDF was not generated.",
        }

    def _find_executable(self, name: str) -> str | None:
        found = shutil.which(name)
        if found:
            return found

        candidate_dirs = [
            Path.home() / "AppData" / "Local" / "Programs" / "MiKTeX" / "miktex" / "bin" / "x64",
            Path("C:/Program Files/MiKTeX/miktex/bin/x64"),
        ]
        for directory in candidate_dirs:
            candidate = directory / f"{name}.exe"
            if candidate.exists():
                return str(candidate)
        return None
