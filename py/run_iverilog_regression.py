"""Open-source RTL regression (Icarus Verilog) for the ANC FPGA project.

Runs the same testbenches, manifests and pass markers as run_questa_regression.py, so the
regression can be reproduced without a Questa licence:
  1. tb/manifest.txt configurations       (tb_anc_core, bit-exact against golden vectors)
  2. protocol corner cases                (tb_anc_protocol)
  3. tb/manifest_hold.txt configurations  (tb_anc_core_freeze_hold)
  4. DE2-115 top-level tests T1-T8        (tb_top with the WM8731 codec model)

Icarus takes parameters at elaboration time, so each configuration is compiled separately.
Summary: results/metrics/iverilog_regression_summary.txt
"""
import argparse
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_questa_regression import is_pass  # noqa: E402  same PASS/FAIL rule as the Questa runner

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IVERILOG = os.environ.get("ANC_IVERILOG", "iverilog")
VVP = os.environ.get("ANC_VVP", "vvp")
BUILD = os.path.join(ROOT, "build", "iverilog")
OUT_LOG = os.path.join(ROOT, "results", "metrics", "iverilog_regression_summary.txt")

CORE_SRC = ["rtl/anc_core.v"]
TOP_SRC = ["rtl/anc_core.v", "quartus/wm8731_i2c_init.v", "quartus/i2s_transceiver.v",
           "quartus/anc_de2_115_top.v", "tb/codec_model.v", "tb/tb_top.v"]

PROTO_CONFIGS = [  # same list as run_questa_regression.run_protocol_tests
    (0, 11, 8, 512, 4, 25),
    (1, 11, 8, 51, 4, 25),
    (2, 11, 8, 512, 4, 25),
    (2, 11, 2, 512, 4, 23),
]
TOP_SCENARIOS = [("top_T1_i2c", "T1"), ("top_T1b_nack", "T1b"), ("top_T2_bypass", "T2"),
                 ("top_T3_anc", "T3"), ("top_T4_freeze", "T4"), ("top_T5_reset", "T5"),
                 ("top_T6_flags", "T6"), ("top_T7_clock", "T7"), ("top_T8_skew", "T8"),
                 ("top_T9_rate", "T9"), ("top_T10_gpio", "T10")]


def run(cmd):
    p = subprocess.run(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return p.returncode, p.stdout


def compile_and_run(name, top, sources, params, plusargs, marker):
    vvp_file = os.path.join(BUILD, name + ".vvp")
    cmd = [IVERILOG, "-g2005", "-o", vvp_file, "-s", top]
    cmd += [f"-P{top}.{k}={v}" for k, v in params.items()]
    cmd += sources
    rc, out = run(cmd)
    if rc != 0:
        return False, "COMPILE FAIL: " + out.strip().splitlines()[-1] if out.strip() else "COMPILE FAIL"
    rc, out = run([VVP, "-n", vvp_file] + plusargs)
    lines = [l for l in out.splitlines() if marker in l]
    detail = lines[-1].strip() if lines else ("FAIL (no result line)" if rc != 0 else "UNKNOWN")
    return is_pass(rc, out, marker), detail


def read_manifest(path):
    with open(path, encoding="utf-8") as f:
        return [l.split() for l in f if l.strip() and not l.startswith("#")]


def manifest_tests(manifest, tb, filt):
    results = []
    for item in read_manifest(os.path.join(ROOT, "tb", manifest)):
        name, algo, W, L, MU_INT, K, ACC_W, prefix = item[:8]
        eps = item[9] if len(item) > 9 else "10"
        if filt and filt not in name:
            continue
        params = dict(W=W, L=L, ALGO=algo, MU_INT=MU_INT, K=K, ACC_W=ACC_W, EPS_EXP=eps)
        ok, detail = compile_and_run(name, tb, CORE_SRC + [f"tb/{tb}.v"], params, [f"+vec={prefix}"], "TB_RESULT")
        results.append((name, ok, detail))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name:35s}: {detail}", flush=True)
    return results


def protocol_tests(filt):
    results = []
    for algo, W, L, MU_INT, K, ACC_W in PROTO_CONFIGS:
        name = f"proto_algo{algo}_L{L}"
        if filt and filt not in name:
            continue
        params = dict(W=W, L=L, ALGO=algo, MU_INT=MU_INT, K=K, ACC_W=ACC_W)
        ok, detail = compile_and_run(name, "tb_anc_protocol", CORE_SRC + ["tb/tb_anc_protocol.v"], params, [], "TB_PROTO")
        results.append((name, ok, detail))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name:35s}: {detail}", flush=True)
    return results


def top_tests(filt):
    results = []
    vvp_file = os.path.join(BUILD, "tb_top.vvp")
    rc, out = run([IVERILOG, "-g2005", "-o", vvp_file, "-s", "tb_top"] + TOP_SRC)
    if rc != 0:
        return [("tb_top_compile", False, out.strip())]
    for name, arg in TOP_SCENARIOS:
        if filt and filt not in name:
            continue
        rc, out = run([VVP, "-n", vvp_file, f"+test={arg}"])
        lines = [l for l in out.splitlines() if "TB_TOP" in l and "all_completed" not in l]
        lines = lines or [l for l in out.splitlines() if "TB_TOP" in l]
        detail = lines[-1].strip() if lines else "FAIL (no result line)"
        ok = is_pass(rc, out, "TB_TOP")
        results.append((name, ok, detail))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name:35s}: {detail}", flush=True)
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--filter", default="", help="run only tests whose name contains this string")
    args = ap.parse_args()
    if not shutil.which(IVERILOG) or not shutil.which(VVP):
        raise SystemExit("iverilog/vvp not found (install Icarus Verilog or set ANC_IVERILOG / ANC_VVP)")
    os.makedirs(BUILD, exist_ok=True)
    t0 = time.time()
    rc, ver = run([IVERILOG, "-V"])
    version = ver.splitlines()[0] if ver else "unknown"

    sections = [
        ("MANIFEST TESTS", manifest_tests("manifest.txt", "tb_anc_core", args.filter)),
        ("PROTOCOL TESTS", protocol_tests(args.filter)),
        ("HOLD / TOGGLE VARIANT TESTS", manifest_tests("manifest_hold.txt", "tb_anc_core_freeze_hold", args.filter)),
        ("TOP-LEVEL TESTS", top_tests(args.filter)),
    ]
    total = sum(len(r) for _, r in sections)
    passed = sum(ok for _, r in sections for _, ok, _ in r)

    os.makedirs(os.path.dirname(OUT_LOG), exist_ok=True)
    with open(OUT_LOG, "w") as f:
        f.write(f"Icarus Verilog Regression Summary ({time.strftime('%Y-%m-%d %H:%M:%S')})\n")
        f.write("=" * 80 + "\n")
        f.write(f"Total Tests : {total}\nPassed      : {passed}\nFailed      : {total - passed}\n")
        f.write(f"Simulator   : {version}\n")
        f.write("=" * 80 + "\n")
        for title, res in sections:
            f.write(f"\n{title}:\n")
            for name, ok, detail in res:
                f.write(f"{name:35s} | {'PASS' if ok else 'FAIL'} | {detail}\n")
    print("=" * 80)
    print(f"[Icarus] Regression Complete: {passed}/{total} Tests PASSED in {time.time() - t0:.1f}s")
    print(f"[Icarus] Summary exported to: {OUT_LOG}")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
