"""
parse_wm8731_rom.py: Programmatic parser for WM8731 configuration ROM and clocking.
Parses quartus/wm8731_i2c_init.v and quartus/anc_de2_115_top.v to generate docs/wm8731_config.md.
"""

import re
import os

def parse_config_rom(init_v_path):
    with open(init_v_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Match lines like: config_rom[0]  = {7'h0F, 9'b0_0000_0000};
    pattern = re.compile(r"config_rom\[(\d+)\]\s*=\s*\{7'h([0-9A-Fa-f]+),\s*9'b([01_]+)\};")
    matches = pattern.findall(content)

    rom_entries = []
    reg_names = {
        0x00: ("R0", "Left Line In Control", "Unmute Left Line In; 0 dB default volume gain"),
        0x01: ("R1", "Right Line In Control", "Unmute Right Line In; 0 dB default volume gain"),
        0x02: ("R2", "Left Headphone Out", "0 dB volume; zero-cross detect disabled (bit 7 = 0)"),
        0x03: ("R3", "Right Headphone Out", "0 dB volume; zero-cross detect disabled (bit 7 = 0)"),
        0x04: ("R4", "Analogue Audio Path", "DAC select active, mic mute enabled, analogue bypass disabled"),
        0x05: ("R5", "Digital Audio Path", "De-emphasis filter off, ADC high-pass filter enabled"),
        0x06: ("R6", "Power Down Control", "Powers up all internal blocks (Line In, Mic, ADC, DAC, Oscillator, Output)"),
        0x07: ("R7", "Digital Audio Format", "I2S standard format, 16-bit word length, Master mode (codec drives BCLK/LRCK)"),
        0x08: ("R8", "Sampling Rate Control", "Normal mode, base oversampling 256 fs (XCK / fs = 256, fs = 48.828 kHz)"),
        0x09: ("R9", "Active Control", "Activate digital core audio interface (bit 0 = 1)"),
        0x0F: ("R15", "Reset Register", "Resets all registers to defaults. Settling delay requirement unverified")
    }

    for idx_str, addr_hex, bin_str in matches:
        idx = int(idx_str)
        addr = int(addr_hex, 16)
        clean_bin = bin_str.replace('_', '')
        data_val = int(clean_bin, 2)
        r_name, r_desc, r_notes = reg_names.get(addr, (f"R{addr}", "Unknown", "N/A"))
        rom_entries.append({
            "rom_idx": idx,
            "addr_hex": f"0x{addr:02X}",
            "data_hex": f"0x{data_val:03X}",
            "data_bin": bin_str,
            "name": r_name,
            "desc": r_desc,
            "notes": r_notes
        })

    return rom_entries

def parse_xck_clock(top_v_path):
    with open(top_v_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Look for assign AUD_XCK = ...
    m = re.search(r"assign\s+AUD_XCK\s*=\s*([^;]+);", content)
    xck_signal = m.group(1).strip() if m else "xck_cnt[1]"
    return xck_signal

def generate_markdown(rom_entries, xck_signal, output_md_path):
    lines = [
        "# WM8731 Codec Configuration & Clocking Specification",
        "",
        "## 1. Clocking Architecture & Sampling Rates",
        "",
        "- **Master Clock (`AUD_XCK`):**",
        f"  - Generated on Cyclone IV FPGA by dividing `CLOCK_50` (50.000 MHz) by 4 using a synchronous 2-bit counter (`{xck_signal}`).",
        "  - Nominal Frequency: **12.500 MHz** (Period = 80.0 ns).",
        "- **Audio Clocks (WM8731 Master Mode):**",
        r"  - **BCLK (Bit Clock):** Derived as $\text{AUD\_XCK} / 4 = \mathbf{3.125\ \text{MHz}}$ (Period = 320.0 ns, 16 `CLOCK_50` cycles).",
        r"  - **LRCK (Left/Right Sample Clock / $f_s$):** Derived as $\text{BCLK} / 64 = \mathbf{48.828125\ \text{kHz}}$ (Period = 20.480 $\mu$s, 1024 `CLOCK_50` cycles).",
        r"  - **Oversampling Ratio:** $XCK / f_s = 12.5\ \text{MHz} / 48.828125\ \text{kHz} = \mathbf{256\ f_s}$.",
        "",
        "## 2. I2C Control Protocol",
        "",
        "- **I2C Clock (`i2c_sclk`):** 50.000 MHz / 1250 = **40.0 kHz** (Quarter-phase state duration = 312 clock cycles).",
        "- **I2C Device Address Byte:** `8'h34` (`{7'b0011010, 1'b0}`: WM8731 7-bit address 0x1A with R/W# = 0).",
        "- **3-Byte Transmission Format:**",
        "  1. **Byte 1:** `8'h34` (Device Address + Write).",
        "  2. **Byte 2:** `{reg_addr[6:0], data[8]}` (7-bit register address + MSB of 9-bit data).",
        "  3. **Byte 3:** `data[7:0]` (Lower 8 bits of 9-bit data).",
        "",
        "## 3. Register Configuration Table (Auto-Generated from config_rom)",
        "",
        "> [!NOTE]",
        "> The official Wolfson WM8731 datasheet is inaccessible in this environment. As required by engineering governance, all register settings, bitfields, and post-reset settling delay requirements are classified as **UNVERIFIED**.",
        "",
        "| Register | Address | Value (9-bit Hex) | Field Meanings as Coded | Status | Datasheet Page | Notes & Top-Level Context |",
        "| :--- | :---: | :---: | :--- | :---: | :---: | :--- |"
    ]

    for r in rom_entries:
        lines.append(f"| **{r['name']}** | `{r['addr_hex']}` | `{r['data_hex']}` | {r['desc']} | **UNVERIFIED** | UNVERIFIED | {r['notes']} |")

    lines.extend([
        "",
        "---",
        "",
        "## 4. Top-Level Freeze Timing & Pipeline Latency",
        "",
        "- **Frame Latency:**",
        "  In hardware, frame $f$ ADC audio data is shifted serially over 64 BCLK periods. At the end of frame $f$, `i2s_transceiver` pulses `sample_strobe` in the 50 MHz domain.",
        "- **Freeze Application:**",
        "  The adaptation freeze switch `SW[1]` is synchronized through a 2-flop 50 MHz synchronizer and routed directly to `dut.u_anc_core.freeze`. When `anc_core` accepts sample $f$ at the beginning of frame $f+1$, it samples `freeze_r <= freeze`. Therefore, the freeze decision for sample $f$ is applied during frame $f+1$.",
        ""
    ])

    content = "\n".join(lines)
    with open(output_md_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Successfully generated {output_md_path} from config_rom ({len(rom_entries)} registers)")

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    init_v = os.path.join(base_dir, 'quartus', 'wm8731_i2c_init.v')
    top_v = os.path.join(base_dir, 'quartus', 'anc_de2_115_top.v')
    out_md = os.path.join(base_dir, 'docs', 'wm8731_config.md')

    rom = parse_config_rom(init_v)
    xck_sig = parse_xck_clock(top_v)
    generate_markdown(rom, xck_sig, out_md)
