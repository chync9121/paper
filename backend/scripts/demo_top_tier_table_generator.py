from __future__ import annotations

import json
from pathlib import Path

from app.services.top_tier_table_generator import TopTierTableGenerator


def main() -> None:
    data_path = Path(__file__).with_name("mock_top_tier_table_data.json")
    payload = json.loads(data_path.read_text(encoding="utf-8"))

    generator = TopTierTableGenerator()
    results = generator.generate_tables(payload)

    print("=== Benchmark Table ===")
    print(results["benchmark_latex"])
    print()
    print("=== Ablation Table ===")
    print(results["ablation_latex"])


if __name__ == "__main__":
    main()
