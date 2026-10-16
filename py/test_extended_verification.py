"""Unit test adapter for extended RTL verification suite."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from verify_core import run_verification_suite

ROOT = os.path.dirname(HERE)


class TestExtendedVerification(unittest.TestCase):
    def test_extended_verification_suite(self):
        wav_file = os.path.join(ROOT, "vectors", "audio", "acoustic_chord.wav")
        passed, summary = run_verification_suite(wav_file if os.path.exists(wav_file) else None)
        self.assertTrue(passed, f"Verification suite failed: {summary}")


if __name__ == "__main__":
    unittest.main()
