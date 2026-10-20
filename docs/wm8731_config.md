# WM8731 Codec Configuration & Clocking Specification

## 1. Clocking Architecture & Sampling Rates

- **Master Clock (`AUD_XCK`):**
  - Generated on Cyclone IV FPGA by dividing `CLOCK_50` (50.000 MHz) by 4 using a synchronous 2-bit counter (`xck_cnt[1]`).
  - Nominal Frequency: **12.500 MHz** (Period = 80.0 ns).
- **Audio Clocks (WM8731 Master Mode):**
  - **BCLK (Bit Clock):** Derived as $\text{AUD\_XCK} / 4 = \mathbf{3.125\ \text{MHz}}$ (Period = 320.0 ns, 16 `CLOCK_50` cycles).
  - **LRCK (Left/Right Sample Clock / $f_s$):** Derived as $\text{BCLK} / 64 = \mathbf{48.828125\ \text{kHz}}$ (Period = 20.480 $\mu$s, 1024 `CLOCK_50` cycles).
  - **Oversampling Ratio:** $XCK / f_s = 12.5\ \text{MHz} / 48.828125\ \text{kHz} = \mathbf{256\ f_s}$.

## 2. I2C Control Protocol

- **I2C Clock (`i2c_sclk`):** 50.000 MHz / 1250 = **40.0 kHz** (Quarter-phase state duration = 312 clock cycles).
- **I2C Device Address Byte:** `8'h34` (`{7'b0011010, 1'b0}`: WM8731 7-bit address 0x1A with R/W# = 0).
- **3-Byte Transmission Format:**
  1. **Byte 1:** `8'h34` (Device Address + Write).
  2. **Byte 2:** `{reg_addr[6:0], data[8]}` (7-bit register address + MSB of 9-bit data).
  3. **Byte 3:** `data[7:0]` (Lower 8 bits of 9-bit data).

## 3. Register Configuration Table

> [!NOTE]
> The official Wolfson WM8731 datasheet is inaccessible in this environment. As required by engineering governance, all register settings, bitfields, and post-reset settling delay requirements are classified as **UNVERIFIED**.

| Register | Address | Value (9-bit Hex) | Field Meanings as Coded | Status | Datasheet Page | Notes & Top-Level Context |
| :--- | :---: | :---: | :--- | :---: | :---: | :--- |
| **R15** | `0x0F` | `0x000` | Codec Software Reset | **UNVERIFIED** | UNVERIFIED | Resets all registers to defaults. Settling delay requirement unverified. |
| **R6**  | `0x06` | `0x000` | Power Down Control | **UNVERIFIED** | UNVERIFIED | Powers up all internal blocks (Line In, Mic, ADC, DAC, Oscillator, Output). |
| **R0**  | `0x00` | `0x017` | Left Line In Control | **UNVERIFIED** | UNVERIFIED | Unmute Left Line In; 0 dB default volume gain (`0b00010111`). |
| **R1**  | `0x01` | `0x017` | Right Line In Control | **UNVERIFIED** | UNVERIFIED | Unmute Right Line In; 0 dB default volume gain (`0b00010111`). |
| **R2**  | `0x02` | `0x079` | Left Headphone Out | **UNVERIFIED** | UNVERIFIED | 0 dB volume; zero-cross detect disabled (bit 7 = 0). |
| **R3**  | `0x03` | `0x079` | Right Headphone Out | **UNVERIFIED** | UNVERIFIED | 0 dB volume; zero-cross detect disabled (bit 7 = 0). |
| **R4**  | `0x04` | `0x012` | Analogue Audio Path | **UNVERIFIED** | UNVERIFIED | DAC select active, mic mute enabled, analogue bypass disabled. |
| **R5**  | `0x05` | `0x000` | Digital Audio Path | **UNVERIFIED** | UNVERIFIED | De-emphasis filter off, ADC high-pass filter enabled. |
| **R7**  | `0x07` | `0x042` | Digital Audio Format | **UNVERIFIED** | UNVERIFIED | I2S standard format, 16-bit word length, Master mode (codec drives BCLK/LRCK). |
| **R8**  | `0x08` | `0x000` | Sampling Rate Control | **UNVERIFIED** | UNVERIFIED | Normal mode, base oversampling 256 $f_s$ ($XCK / f_s = 256$, $f_s \approx 48.828\ \text{kHz}$). |
| **R9**  | `0x09` | `0x001` | Active Control | **UNVERIFIED** | UNVERIFIED | Activate digital core audio interface (`bit 0 = 1`). |

---

## 4. Top-Level Freeze Timing & Pipeline Latency

- **Frame Latency:**
  In hardware, frame $f$ ADC audio data is shifted serially over 64 BCLK periods. At the end of frame $f$, `i2s_transceiver` pulses `sample_strobe` in the 50 MHz domain.
- **Freeze Application:**
  The adaptation freeze switch `SW[1]` is synchronized through a 2-flop 50 MHz synchronizer and routed directly to `dut.u_anc_core.freeze`. When `anc_core` accepts sample $f$ at the beginning of frame $f+1$, it samples `freeze_r <= freeze`. Therefore, the freeze decision for sample $f$ is applied during frame $f+1$.
