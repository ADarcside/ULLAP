"""Focused tests for py/run_questa_regression.py (pass criteria and license environment). No simulator is run."""
import os
import sys
import unittest
from unittest import mock

import io

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_questa_regression as rq

LIC = rq.LIC_VARS


class TestPassCriteria(unittest.TestCase):
    def test_pass_requires_rc0_and_marker(self):
        self.assertTrue(rq.is_pass(0, "# TB_RESULT PASS vec=x\n", "TB_RESULT"))
        self.assertFalse(rq.is_pass(1, "# TB_RESULT PASS vec=x\n", "TB_RESULT"))   # non-zero exit
        self.assertFalse(rq.is_pass(0, "# nothing printed\n", "TB_RESULT"))          # no marker
        self.assertFalse(rq.is_pass(0, "TB_RESULT FAIL vec=x\n", "TB_RESULT"))
        self.assertFalse(rq.is_pass(0, "TB_RESULT PASS a\nTB_RESULT FAIL b\n", "TB_RESULT"))
        self.assertFalse(rq.is_pass(0, "echo TB_RESULT PASS in a message\n", "TB_RESULT"))  # not an explicit marker line
        self.assertTrue(rq.is_pass(0, "TB_PROTO PASS ALGO=0\n", "TB_PROTO"))
        self.assertFalse(rq.is_pass(0, "TB_RESULT PASS x\n", "TB_PROTO"))
        self.assertTrue(rq.is_pass(0, "TB_TOP PASS T1_i2c\n", "TB_TOP"))
        self.assertFalse(rq.is_pass(0, "TB_RESULT PASS x\n", "TB_TOP"))

    def _run(self, rc, out):
        with mock.patch.object(rq, "run_cmd", return_value=(rc, out)), \
             mock.patch("sys.stdout", new_callable=io.StringIO):
            return rq.run_manifest_tests("shipped_lms_W11_stationary"), rq.run_protocol_tests(), rq.run_hold_tests(), rq.run_top_tests()

    def test_runner_counts_pass_only_when_rc0_and_marker(self):
        m, p, h, t = self._run(0, "TB_RESULT PASS ok\nTB_PROTO PASS ok\nTB_TOP PASS ok\n")
        self.assertTrue(all(r["passed"] for r in m + p + h + t) and len(m) == 1 and len(p) == 4 and len(h) == 3 and len(t) == 11)
        m, p, h, t = self._run(2, "TB_RESULT PASS ok\nTB_PROTO PASS ok\nTB_TOP PASS ok\n")
        self.assertFalse(any(r["passed"] for r in m + p + h + t))
        m, p, h, t = self._run(0, "")
        self.assertFalse(any(r["passed"] for r in m + p + h + t))


class TestLicenseEnv(unittest.TestCase):
    def _env(self, base, lic=None, default_exists=False):
        with mock.patch.dict(os.environ, base, clear=True), \
             mock.patch.object(rq, "LIC_PATH", lic), \
             mock.patch.object(rq.os.path, "isfile", return_value=default_exists):
            return rq.get_env()

    def test_existing_license_preserved(self):
        e = self._env({"LM_LICENSE_FILE": "1717@server"}, default_exists=True)
        self.assertEqual(e["LM_LICENSE_FILE"], "1717@server")
        self.assertNotIn("SALT_LICENSE_SERVER", e)
        self.assertNotIn("MGLS_LICENSE_FILE", e)

    def test_explicit_override_wins(self):
        e = self._env({"LM_LICENSE_FILE": "1717@server"}, lic="/my/lic.dat")
        for v in LIC:
            self.assertEqual(e[v], "/my/lic.dat")

    def test_default_used_only_if_valid(self):
        e = self._env({}, default_exists=True)
        for v in LIC:
            self.assertEqual(e[v], rq.DEFAULT_LIC_PATH)
        e = self._env({}, default_exists=False)
        for v in LIC:
            self.assertNotIn(v, e)


if __name__ == "__main__":
    unittest.main()
