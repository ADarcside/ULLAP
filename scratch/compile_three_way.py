import os, sys, subprocess, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUARTUS_DIR = os.path.join(ROOT, "quartus")
QUARTUS_SH = r"C:\altera_lite\25.1std\quartus\bin64\quartus_sh.exe"

def compile_and_extract(algo, w, k, eps_exp, mu_int, name):
    print(f"\n{'='*80}")
    print(f"COMPILING {name}: ALGO={algo}, W={w}, K={k}, EPS_EXP={eps_exp}, MU_INT={mu_int}")
    print(f"{'='*80}")
    
    cmd = [
        QUARTUS_SH, "-t", "build_quartus.tcl",
        str(algo), str(w), str(k), str(eps_exp), str(mu_int)
    ]
    
    res = subprocess.run(cmd, cwd=QUARTUS_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if res.returncode != 0:
        print(f"ERROR: Quartus compilation failed with code {res.returncode}")
        print(res.stdout[-2000:])
        return None
    
    print("Compilation succeeded! Parsing reports...")
    
    # 1. Parse fit.summary
    fit_sum_path = os.path.join(QUARTUS_DIR, "anc_de2_115.fit.summary")
    with open(fit_sum_path, "r") as f:
        fit_text = f.read()
    
    les_m = re.search(r"Total logic elements\s*:\s*([0-9,]+)\s*/\s*([0-9,]+)\s*\(\s*([0-9]+)\s*%\s*\)", fit_text)
    les = les_m.group(1).replace(",", "") if les_m else "N/A"
    le_pct = les_m.group(3) if les_m else "N/A"
    
    regs_m = re.search(r"Total registers\s*:\s*([0-9,]+)", fit_text)
    regs = regs_m.group(1).replace(",", "") if regs_m else "N/A"
    
    mult_m = re.search(r"Embedded Multiplier 9-bit elements\s*:\s*([0-9,]+)\s*/\s*([0-9,]+)\s*\(\s*([0-9]+)\s*%\s*\)", fit_text)
    mults = mult_m.group(1).replace(",", "") if mult_m else "N/A"
    
    # 2. Parse sta.summary
    sta_sum_path = os.path.join(QUARTUS_DIR, "anc_de2_115.sta.summary")
    with open(sta_sum_path, "r") as f:
        sta_text = f.read()
        
    def get_slack(model, typ):
        p = rf"Type\s*:\s*{model}\s+{typ}\s+'CLOCK_50'\s*\nSlack\s*:\s*([-0-9\.]+)"
        m = re.search(p, sta_text)
        return float(m.group(1)) if m else None

    s_85_setup = get_slack("Slow 1200mV 85C Model", "Setup")
    s_85_hold  = get_slack("Slow 1200mV 85C Model", "Hold")
    s_0_setup  = get_slack("Slow 1200mV 0C Model", "Setup")
    s_0_hold   = get_slack("Slow 1200mV 0C Model", "Hold")
    f_0_setup  = get_slack("Fast 1200mV 0C Model", "Setup")
    f_0_hold   = get_slack("Fast 1200mV 0C Model", "Hold")
    
    # 3. Parse sta.rpt for Fmax and critical path
    sta_rpt_path = os.path.join(QUARTUS_DIR, "anc_de2_115.sta.rpt")
    with open(sta_rpt_path, "r") as f:
        sta_rpt = f.read()
        
    fmax_m = re.search(r";\s*([0-9\.]+)\s*MHz\s*;\s*50\.00\s*MHz\s*;\s*CLOCK_50\s*;", sta_rpt)
    fmax = float(fmax_m.group(1)) if fmax_m else None
    
    # Critical path in Slow 85C setup
    crit_m = re.search(r"From Node\s*;\s*([^;\n]+).*?To Node\s*;\s*([^;\n]+).*?Data Delay\s*;\s*([^;\n]+)", sta_rpt, re.DOTALL)
    crit_from = crit_m.group(1).strip() if crit_m else "N/A"
    crit_to = crit_m.group(2).strip() if crit_m else "N/A"
    crit_delay = crit_m.group(3).strip() if crit_m else "N/A"
    
    unc_clks = 0
    unc_in = 0
    unc_out = 0
    for line in sta_rpt.splitlines():
        if "Unconstrained Clocks" in line:
            parts = [p.strip() for p in line.split(";") if p.strip()]
            if len(parts) >= 2: unc_clks = parts[1]
        elif "Unconstrained Input Ports" in line and "Paths" not in line:
            parts = [p.strip() for p in line.split(";") if p.strip()]
            if len(parts) >= 2: unc_in = parts[1]
        elif "Unconstrained Output Ports" in line and "Paths" not in line:
            parts = [p.strip() for p in line.split(";") if p.strip()]
            if len(parts) >= 2: unc_out = parts[1]
            
    record = {
        "name": name, "algo": algo, "W": w, "K": k, "eps_exp": eps_exp, "mu_int": mu_int,
        "LEs": les, "LE_pct": le_pct, "Registers": regs, "Mult_9bit": mults,
        "Fmax": fmax,
        "slow_85_setup": s_85_setup, "slow_85_hold": s_85_hold,
        "slow_0_setup": s_0_setup, "slow_0_hold": s_0_hold,
        "fast_0_setup": f_0_setup, "fast_0_hold": f_0_hold,
        "crit_from": crit_from, "crit_to": crit_to, "crit_delay": crit_delay,
        "unc_clks": unc_clks, "unc_in": unc_in, "unc_out": unc_out
    }
    print(f"Extracted: {record}")
    return record

if __name__ == "__main__":
    import json
    configs = [
        (0, 12, 3, 2, 512, "LMS_W12"),
        (1, 12, 3, 2, 512, "NLMS_W12"),
        (2, 12, 3, 2, 512, "NLMS_Shift_W12"),
    ]
    results = []
    for c in configs:
        rec = compile_and_extract(*c)
        if rec:
            results.append(rec)
            
    with open(r"c:\Users\Lenovo\OneDrive\Desktop\esa_proj\ULLAP\scratch\task4_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nALL THREE COMPILATIONS COMPLETE!")
