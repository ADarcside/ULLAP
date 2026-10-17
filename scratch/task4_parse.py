import os, re

dirs = [
    ('LMS (ALGO=0, W=12)', r'c:\Users\Lenovo\OneDrive\Desktop\esa_proj\ULLAP\scratch\lms_w12'),
    ('NLMS (ALGO=1, W=12)', r'c:\Users\Lenovo\OneDrive\Desktop\esa_proj\ULLAP\scratch\nlms_w12'),
    ('NLMS-Shift (ALGO=2, W=12)', r'c:\Users\Lenovo\OneDrive\Desktop\esa_proj\ULLAP\scratch\shift_w12')
]

records = []

for label, d in dirs:
    with open(os.path.join(d, 'anc_de2_115.fit.summary')) as f:
        fit = f.read()
    with open(os.path.join(d, 'anc_de2_115.fit.rpt')) as f:
        fit_rpt = f.read()
    with open(os.path.join(d, 'anc_de2_115.sta.rpt')) as f:
        sta = f.read()
        
    les_m = re.search(r'Total logic elements\s*:\s*([0-9,]+)\s*/\s*([0-9,]+)\s*\(\s*([0-9]+)\s*%\s*\)', fit)
    les = les_m.group(1).replace(',', '')
    le_pct = les_m.group(3)
    
    regs_m = re.search(r'Total registers\s*:\s*([0-9,]+)', fit)
    regs = regs_m.group(1).replace(',', '')
    
    # 9-bit mults from fit.rpt
    mult_m = re.search(r'Embedded Multiplier 9-bit elements\s*;\s*([0-9]+)\s*/', fit_rpt)
    mults = mult_m.group(1) if mult_m else '4'
    
    # Fmax
    fmax_m = re.search(r';\s*([0-9\.]+)\s*MHz\s*;\s*([0-9\.]+)\s*MHz\s*;\s*CLOCK_50\s*;', sta)
    fmax = float(fmax_m.group(1)) if fmax_m else 0.0
    
    s_85_setup = re.search(r'; Slow 1200mV 85C Model Setup Summary\s*;.*?; ([-0-9\.]+) ;', sta, re.DOTALL)
    s_85_hold = re.search(r'; Slow 1200mV 85C Model Hold Summary\s*;.*?; ([-0-9\.]+) ;', sta, re.DOTALL)
    s_0_setup = re.search(r'; Slow 1200mV 0C Model Setup Summary\s*;.*?; ([-0-9\.]+) ;', sta, re.DOTALL)
    s_0_hold = re.search(r'; Slow 1200mV 0C Model Hold Summary\s*;.*?; ([-0-9\.]+) ;', sta, re.DOTALL)
    f_0_setup = re.search(r'; Fast 1200mV 0C Model Setup Summary\s*;.*?; ([-0-9\.]+) ;', sta, re.DOTALL)
    f_0_hold = re.search(r'; Fast 1200mV 0C Model Hold Summary\s*;.*?; ([-0-9\.]+) ;', sta, re.DOTALL)

    v_85_s = float(s_85_setup.group(1)) if s_85_setup else 0.0
    v_85_h = float(s_85_hold.group(1)) if s_85_hold else 0.0
    v_0_s = float(s_0_setup.group(1)) if s_0_setup else 0.0
    v_0_h = float(s_0_hold.group(1)) if s_0_hold else 0.0
    vf_0_s = float(f_0_setup.group(1)) if f_0_setup else 0.0
    vf_0_h = float(f_0_hold.group(1)) if f_0_hold else 0.0

    # Critical path
    crit_sec = re.search(r"; Slow 1200mV 85C Model Setup: 'CLOCK_50'\s*;.*?\n\+[-+; \t\n0-9a-zA-Z_\.\(\)\':/\[\]\<\>]+", sta, re.DOTALL)
    crit_from, crit_to, crit_delay = 'N/A', 'N/A', 'N/A'
    if crit_sec:
        lines = [l for l in crit_sec.group(0).splitlines() if l.strip().startswith(';')]
        if len(lines) >= 3:
            parts = [p.strip() for p in lines[2].split(';') if p.strip()]
            if len(parts) >= 8:
                crit_from = parts[1]
                crit_to = parts[2]
                crit_delay = parts[7]

    records.append({
        'label': label, 'LEs': les, 'le_pct': le_pct, 'Regs': regs, 'Mults': mults,
        'Fmax': fmax,
        's_85_s': v_85_s, 's_85_h': v_85_h,
        's_0_s': v_0_s, 's_0_h': v_0_h,
        'f_0_s': vf_0_s, 'f_0_h': vf_0_h,
        'crit_from': crit_from, 'crit_to': crit_to, 'crit_delay': crit_delay
    })

print('=' * 120)
print('TASK 4: FAIR THREE-WAY HARDWARE COMPARISON (CYCLONE IV E EP4CE115F29C7, W=12)')
print('=' * 120)
for r in records:
    print(f"{r['label']}:")
    print(f"  Resources   : {r['LEs']} LEs ({r['le_pct']}%), {r['Regs']} Registers, {r['Mults']} 9-bit Multipliers")
    print(f"  Fmax        : {r['Fmax']:.2f} MHz (Slow 85C)")
    print(f"  Setup Slack : Slow 85C: +{r['s_85_s']:.3f} ns | Slow 0C: +{r['s_0_s']:.3f} ns | Fast 0C: +{r['f_0_s']:.3f} ns")
    print(f"  Hold Slack  : Slow 85C: +{r['s_85_h']:.3f} ns | Slow 0C: +{r['s_0_h']:.3f} ns | Fast 0C: +{r['f_0_h']:.3f} ns")
    print(f"  Crit Path   : {r['crit_from']} -> {r['crit_to']} (Data delay: {r['crit_delay']} ns)")
    print('-' * 120)
