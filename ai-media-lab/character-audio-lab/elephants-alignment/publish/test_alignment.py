import unittest
import numpy as np
from align_production_dialogue import normalized_match, group_anchors, union_intervals, refine_local_offset

class AlignmentTests(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.default_rng(19)

    def test_known_delay_in_noise(self):
        source = self.rng.normal(size=400)
        movie = self.rng.normal(scale=.1, size=3000)
        movie[821:1221] += source
        lag, coefficient = normalized_match(movie, source)
        self.assertEqual(lag, 821)
        self.assertGreater(coefficient, .99)

    def test_polarity_reversal_is_detected(self):
        source = self.rng.normal(size=200)
        movie = np.zeros(1000)
        movie[307:507] = -source
        lag, coefficient = normalized_match(movie, source)
        self.assertEqual(lag, 307)
        self.assertAlmostEqual(coefficient, -1., places=6)

    def test_silent_anchor_rejected(self):
        with self.assertRaises(ValueError):
            normalized_match(np.zeros(100), np.zeros(20))

    def test_edit_offsets_form_distinct_groups(self):
        anchors = [dict(source_start=t, offset=o, correlation=.9)
                   for t, o in [(0., 14.), (.4, 14.001), (.8, 15.), (1.2, 15.001)]]
        groups = group_anchors(anchors)
        self.assertEqual([len(g) for g in groups], [2, 2])

    def test_isolated_and_weak_matches_not_accepted(self):
        anchors = [dict(source_start=0., offset=14., correlation=.9),
                   dict(source_start=.4, offset=14., correlation=.3)]
        self.assertEqual(group_anchors(anchors), [])

    def test_duplicate_union_not_double_counted(self):
        merged = union_intervals([(1, 5), (1.1, 4.9), (4, 6), (8, 9)])
        self.assertEqual(merged, [[1, 6], [8, 9]])
        self.assertEqual(sum(b-a for a, b in merged), 6)

    def test_fullrate_local_refinement(self):
        rate = 1000
        source = self.rng.normal(size=3000)
        movie = self.rng.normal(scale=.05, size=6000)
        movie[1234:4234] += source
        anchors = refine_local_offset(movie, source, .2, 2.2, 1.23, rate)
        self.assertTrue(anchors)
        self.assertTrue(all(a['offset_samples'] == 1234 for a in anchors))

if __name__ == '__main__':
    unittest.main()
