import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK_DIR = os.path.join(ROOT, "build", "questa_work").replace("\\", "/")
VLOG = r"C:\altera_lite\25.1std\questa_fse\win64\vlog.exe"
VSIM = r"C:\altera_lite\25.1std\questa_fse\win64\vsim.exe"
LIC_PATH = r"C:\Users\Lenovo\questa_lic.dat"

env = os.environ.copy()
for v in ["LM_LICENSE_FILE", "MGLS_LICENSE_FILE", "SALT_LICENSE_SERVER"]:
    env[v] = LIC_PATH

print("[1/2] Compiling top wrapper and testbench...")
vlog_cmd = [
    VLOG, "-work", WORK_DIR,
    os.path.join(ROOT, "rtl", "anc_core.v"),
    os.path.join(ROOT, "quartus", "wm8731_i2c_init.v"),
    os.path.join(ROOT, "quartus", "i2s_transceiver.v"),
    os.path.join(ROOT, "quartus", "anc_de2_115_top.v"),
    os.path.join(ROOT, "quartus", "tb_anc_de2_115_top.v"),
]
p = subprocess.run(vlog_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
print(p.stdout)
if p.returncode != 0:
    print(p.stderr)
    sys.exit(1)

print("[2/2] Running tb_anc_de2_115_top simulation...")
vsim_cmd = [
    VSIM, "-c", "-work", WORK_DIR, "tb_anc_de2_115_top",
    "-do", "run -all; quit -f"
]
p2 = subprocess.run(vsim_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
print(p2.stdout)
if p2.returncode != 0:
    print(p2.stderr)
    sys.exit(1)

print("Top testbench finished with return code:", p2.returncode)
