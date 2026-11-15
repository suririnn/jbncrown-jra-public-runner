"""Merge private local or synthetic per-month sufficient statistics by total counts."""
import argparse
import json
from pathlib import Path
from jbn_public.research import merge


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input-dir", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--demo-only", action="store_true")
    args = p.parse_args()
    folder = Path(args.input_dir)
    months = [json.loads((folder / f"2026-{i:02d}.json").read_text(encoding="utf-8"))
              for i in range(1, 12)]
    if args.demo_only and any(m["source_type"] != "synthetic_demo" for m in months):
        raise ValueError("Public workflow cannot ingest real data")
    final = merge(months)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(final, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{'SYNTHETIC_TEST_ONLY' if args.demo_only else 'LOCAL_PRIVATE_AGGREGATION'} "
          f"merged_months={final['month_count']} distinct={final['races']}; "
          f"full_JRA_collection_NOT_claimed")


if __name__ == "__main__":
    main()
