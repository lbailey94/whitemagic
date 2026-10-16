import unittest
from peb10_timing_stats import FLOOR, parse_sample, summarize


class TimingQualificationTests(unittest.TestCase):
    def test_rounded_140_percent_does_not_pass_full_precision_floor(self):
        sample = {"speedup_x": 1.39844}
        self.assertEqual(f"{sample['speedup_x']:.2f}", "1.40")
        self.assertLess(summarize([sample]), FLOOR)

    def test_median_is_used_for_repeatable_qualification(self):
        self.assertEqual(
            summarize([{"speedup_x": 1.0}, {"speedup_x": 1.5}, {"speedup_x": 2.0}]),
            1.5,
        )

    def test_missing_samples_have_no_qualifying_median(self):
        self.assertIsNone(summarize([]))

    def test_requires_full_precision_sample_marker(self):
        self.assertIsNone(parse_sample("speedup=1.40x"))
        self.assertEqual(
            parse_sample("PEB10_TIMING_SAMPLE pulse_us=100 dag_emulated_us=139.844 speedup=1.39844"),
            {"pulse_avg_us": 100.0, "dag_emulated_avg_us": 139.844, "speedup_x": 1.39844},
        )


if __name__ == "__main__":
    unittest.main()
