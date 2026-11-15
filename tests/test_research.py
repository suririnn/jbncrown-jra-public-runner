import copy
import json
from pathlib import Path
import tempfile
import unittest

from examples.create_synthetic import make_race
from jbn_public.research import (CONDITIONS, MARKETS, SERIES, analyze, band,
                                  feature_bins, merge, normalized_combo, validate_race)

ROOT = Path(__file__).resolve().parents[1]
ODDS = json.loads((ROOT / 'config/DEMO_ONLY_bounds.json').read_text())
PAYOUT = json.loads((ROOT / 'config/DEMO_ONLY_payout_bounds.json').read_text())


class ResearchContract(unittest.TestCase):
    def test_7_conditions_and_12_series(self):
        self.assertEqual(len(CONDITIONS), 7)
        self.assertEqual(list(CONDITIONS), ['①②③','①②','①③','②③','①','②','③'])
        self.assertEqual(len(SERIES), 12)
        self.assertEqual(len(MARKETS), 7)
        self.assertEqual(SERIES['A1'], 'exacta')
        self.assertEqual(SERIES['C4'], 'trifecta')

    def test_bands_respect_intervals(self):
        self.assertEqual(band(4.9, [5,10,20,50,100]), '0')
        self.assertEqual(band(5, [5,10,20,50,100]), '1')
        self.assertEqual(band([4.9,5.1], [5,10,20,50,100]), 'spans_bins')
        self.assertEqual(band([5.1,5.7], [5,10,20,50,100]), '1')
        self.assertEqual(band(None, [5,10,20,50,100]), 'not_numeric')

    def test_all_ticket_combos_are_verified_not_only_cardinality(self):
        x = make_race(1)
        validate_race(x)
        x['markets']['quinella'][0]['combination'] = '3-4'
        with self.assertRaisesRegex(ValueError, 'Duplicate combo'):
            validate_race(x)

    def test_unverified_results_rejected(self):
        x = make_race(1)
        x['official_result']['independently_verified'] = False
        with self.assertRaisesRegex(ValueError, 'Unverified'):
            analyze([x], ODDS, PAYOUT)

    def test_non_jra_mixing_rejected(self):
        x = make_race(1)
        x['market'] = 'NAR'
        with self.assertRaisesRegex(ValueError, 'JRA and NAR'):
            analyze([x], ODDS, PAYOUT)

    def test_1r_synthetic_month(self):
        x = analyze([make_race(1)], ODDS, PAYOUT, 'synthetic_demo')
        self.assertEqual(x['races'], 1)
        self.assertEqual(x['officially_scored_races'], 1)
        self.assertEqual(len(x['race_ids_sorted']), 1)
        self.assertEqual(x['NOT_prestart_validation'], True)
        series_ids = {json.loads(k)[3] for k in x['sufficient_statistics']
                      if json.loads(k)[0]=='position_series'}
        self.assertEqual(series_ids, set(SERIES))

    def test_original_123_semantics(self):
        a = feature_bins({'1':1.4,'2':5.1,'3':11.2},{'1-2':6.2,'1-3':12.4,'2-3':9.5})
        self.assertEqual(a, {'①':'≤1.5','②':'2','③':'2'})

    def test_merging_11_months_counts_distinct_and_rates_are_not_averaged(self):
        inputs = [analyze([make_race(i)], ODDS, PAYOUT, 'synthetic_demo') for i in range(1,12)]
        merged = merge(inputs)
        self.assertEqual(merged['races'],11)
        self.assertEqual(merged['officially_scored_races'],11)
        c = json.dumps(['races','baseline','all'], ensure_ascii=False,separators=(',',':'))
        self.assertEqual(merged['sufficient_statistics'][c]['total_races'], 11)
        self.assertEqual(merged['production_adoptions'], 0)
        inputs[1]['race_ids_sorted'][0] = inputs[0]['race_ids_sorted'][0]
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            merge(inputs)

    def test_five_bins_are_same_across_all_months(self):
        inputs = [analyze([make_race(i)], ODDS, PAYOUT, 'synthetic_demo') for i in range(1,12)]
        inputs[9]['odds_edges_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'boundaries'):
            merge(inputs)

    def test_no_private_provenance_unless_real_sha(self):
        x = make_race(1)
        x.pop('synthetic')
        with self.assertRaisesRegex(ValueError, 'provenance'):
            analyze([x], ODDS, PAYOUT, 'real_private')


if __name__ == '__main__':
    unittest.main()
