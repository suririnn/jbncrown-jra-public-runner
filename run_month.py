"""Monthly CLI. Public workflow runs demo-only; no private materials required."""
import argparse
import json
from pathlib import Path
import sys

from jbn_public.research import analyze


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--month", required=True, choices=[f"{i:02d}" for i in range(1, 12)])
    p.add_argument("--input-dir", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--odds-config", default="config/DEMO_ONLY_bounds.json")
    p.add_argument("--payout-config", default="config/DEMO_ONLY_payout_bounds.json")
    p.add_argument("--demo-only", action="store_true")
    args = p.parse_args()
    if not args.demo_only:
        sys.exit("Safety gate: the public runner is demo-only until a verified private-data bridge is approved")
    input_path = Path(args.input_dir) / f"2026-{args.month}.jsonl"
    if not input_path.is_file():
        sys.exit("Missing explicit synthetic demo input: " + str(input_path))
    races = [json.loads(line) for line in input_path.read_text(encoding="utf-8").splitlines()
             if line.strip()]
    if not races or any(not x.get("synthetic") for x in races):
        sys.exit("Safety gate refused real/private or unmarked data")
    if any(x["date"][5:7] != args.month for x in races):
        sys.exit("A race was placed in the wrong calendar month")
    odds = json.loads(Path(args.odds_config).read_text(encoding="utf-8"))
    payouts = json.loads(Path(args.payout_config).read_text(encoding="utf-8"))
    result = analyze(races, odds, payouts, source_type="synthetic_demo")
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"2026-{args.month}.json").write_text(json.dumps(result, ensure_ascii=False,
                                                          indent=2) + "\n", encoding="utf-8")
    print(f"SYNTHETIC_TEST_ONLY month={args.month} races={result['races']} "
          f"position_series={'any' if any('position_series' in k for k in result['sufficient_statistics']) else 'none'}")


if __name__ == "__main__":
    main()
