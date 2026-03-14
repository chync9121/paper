from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def generate_performance_bar_chart(df: pd.DataFrame, output_path: Path, metric_name: str) -> Path:
    chart_df = df[df["metric_name"] == metric_name].copy()
    if chart_df.empty:
        raise ValueError(f"No rows available for metric: {metric_name}")

    chart_df["label"] = chart_df["model_name"] + "\n" + chart_df["dataset_name"]
    grouped = chart_df.groupby("label", as_index=False)["metric_value"].mean()

    plt.figure(figsize=(8.6, 3.8))
    plt.bar(grouped["label"], grouped["metric_value"], color="#0f6db8")
    plt.ylabel(metric_name)
    plt.xticks(rotation=18, ha="right")
    plt.grid(axis="y", linestyle="--", alpha=0.25)
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=240, bbox_inches="tight")
    plt.close()
    return output_path


def generate_metric_scatter_chart(df: pd.DataFrame, output_path: Path, x_metric: str, y_metric: str) -> Path:
    x_df = df[df["metric_name"] == x_metric][["run_id", "model_name", "dataset_name", "metric_value"]].rename(
        columns={"metric_value": "x_value"}
    )
    y_df = df[df["metric_name"] == y_metric][["run_id", "metric_value"]].rename(columns={"metric_value": "y_value"})
    merged = x_df.merge(y_df, on="run_id", how="inner")
    if merged.empty:
        raise ValueError(f"No overlapping rows available for {x_metric} and {y_metric}")

    plt.figure(figsize=(6.8, 4.0))
    for _, row in merged.iterrows():
        plt.scatter(row["x_value"], row["y_value"], s=60, color="#0f766e")
        plt.text(row["x_value"], row["y_value"], row["model_name"], fontsize=8, alpha=0.9)
    plt.xlabel(x_metric)
    plt.ylabel(y_metric)
    plt.grid(linestyle="--", alpha=0.25)
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=240, bbox_inches="tight")
    plt.close()
    return output_path
