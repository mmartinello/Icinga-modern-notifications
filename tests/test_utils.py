"""Tests for the date/time and duration helpers."""

import doctest
import time
import unittest

from icinga_modern_notifications import utils
from icinga_modern_notifications.utils import (
    format_duration,
    format_timestamp,
    parse_duration,
    parse_timestamp,
)


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(utils))
    return tests


class FormatDurationTests(unittest.TestCase):
    def test_examples(self):
        cases = {
            0: "0s",
            1: "1s",
            12: "12s",
            47: "47s",
            59: "59s",
            60: "1m",
            61: "1m 1s",
            74: "1m 14s",
            494: "8m 14s",
            3599: "59m 59s",
            3600: "1h",
            3601: "1h",
            3660: "1h 1m",
            12420: "3h 27m",
            86399: "23h 59m",
            86400: "1d",
            86460: "1d",
            90000: "1d 1h",
            187200: "2d 4h",
            187259: "2d 4h",
        }
        for seconds, expected in cases.items():
            with self.subTest(seconds=seconds):
                self.assertEqual(format_duration(seconds), expected)

    def test_negative_is_rejected(self):
        with self.assertRaises(ValueError):
            format_duration(-1)

    def test_custom_precision(self):
        self.assertEqual(format_duration(90061, precision=3), "1d 1h 1m")
        self.assertEqual(format_duration(90061, precision=1), "1d")


class FormatTimestampTests(unittest.TestCase):
    def test_default_format(self):
        ts = time.mktime((2026, 9, 28, 15, 42, 31, 0, 0, -1))
        self.assertEqual(format_timestamp(ts), "28/09/2026 15:42:31")

    def test_custom_format(self):
        ts = time.mktime((2026, 9, 28, 15, 42, 31, 0, 0, -1))
        self.assertEqual(format_timestamp(ts, "%Y-%m-%d"), "2026-09-28")


class ParseTests(unittest.TestCase):
    def test_parse_timestamp(self):
        self.assertEqual(parse_timestamp("1790000000"), 1790000000.0)
        self.assertEqual(parse_timestamp(" 1790000000.25 "), 1790000000.25)

    def test_parse_duration(self):
        self.assertEqual(parse_duration("0"), 0)
        self.assertEqual(parse_duration("74"), 74)
        self.assertEqual(parse_duration("74.9"), 74)

    def test_invalid_values(self):
        for value in ("", "abc", "-1", "nan", "inf", "1e999"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    parse_timestamp(value)
                with self.assertRaises(ValueError):
                    parse_duration(value)


if __name__ == "__main__":
    unittest.main()
