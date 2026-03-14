from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from jinja2 import Environment, FileSystemLoader


LATEX_ESCAPES = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def escape_latex(text: str) -> str:
    return "".join(LATEX_ESCAPES.get(char, char) for char in text)


class TopTierTableGenerator:
    def __init__(self, template_dir: str | Path | None = None) -> None:
        base_dir = Path(template_dir) if template_dir else Path(__file__).resolve().parent.parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(base_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False,
        )

    def generate_tables(self, payload: dict[str, Any]) -> dict[str, str]:
        benchmark_payload = payload["benchmark_table"]
        ablation_payload = payload["ablation_table"]
        return {
            "benchmark_latex": self._generate_benchmark_table(benchmark_payload),
            "ablation_latex": self._generate_ablation_table(ablation_payload),
        }

    def _generate_benchmark_table(self, payload: dict[str, Any]) -> str:
        records = []
        for model_item in payload["models"]:
            model_name = model_item["model"]
            for dataset_name, metric_map in model_item["scores"].items():
                for metric_name, value in metric_map.items():
                    records.append(
                        {
                            "row_label": model_name,
                            "dataset": dataset_name,
                            "metric": metric_name,
                            "value": float(value),
                        }
                    )

        directions = payload["metric_directions"]
        context = self._build_table_context(
            records=records,
            row_order=payload["model_order"],
            dataset_order=payload["dataset_order"],
            metric_order=payload["metric_order"],
            metric_directions=directions,
            precision=payload.get("precision", 2),
            caption=payload["caption"],
            label=payload["label"],
            note=payload["note"],
            component_names=[],
            component_rows=None,
        )
        return self.env.get_template("benchmark_table.tex.j2").render(**context)

    def _generate_ablation_table(self, payload: dict[str, Any]) -> str:
        records = []
        component_rows: dict[str, dict[str, bool]] = {}

        for variant_item in payload["variants"]:
            variant_name = variant_item["variant"]
            component_rows[variant_name] = variant_item["components"]
            for dataset_name, metric_map in variant_item["scores"].items():
                for metric_name, value in metric_map.items():
                    records.append(
                        {
                            "row_label": variant_name,
                            "dataset": dataset_name,
                            "metric": metric_name,
                            "value": float(value),
                        }
                    )

        directions = payload["metric_directions"]
        context = self._build_table_context(
            records=records,
            row_order=payload["variant_order"],
            dataset_order=payload["dataset_order"],
            metric_order=payload["metric_order"],
            metric_directions=directions,
            precision=payload.get("precision", 2),
            caption=payload["caption"],
            label=payload["label"],
            note=payload["note"],
            component_names=payload["component_order"],
            component_rows=component_rows,
        )
        return self.env.get_template("ablation_table.tex.j2").render(**context)

    def _build_table_context(
        self,
        *,
        records: list[dict[str, Any]],
        row_order: list[str],
        dataset_order: list[str],
        metric_order: list[str],
        metric_directions: dict[str, str],
        precision: int,
        caption: str,
        label: str,
        note: str,
        component_names: list[str],
        component_rows: dict[str, dict[str, bool]] | None,
    ) -> dict[str, Any]:
        frame = pd.DataFrame(records)
        pivot = frame.pivot_table(
            index="row_label",
            columns=["dataset", "metric"],
            values="value",
            aggfunc="mean",
        )

        ordered_columns = pd.MultiIndex.from_product([dataset_order, metric_order])
        pivot = pivot.reindex(index=row_order, columns=ordered_columns)

        ranked_columns = self._compute_ranked_columns(
            pivot=pivot,
            metric_directions=metric_directions,
        )

        rows = []
        for row_label in row_order:
            values = []
            for dataset_name, metric_name in ordered_columns:
                cell_value = pivot.loc[row_label, (dataset_name, metric_name)]
                if pd.isna(cell_value):
                    values.append("--")
                    continue
                formatted = self._format_value(
                    value=float(cell_value),
                    ranked_values=ranked_columns[(dataset_name, metric_name)],
                    direction=metric_directions.get(metric_name, "max"),
                    precision=precision,
                )
                values.append(formatted)

            row_components = []
            if component_names and component_rows is not None:
                row_components = [
                    r"$\checkmark$" if component_rows.get(row_label, {}).get(component_name) else ""
                    for component_name in component_names
                ]

            rows.append(
                {
                    "row_label": escape_latex(row_label),
                    "components": row_components,
                    "values": values,
                }
            )

        dataset_headers = self._dataset_headers(
            dataset_order=dataset_order,
            metric_order=metric_order,
            leading_cols=1 + len(component_names),
        )
        metric_columns = [
            {
                "dataset": dataset_name,
                "metric": metric_name,
                "metric_label": self._metric_label(metric_name, metric_directions.get(metric_name, "max")),
            }
            for dataset_name in dataset_order
            for metric_name in metric_order
        ]

        return {
            "caption": escape_latex(caption),
            "label": label,
            "note": escape_latex(note),
            "alignment": "l" + "c" * len(component_names) + "c" * len(metric_columns),
            "dataset_headers": dataset_headers,
            "metric_columns": metric_columns,
            "component_names": [escape_latex(name) for name in component_names],
            "rows": rows,
        }

    def _compute_ranked_columns(
        self,
        *,
        pivot: pd.DataFrame,
        metric_directions: dict[str, str],
    ) -> dict[tuple[str, str], list[float]]:
        ranked: dict[tuple[str, str], list[float]] = {}
        for dataset_name, metric_name in pivot.columns:
            values = pivot[(dataset_name, metric_name)].dropna().tolist()
            unique_values = sorted(
                {float(value) for value in values},
                reverse=metric_directions.get(metric_name, "max") == "max",
            )
            ranked[(dataset_name, metric_name)] = unique_values
        return ranked

    def _format_value(
        self,
        *,
        value: float,
        ranked_values: list[float],
        direction: str,
        precision: int,
    ) -> str:
        raw = f"{value:.{precision}f}"
        if not ranked_values:
            return raw

        best = ranked_values[0]
        second = ranked_values[1] if len(ranked_values) > 1 else None

        if value == best:
            return rf"\textbf{{{raw}}}"
        if second is not None and value == second:
            return rf"\underline{{{raw}}}"
        return raw

    def _metric_label(self, metric_name: str, direction: str) -> str:
        arrow = r" $\uparrow$" if direction == "max" else r" $\downarrow$"
        return f"{escape_latex(metric_name)}{arrow}"

    def _dataset_headers(
        self,
        *,
        dataset_order: list[str],
        metric_order: list[str],
        leading_cols: int,
    ) -> list[dict[str, Any]]:
        headers = []
        current_col = leading_cols + 1
        for dataset_name in dataset_order:
            span = len(metric_order)
            headers.append(
                {
                    "name": escape_latex(dataset_name),
                    "span": span,
                    "start_col": current_col,
                    "end_col": current_col + span - 1,
                }
            )
            current_col += span
        return headers
