"""Automated Questa Verification Runner for ANC FPGA Project.

Executes:
  1. Setting Questa / Siemens license environment (SALT_LICENSE_SERVER / LM_LICENSE_FILE)
  2. Compiling RTL and testbench into Questa simulation library
  3. Running all configurations from tb/manifest.txt with matching parameters and +vec
  4. Running protocol / corner-case testbench (tb_anc_protocol.v)
  5. Generating comprehensive regression report in results/metrics/
"""
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Defaults are the original Windows install paths; override with environment variables on another machine.
VLOG = os.environ.get("ANC_VLOG", r"C:\altera_lite\25.1std\questa_fse\win64\vlog.exe")
VSIM = os.environ.get("ANC_VSIM", r"C:\altera_lite\25.1std\questa_fse\win64\vsim.exe")
VLIB = os.environ.get("ANC_VLIB", r"C:\altera_lite\25.1std\questa_fse\win64\vlib.exe")
LIC_PATH = os.environ.get("ANC_QUESTA_LIC")          # explicit override (None if not supplied)
DEFAULT_LIC_PATH = r"C:\Users\Lenovo\questa_lic.dat"  # original development-PC default
LIC_VARS = ("SALT_LICENSE_SERVER", "LM_LICENSE_FILE", "MGLS_LICENSE_FILE")

WORK_DIR = os.path.join(ROOT, "build", "questa_work").replace("\\", "/")
OUT_LOG = os.path.join(ROOT, "results", "metrics", "questa_regression_summary.txt").replace("\\", "/")



def get_env():
    """Questa license environment.

    * ANC_QUESTA_LIC supplied explicitly  -> used for all three license variables.
    * otherwise, if any license variable is already set in the environment -> left untouched (working config kept).
    * otherwise the original default license file is used only if it exists; if not, nothing is set.
    """
    env = os.environ.copy()
    lic = LIC_PATH
    if not lic and not any(env.get(v) for v in LIC_VARS) and os.path.isfile(DEFAULT_LIC_PATH):
        lic = DEFAULT_LIC_PATH
    if lic:
        for v in LIC_VARS:
            env[v] = lic
    return env


def is_pass(rc, out, marker):
    """PASS only if the simulator exited with 0 AND printed an explicit '<marker> PASS' line and no '<marker> FAIL' line."""
    if rc != 0:
        return False
    lines = [l.strip().lstrip("#").strip() for l in out.splitlines()]
    has_pass = any(l.startswith(marker + " PASS") for l in lines)
    has_fail = any(l.startswith(marker + " FAIL") for l in lines)
    return has_pass and not has_fail


def run_cmd(cmd, cwd=ROOT):
    p = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       text=True, env=get_env())
    return p.returncode, p.stdout + p.stderr


def setup_library():
    missing = [t for t in (VLOG, VSIM, VLIB) if not os.path.isfile(t)]
    if missing:
        raise SystemExit("Questa tool(s) not found: " + ", ".join(missing)
                         + " (set ANC_VLOG / ANC_VSIM / ANC_VLIB to the correct paths)")
    os.makedirs(os.path.dirname(WORK_DIR), exist_ok=True)
    if not os.path.exists(WORK_DIR):
        rc, out = run_cmd([VLIB, WORK_DIR])
        if rc != 0:
            raise RuntimeError(f"vlib failed: {out}")
    # Compile RTL and testbenches
    rc, out = run_cmd([VLOG, "-work", WORK_DIR, "rtl/anc_core.v", "tb/tb_anc_core.v", "tb/tb_anc_protocol.v"])
    if rc != 0:
        raise RuntimeError(f"vlog failed: {out}")
    print("[Questa] RTL and testbenches compiled successfully.")


def run_manifest_tests(filter_str=""):
    manifest_path = os.path.join(ROOT, "tb", "manifest.txt")
    with open(manifest_path, "r", encoding="utf-8") as f:
        lines = [l.strip().split() for l in f if l.strip() and not l.startswith("#")]
    results = []

    print(f"[Questa] Running {len(lines)} manifest regression configurations...", flush=True)
    for item in lines:
        name, algo, W, L, MU_INT, K, ACC_W, prefix, nsamples = item[:9]
        EPS_EXP = item[9] if len(item) > 9 else "10"      # optional 10th manifest column
        if filter_str and filter_str not in name:
            continue

        cmd = [
            VSIM, "-c", "-work", WORK_DIR, "tb_anc_core",
            f"-gW={W}", f"-gL={L}", f"-gALGO={algo}", f"-gMU_INT={MU_INT}",
            f"-gK={K}", f"-gACC_W={ACC_W}", f"-gEPS_EXP={EPS_EXP}",
            f"+vec={prefix}",
            "-do", "run -all; quit -f"
        ]
        rc, out = run_cmd(cmd)
        passed = is_pass(rc, out, "TB_RESULT")
        res_line = [l for l in out.splitlines() if "TB_RESULT" in l]
        detail = res_line[-1] if res_line else ("FAIL (no result line)" if rc != 0 else "UNKNOWN")
        if rc != 0 and res_line:
            detail += f" [simulator exit code {rc}]"

        results.append({
            "name": name,
            "algo": algo,
            "W": W,
            "L": L,
            "passed": passed,
            "detail": detail
        })
        status_str = "PASS" if passed else "FAIL"
        print(f"  [{status_str}] {name:35s}: {detail}", flush=True)


    return results


def run_protocol_tests():
    print("[Questa] Running protocol corner-case tests...", flush=True)
    proto_configs = [
        (0, 11, 8, 512, 4, 25),
        (1, 11, 8, 51, 4, 25),
        (2, 11, 8, 512, 4, 25),
        (2, 11, 2, 512, 4, 23),
    ]
    results = []
    for algo, W, L, MU_INT, K, ACC_W in proto_configs:
        name = f"proto_algo{algo}_L{L}"
        cmd = [
            VSIM, "-c", "-work", WORK_DIR, "tb_anc_protocol",
            f"-gW={W}", f"-gL={L}", f"-gALGO={algo}", f"-gMU_INT={MU_INT}",
            f"-gK={K}", f"-gACC_W={ACC_W}",
            "-do", "run -all; quit -f"
        ]
        rc, out = run_cmd(cmd)
        passed = is_pass(rc, out, "TB_PROTO")
        res_line = [l for l in out.splitlines() if "TB_PROTO" in l]
        detail = res_line[-1] if res_line else "FAIL"
        results.append({"name": name, "passed": passed, "detail": detail})
        status_str = "PASS" if passed else "FAIL"
        print(f"  [{status_str}] {name:35s}: {detail}", flush=True)
    return results



def main():
    t_start = time.time()
    setup_library()
    manifest_results = run_manifest_tests()
    proto_results = run_protocol_tests()

    total = len(manifest_results) + len(proto_results)
    passed = sum(1 for r in manifest_results if r["passed"]) + sum(1 for r in proto_results if r["passed"])

    os.makedirs(os.path.dirname(OUT_LOG), exist_ok=True)
    with open(OUT_LOG, "w") as f:
        f.write(f"Questa Verification Regression Summary ({time.strftime('%Y-%m-%d %H:%M:%S')})\n")
        f.write("=" * 80 + "\n")
        f.write(f"Total Tests : {total}\n")
        f.write(f"Passed      : {passed}\n")
        f.write(f"Failed      : {total - passed}\n")
        f.write(f"Simulator   : Questa Altera Starter FPGA Edition-64 2025.2\n")
        f.write("=" * 80 + "\n\n")
        f.write("MANIFEST TESTS:\n")
        for r in manifest_results:
            f.write(f"{r['name']:35s} | {'PASS' if r['passed'] else 'FAIL'} | {r['detail']}\n")
        f.write("\nPROTOCOL TESTS:\n")
        for r in proto_results:
            f.write(f"{r['name']:35s} | {'PASS' if r['passed'] else 'FAIL'} | {r['detail']}\n")

    print("=" * 80)
    print(f"[Questa] Regression Complete: {passed}/{total} Tests PASSED in {time.time() - t_start:.1f}s")
    print(f"[Questa] Summary exported to: {OUT_LOG}")
    print("=" * 80)
    return 0 if passed == total and total > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
