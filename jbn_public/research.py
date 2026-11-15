"""Original, independent JRA research calculation engine.

NO private code or private original records are imported. A public runner is
allowed to exercise this module with clearly marked synthetic data only.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations, permutations
import hashlib
import json
import math
import re

MARKETS = ("win", "place", "quinella", "wide", "exacta", "trio", "trifecta")
MARKET_JP = dict(zip(MARKETS, ("単勝", "複勝", "馬連", "ワイド", "馬単", "3連複", "3連単")))
CONDITIONS = ("①②③", "①②", "①③", "②③", "①", "②", "③")
SERIES = {f"{family}{i}": market for family in "ABC" for i, market in
          enumerate(("exacta", "wide", "trio", "trifecta"), 1)}
UNORDERED = {"quinella", "wide", "trio"}
POPULARITY_BINS = ("1–2", "3", "4–5", "6–10", "11–20", "21–39", "40+")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def rank_band(rank):
    if not isinstance(rank, int) or rank < 1:
        return "unavailable"
    if rank <= 2: return "1–2"
    if rank == 3: return "3"
    if rank <= 5: return "4–5"
    if rank <= 10: return "6–10"
    if rank <= 20: return "11–20"
    if rank <= 39: return "21–39"
    return "40+"


def band(value, thresholds):
    if value is None:
        return "not_numeric"
    if isinstance(value, list):
        if len(value) != 2 or not all(isinstance(x, (int, float)) for x in value):
            return "invalid_interval"
        lo, hi = value
        if not (0 < lo <= hi and math.isfinite(lo) and math.isfinite(hi)):
            return "invalid_interval"
        lo_bin, hi_bin = band(lo, thresholds), band(hi, thresholds)
        return lo_bin if lo_bin == hi_bin else "spans_bins"
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        return "not_numeric"
    if value <= 0: return "not_sold_or_zero"
    return str(sum(value >= x for x in thresholds))


def normalized_combo(combo, market):
    parts = combo.split("-")
    expected = 1 if market in ("win", "place") else 2 if market in ("quinella", "wide", "exacta") else 3
    if len(parts) != expected or not all(x.isdecimal() and int(x) >= 1 for x in parts):
        raise ValueError(f"Invalid combination {combo!r} in market {market}")
    if len(set(parts)) != len(parts):
        raise ValueError("Duplicate horse within ticket")
    if market in UNORDERED:
        return "-".join(map(str, sorted(map(int, parts))))
    return "-".join(map(str, map(int, parts)))


def feature_bins(win, quinella):
    # The three axes are the user's protected semantic definitions.
    nums = [v for v in win.values() if isinstance(v, (int, float)) and v > 0]
    if len(nums) != len(win):
        raise ValueError("All active win odds are required for ① and ②")
    if not quinella:
        raise ValueError("All quinella combinations are required for ③")
    minimum = min(nums)
    a = "≤1.5" if minimum <= 1.5 else "1.6–2.0" if minimum <= 2 else "2.1–3.0" if minimum <= 3 else "3.1–5.0" if minimum <= 5 else "5.1+"
    b_count = sum(x <= 9.9 for x in nums)
    c_count = sum(isinstance(x, (int, float)) and 0 < x <= 9.9 for x in quinella.values())
    b = "0–1" if b_count <= 1 else str(b_count) if b_count <= 4 else "5+"
    c = str(c_count) if c_count <= 3 else "4+"
    return {"①": a, "②": b, "③": c}


def views(features):
    for condition in CONDITIONS:
        yield (condition, "|".join(f"{c}={features[c]}" for c in condition))
    yield ("baseline", "all")


def validate_edges(edges, enforce_quinella=True):
    if set(edges) != set(MARKETS):
        raise ValueError("Fixed thresholds for all 7 markets are required")
    for market, v in edges.items():
        if len(v) != 5 or sorted(set(v)) != v or any(not isinstance(x, (int, float)) or x <= 0 for x in v):
            raise ValueError("Every market must have five ascending fixed thresholds: " + market)
    if enforce_quinella and edges["quinella"] != [5, 10, 20, 50, 100]:
        raise ValueError("Protected quinella six-band boundaries must not change")


def record_map(rows, market, active):
    out = {}
    for obj in rows:
        combo = normalized_combo(str(obj["combination"]), market)
        members = [int(n) for n in combo.split("-")]
        if any(h not in active for h in members):
            raise ValueError("Cancelled/excluded horse listed as active: " + combo)
        if combo in out:
            raise ValueError("Duplicate combo: " + combo)
        out[combo] = obj
    return out


def validate_race(race):
    if race.get("market") != "JRA":
        raise ValueError("JRA and NAR/ばんえい may never mix")
    date = race.get("date", "")
    if not re.fullmatch(r"2026-(0[1-9]|1[01])-(0[1-9]|[12][0-9]|3[01])", date):
        raise ValueError("Outside Jan–Nov 2026 or invalid date")
    if not race.get("race_id"):
        raise ValueError("race_id is required")
    active = set(int(x) for x in race["active_horses"])
    if len(active) < 3 or len(active) != len(race["active_horses"]):
        raise ValueError("Invalid active horse set")
    win = {str(k): v for k, v in race["win_odds"].items()}
    if {int(x) for x in win} != active:
        raise ValueError("Win odds must match active horse set")
    place = {str(k): v for k, v in race["place_odds"].items()}
    if set(place) != set(win):
        raise ValueError("Place odds must match active horse set")
    if set(race["markets"]) != set(MARKETS):
        raise ValueError("All seven original odds markets are required")
    parsed = {m: record_map(race["markets"][m], m, active) for m in MARKETS}
    n = len(active)
    expected = {"win": n, "place": n, "quinella": n*(n-1)//2,
                "wide": n*(n-1)//2, "exacta": n*(n-1),
                "trio": math.comb(n, 3), "trifecta": n*(n-1)*(n-2)}
    for m in MARKETS:
        if len(parsed[m]) != expected[m]:
            raise ValueError(f"Incomplete {m}: {len(parsed[m])} / {expected[m]}")
    for horse in active:
        if str(horse) not in parsed["win"] or str(horse) not in parsed["place"]:
            raise ValueError("Market and horse labels disagree")
    # The rest of the combinatorial identity must match, not just lengths.
    sorted_h = sorted(active)
    for m, expected_keys in (("quinella", combinations(sorted_h, 2)),
                             ("wide", combinations(sorted_h, 2)),
                             ("exacta", permutations(sorted_h, 2)),
                             ("trio", combinations(sorted_h, 3)),
                             ("trifecta", permutations(sorted_h, 3))):
        canonical = {"-".join(map(str, c)) for c in expected_keys}
        if set(parsed[m]) != canonical:
            raise ValueError("Complete count but incorrect composition in " + m)
    quinella = {k: x.get("odds") for k, x in parsed["quinella"].items()}
    features = feature_bins(win, quinella)
    result = race.get("official_result")
    if result:
        if not result.get("independently_verified"):
            raise ValueError("Unverified actual outcomes cannot be scored")
        if not race.get("synthetic"):
            for label in ("official_result_sha256", "original_final_odds_sha256"):
                if not HEX64.fullmatch(result.get(label, "")):
                    raise ValueError("Required independent provenance SHA missing")
        positions = {int(k): int(v) for k, v in result["finish_positions"].items()}
        if set(positions) != active or not all(x >= 1 for x in positions.values()):
            raise ValueError("Incomplete official finish positions")
        if set(result["winning_tickets"]) != set(MARKETS):
            raise ValueError("All seven official winning markets required")
        for m, winners in result["winning_tickets"].items():
            if not winners:
                raise ValueError("Official payout set empty: " + m)
            seen = set()
            for x in winners:
                k = normalized_combo(x["combination"], m)
                if k in seen or k not in parsed[m]:
                    raise ValueError("Official winning combo inconsistent: " + m + ":" + k)
                seen.add(k)
                if not isinstance(x["payout_yen"], int) or x["payout_yen"] <= 0:
                    raise ValueError("Official payout not a positive integer")
    return parsed, features


def increment(stats, cat, key, **values):
    ident = json.dumps([cat, *key], ensure_ascii=False, separators=(",", ":"))
    row = stats.setdefault(ident, {})
    for k, v in values.items():
        row[k] = row.get(k, 0) + v


def analyze(races, odds_edges, payout_edges, source_type="synthetic_demo"):
    validate_edges(odds_edges)
    validate_edges(payout_edges, enforce_quinella=False)
    stats = {}
    seen_ids = set()
    source_dates = Counter()
    total = scored = 0
    for race in races:
        if race["race_id"] in seen_ids:
            raise ValueError("Duplicate unique race across inputs")
        seen_ids.add(race["race_id"])
        parsed, features = validate_race(race)
        labels = list(views(features))
        total += 1
        source_dates[race["date"][:7]] += 1
        official = race.get("official_result")
        if official:
            scored += 1
        for cond, signature in labels:
            increment(stats, "races", (cond, signature), total_races=1,
                      independently_scored_races=int(bool(official)))
        for market, tickets in parsed.items():
            for combo, entry in tickets.items():
                ticket_band = band(entry.get("odds"), odds_edges[market])
                popularity = rank_band(entry.get("popularity"))
                official_hits = {}
                if official:
                    official_hits = {normalized_combo(w["combination"], market): w
                                     for w in official["winning_tickets"][market]}
                for cond, signature in labels:
                    increment(stats, "ticket_band", (cond, signature, market, ticket_band),
                              saved_combos=1, final_odds_popularity_known=int(popularity != "unavailable"),
                              officially_scored_combos=int(bool(official)),
                              official_hit=int(bool(official) and combo in official_hits))
                if not official or combo not in official_hits:
                    continue
                win_entry = official_hits[combo]
                payout_band = band(win_entry["payout_yen"], payout_edges[market])
                won_pop = rank_band(win_entry.get("popularity"))
                for cond, signature in labels:
                    increment(stats, "payout", (cond, signature, market, won_pop, payout_band),
                              winners=1, equal_race_share=1 / len(official_hits))
        # Win- and quinella-odds input axes for each target market (7 conditions x 7 markets).
        for source_market in ("win", "quinella"):
            for v in parsed[source_market].values():
                sb = band(v.get("odds"), odds_edges[source_market])
                for cond, signature in labels:
                    increment(stats, "input_axis", (cond, signature, source_market, sb), observations=1)
        if not official:
            continue
        positions = {int(k): int(v) for k, v in official["finish_positions"].items()}
        win_bands = {int(h): band(v, odds_edges["win"]) for h, v in race["win_odds"].items()}
        place_bands = {int(h): band(v, odds_edges["place"]) for h, v in race["place_odds"].items()}
        for h, pos in positions.items():
            for cond, signature in labels:
                for source, b in (("win", win_bands[h]), ("place", place_bands[h])):
                    increment(stats, "horse_finish", (cond, signature, source, b),
                              observations=1, first=int(pos == 1), second=int(pos == 2), third=int(pos == 3))
        for sid, market in SERIES.items():
            winners = {normalized_combo(x["combination"], market)
                       for x in official["winning_tickets"][market]}
            for combo, ticket in parsed[market].items():
                tb = band(ticket.get("odds"), odds_edges[market])
                hit = int(combo in winners)
                horse_numbers = [int(x) for x in combo.split("-")]
                for slot, horse in enumerate(horse_numbers, 1):
                    source = (win_bands[horse] if sid[0] == "A" else
                              place_bands[horse] if sid[0] == "B" else
                              win_bands[horse] + "&" + place_bands[horse])
                    role = "unordered_member" if market in ("wide", "trio") else f"position_{slot}"
                    finish = positions[horse]
                    for cond, signature in labels:
                        increment(stats, "position_series", (cond, signature, sid, market, tb, role, source),
                                  member_observations=1, linked_ticket_hits=hit,
                                  first=int(finish == 1), second=int(finish == 2), third=int(finish == 3),
                                  correct_order_slot=int(role != "unordered_member" and finish == slot))
    return {"schema":"PUBLIC_CODE_ONLY_JRA_RESEARCH_V1", "source_type":source_type,
            "races":total,"officially_scored_races":scored,
            "observed_months":dict(sorted(source_dates.items())),
            "odds_edges_sha256":hashlib.sha256(json.dumps(odds_edges, sort_keys=True).encode()).hexdigest(),
            "payout_edges_sha256":hashlib.sha256(json.dumps(payout_edges, sort_keys=True).encode()).hexdigest(),
            "race_ids_sorted":sorted(seen_ids), "sufficient_statistics":stats,
            "NOT_prestart_validation":True, "NOT_original_model":True,
            "NOT_independently_trained_12_models":True}


def merge(results):
    if len(results) != 11:
        raise ValueError("Eleven monthly partitions required")
    ids = set()
    stats = {}
    total = scored = 0
    edges = None
    for r in results:
        hashes = (r["odds_edges_sha256"], r["payout_edges_sha256"])
        if edges is None: edges = hashes
        if edges != hashes: raise ValueError("Month-specific bin boundaries cannot be pooled")
        duplicate = ids.intersection(r["race_ids_sorted"])
        if duplicate: raise ValueError("Cross-month duplicate: " + str(sorted(duplicate)[:3]))
        ids.update(r["race_ids_sorted"])
        total += r["races"]
        scored += r["officially_scored_races"]
        for key, values in r["sufficient_statistics"].items():
            merged = stats.setdefault(key, {})
            for metric, value in values.items():
                merged[metric] = merged.get(metric, 0) + value
    if total != len(ids) or scored > total:
        raise ValueError("Consolidated denominators are inconsistent")
    return {"schema":"PUBLIC_CODE_ONLY_JRA_MERGE_V1","races":total,
            "officially_scored_races":scored,
            "month_count":len(results),"sufficient_statistics":stats,
            "final_coverage":"PARTIAL_UNLESS_AUTHENTICATED_EXTERNAL_MASTER_MANIFEST_MATCHES",
            "production_adoptions":0,
            "source_type":"synthetic_only" if all(x["source_type"] == "synthetic_demo" for x in results) else "mixed_or_real_private",
            "NOT_prestart_validation":True}
