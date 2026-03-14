from __future__ import annotations

from statistics import mean, stdev
from typing import Iterable


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


def _ordered_unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _metric_heading(metric_name: str, higher_is_better: bool | None) -> str:
    arrow = r" $\uparrow$" if higher_is_better is not False else r" $\downarrow$"
    return f"{escape_latex(metric_name)}{arrow}"


def _format_numeric(
    values: list[float],
    precision: int,
    *,
    show_std: bool,
    omit_zero_std: bool,
) -> tuple[str, float]:
    avg = mean(values)
    if show_std and len(values) > 1:
        deviation = stdev(values)
        if omit_zero_std and abs(deviation) < 1e-12:
            return f"{avg:.{precision}f}", avg
        return f"{avg:.{precision}f} $\\pm$ {deviation:.{precision}f}", avg
    return f"{avg:.{precision}f}", avg


def _decorate_value(
    raw: str,
    score: float,
    ranked_scores: list[float],
    higher_is_better: bool,
    highlight_best: bool,
    highlight_second: bool,
) -> str:
    if not ranked_scores:
        return raw

    best = ranked_scores[0]
    second = ranked_scores[1] if len(ranked_scores) > 1 else None

    if highlight_best and score == best:
        return rf"\textbf{{{raw}}}"
    if highlight_second and second is not None and score == second:
        return rf"\underline{{{raw}}}"
    return raw


def render_latex_table(
    *,
    model_order: list[str],
    dataset_order: list[str],
    metric_order: list[str],
    cell_values: dict[tuple[str, str, str], list[float]],
    metric_directions: dict[str, bool],
    caption: str,
    label: str,
    note: str | None,
    placement: str,
    precision: int,
    highlight_best: bool,
    highlight_second: bool,
    use_resizebox: bool,
    compact: bool,
    show_std: bool,
    omit_zero_std: bool,
    use_threeparttable: bool,
    table_environment: str,
    column_group_by: str,
) -> str:
    if not model_order or not dataset_order or not metric_order:
        raise ValueError("No table data available for LaTeX generation.")

    if column_group_by == "metric":
        column_headers = [(dataset_name, metric_name) for metric_name in metric_order for dataset_name in dataset_order]
    else:
        column_headers = [(dataset_name, metric_name) for dataset_name in dataset_order for metric_name in metric_order]
    align = "l" + "c" * len(column_headers)

    ranked_by_column: dict[tuple[str, str], list[float]] = {}
    for dataset_name, metric_name in column_headers:
        scores = []
        for model_name in model_order:
            values = cell_values.get((model_name, dataset_name, metric_name))
            if not values:
                continue
            _, avg = _format_numeric(
                values,
                precision,
                show_std=show_std,
                omit_zero_std=omit_zero_std,
            )
            scores.append(avg)
        reverse = metric_directions.get(metric_name, True)
        unique_scores = sorted(set(scores), reverse=reverse)
        ranked_by_column[(dataset_name, metric_name)] = unique_scores

    lines: list[str] = [rf"\begin{{{table_environment}}}[{placement}]", r"\centering"]
    if compact:
        lines.append(r"\small")
        lines.append(r"\setlength{\tabcolsep}{4pt}")
    lines.append(rf"\caption{{{escape_latex(caption)}}}")
    lines.append(rf"\label{{{label}}}")
    if use_threeparttable:
        lines.append(r"\begin{threeparttable}")

    tabular_lines = [rf"\begin{{tabular}}{{{align}}}", r"\toprule"]

    if len(dataset_order) > 1 and column_group_by == "dataset":
        first_header = ["Model"]
        cmidrules: list[str] = []
        col_idx = 2
        for dataset_name in dataset_order:
            span = len(metric_order)
            first_header.append(rf"\multicolumn{{{span}}}{{c}}{{{escape_latex(dataset_name)}}}")
            cmidrules.append(rf"\cmidrule(lr){{{col_idx}-{col_idx + span - 1}}}")
            col_idx += span
        tabular_lines.append(" & ".join(first_header) + r" \\")
        tabular_lines.append("".join(cmidrules))
    elif len(metric_order) > 1 and column_group_by == "metric":
        first_header = ["Model"]
        cmidrules = []
        col_idx = 2
        for metric_name in metric_order:
            span = len(dataset_order)
            first_header.append(rf"\multicolumn{{{span}}}{{c}}{{{escape_latex(metric_name)}}}")
            cmidrules.append(rf"\cmidrule(lr){{{col_idx}-{col_idx + span - 1}}}")
            col_idx += span
        tabular_lines.append(" & ".join(first_header) + r" \\")
        tabular_lines.append("".join(cmidrules))

    second_header = [""] if len(dataset_order) > 1 or len(metric_order) > 1 else ["Model"]
    for dataset_name, metric_name in column_headers:
        if column_group_by == "metric":
            second_header.append(escape_latex(dataset_name))
        else:
            second_header.append(_metric_heading(metric_name, metric_directions.get(metric_name)))
    tabular_lines.append(" & ".join(second_header) + r" \\")
    tabular_lines.append(r"\midrule")

    for model_name in model_order:
        row = [escape_latex(model_name)]
        for dataset_name, metric_name in column_headers:
            values = cell_values.get((model_name, dataset_name, metric_name))
            if not values:
                row.append("--")
                continue
            raw, avg = _format_numeric(
                values,
                precision,
                show_std=show_std,
                omit_zero_std=omit_zero_std,
            )
            decorated = _decorate_value(
                raw=raw,
                score=avg,
                ranked_scores=ranked_by_column[(dataset_name, metric_name)],
                higher_is_better=metric_directions.get(metric_name, True),
                highlight_best=highlight_best,
                highlight_second=highlight_second,
            )
            row.append(decorated)
        tabular_lines.append(" & ".join(row) + r" \\")

    tabular_lines.append(r"\bottomrule")
    tabular_lines.append(r"\end{tabular}")
    tabular_block = "\n".join(tabular_lines)

    if use_resizebox:
        lines.append(r"\resizebox{\linewidth}{!}{%")
        lines.append(tabular_block)
        lines.append(r"}")
    else:
        lines.append(tabular_block)

    default_note = (
        "Cells report mean $\\pm$ std when multiple runs are selected; otherwise they report single-run values. "
        "Best results are bold and second-best results are underlined."
    )
    final_note = escape_latex(note.strip()) if note else default_note
    if use_threeparttable:
        lines.append(rf"\begin{{tablenotes}}\footnotesize \item {final_note}\end{{tablenotes}}")
        lines.append(r"\end{threeparttable}")
    else:
        lines.append(rf"\vspace{{2pt}}\begin{{minipage}}{{0.98\linewidth}}\footnotesize {final_note}\end{{minipage}}")
    lines.append(rf"\end{{{table_environment}}}")
    return "\n".join(lines)


def normalize_orders(
    *,
    model_names: Iterable[str],
    dataset_names: Iterable[str],
    metric_names: Iterable[str],
    requested_models: list[str] | None = None,
    requested_datasets: list[str] | None = None,
    requested_metrics: list[str] | None = None,
) -> tuple[list[str], list[str], list[str]]:
    model_pool = _ordered_unique(model_names)
    dataset_pool = _ordered_unique(dataset_names)
    metric_pool = _ordered_unique(metric_names)

    final_models = [name for name in (requested_models or model_pool) if name in model_pool]
    final_datasets = [name for name in (requested_datasets or dataset_pool) if name in dataset_pool]
    final_metrics = [name for name in (requested_metrics or metric_pool) if name in metric_pool]
    return final_models, final_datasets, final_metrics


def latex_package_hints(*, use_threeparttable: bool, use_resizebox: bool) -> list[str]:
    packages = [r"\usepackage{booktabs}"]
    if use_threeparttable:
        packages.append(r"\usepackage{threeparttable}")
    if use_resizebox:
        packages.append(r"\usepackage{graphicx}")
    return packages


def guideline_notes() -> list[str]:
    return [
        "Place the caption above the table and keep labels stable for cross-referencing.",
        "Use booktabs-style horizontal rules and avoid vertical lines.",
        "Use bold for best results and a secondary marker such as underline for runner-up results.",
        "If multiple runs are reported, show mean plus/minus standard deviation and explain the protocol in a note.",
    ]
