"""Constructs eleven small, deliberately fictional JRA-shaped race examples."""
from itertools import combinations, permutations
import json
from pathlib import Path

MARKETS = ("win", "place", "quinella", "wide", "exacta", "trio", "trifecta")


def make_race(month):
    horses = (1, 2, 3, 4)
    win = {str(h): round(2.1 + h * 1.7 + month * .01, 1) for h in horses}
    place = {str(h): [round(1.1 + .2 * h, 1), round(1.5 + .4 * h, 1)] for h in horses}
    combos = {
        "win": [(h,) for h in horses], "place": [(h,) for h in horses],
        "quinella": list(combinations(horses, 2)),
        "wide": list(combinations(horses, 2)),
        "exacta": list(permutations(horses, 2)),
        "trio": list(combinations(horses, 3)),
        "trifecta": list(permutations(horses, 3)),
    }
    markets = {}
    for market, selections in combos.items():
        records = []
        for i, elements in enumerate(selections):
            combo = "-".join(map(str, elements))
            if market == "win": odd = win[str(elements[0])]
            elif market == "place": odd = place[str(elements[0])]
            elif market == "wide": odd = [float(i + 2), float(i + 4)]
            else: odd = round(i * 6.1 + (5 if market == "quinella" else 15), 1)
            records.append({"combination": combo, "odds": odd, "popularity": i + 1})
        markets[market] = records
    winners = {"win": ["2"], "place": ["1", "2", "3"],
               "quinella": ["1-2"], "wide": ["1-2", "1-3", "2-3"],
               "exacta": ["2-1"], "trio": ["1-2-3"], "trifecta": ["2-1-3"]}
    return {"synthetic": True, "market": "JRA", "race_id": f"DEMO-NONOFFICIAL-2026{month:02d}-01",
            "date": f"2026-{month:02d}-01", "active_horses": list(horses),
            "win_odds": win, "place_odds": place, "markets": markets,
            "official_result": {
                "independently_verified": True,
                "finish_positions": {"2": 1, "1": 2, "3": 3, "4": 4},
                "winning_tickets": {m: [{"combination": c, "payout_yen": (i + 1) * 1500,
                                         "popularity": i + 1}
                                        for i, c in enumerate(winners[m])]
                                    for m in MARKETS}
            }}


def main():
    p = Path(__file__).parent / "synthetic"
    p.mkdir(parents=True, exist_ok=True)
    for month in range(1, 12):
        (p / f"2026-{month:02d}.jsonl").write_text(
            json.dumps(make_race(month), ensure_ascii=False) + "\n", encoding="utf-8")
    print("Generated 11 clearly fictional demonstration records; NO JRA original odds included")


if __name__ == "__main__":
    main()
