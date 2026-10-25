# DE2-115 board test procedure (T1 to T11)

This is the bench procedure for the measured results the journal paper needs. Everything up to
the bench has been checked in simulation: `python py/run_iverilog_regression.py` (or the Questa
runner) must pass, including top-level tests T1 to T10, before programming the board.

## 1. Build the three bitstreams

The algorithm is a compile-time parameter, so each algorithm is its own `.sof`. Arguments are
`ALGO W K EPS_EXP MU_INT` (fair-tuned settings, `MU_INT = round(mu * 1024)`):

| Algorithm | Command (run in `quartus/`) | Setting |
|---|---|---|
| LMS | `quartus_sh -t build_quartus.tcl 0 12 3 2 256` | mu = 0.25 |
| NLMS | `quartus_sh -t build_quartus.tcl 1 12 3 0 256` | mu = 0.25, eps = 1 |
| NLMS-Shift | `quartus_sh -t build_quartus.tcl 2 12 3 2 512` | K = 3, eps = 0.25 |

After each build, copy the `.sof` to `anc_<algo>_W12_<commit>.sof`, record its SHA-256 and the
STA slack in a build manifest (as `quartus/BUILD_MANIFEST.md` does for NLMS-Shift), and check
the fitter report shows the four `GPIO` pins on PIN_AB22, PIN_AC15, PIN_AB21, PIN_Y17.

## 2. Bench set-up

| Item | Connection |
|---|---|
| USB-Blaster | DE2-115 USB port, programme with Quartus Programmer (JTAG) |
| Stimulus | PC or USB audio interface line output into the blue LINE IN jack. Left = reference x[n], right = primary d[n] |
| Recording | Green LINE OUT into the PC line input (16-bit, 48 kHz is fine) |
| GPIO voltage | Check jumper JP6 selects 3.3 V for the GPIO header before connecting the scope; the build drives GPIO[3:0] as 3.3-V LVTTL (I/O bank 4 at 3.3 V) |
| Scope (T10) | GPIO header JP5: pin 1 = in_valid, pin 2 = out_valid, pin 3 = busy, pin 4 = sample strobe, pin 12 or 30 = GND. 3.3 V logic |
| Switches | SW[0] = bypass (output = d[n]), SW[1] = freeze adaptation, KEY[0] = reset |
| LEDs | LEDR[5:0] sticky saturation flags, LEDR[6] codec configured, LEDR[7] I2C NACK, LEDR[8] overrun, LEDR[9] bypass |

Stimulus files: `python py/board_stimulus.py make --out board_evidence/stimulus --seconds 30`
writes `<scenario>_{noise,speech}_{8k,48k}.wav` for stationary, amp_steps, path_switch and wav.
Each file starts with 1 s of silence and a 0.5 s 1 kHz tone on both channels for level
calibration and alignment. Play the 48 kHz files from a PC (most sound cards do not run at
8 kHz); the signal reaches LINE IN as analogue audio and the codec's ADC, with its own
anti-alias filter, samples it at 8.138 kHz.

Level: with SW[0] = 1 (bypass) play the tone and adjust the PC output so the LINE OUT tone is
clean and no saturation LED lights; keep this level for all tests.

## 3. Tests

| Test | Procedure | Pass criterion | Evidence |
|---|---|---|---|
| T1 Boot | Programme, press KEY[0] | LEDR[6] on, LEDR[7] off, LEDR[5:0] and LEDR[8] off | Photo |
| T2 Bypass | SW[0] = 1, play `stationary_speech_48k.wav` | Clean right-channel signal in both output channels; left-only input gives silence | Recording `t2_bypass.wav` |
| T3 ANC | SW[0] = 0, same file | Noise fades within a few seconds, speech stays | Recording `t3_anc.wav` |
| T4 Freeze | Converge, then SW[1] = 1 for 10 s, then 0 | Cancellation holds while frozen; adaptation resumes when released | Recording with switch times noted |
| T5 Reset | KEY[0] five times during playback | LEDR[6] returns each time, cancellation restarts | Notes |
| T6 Overload | Raise the input level until clipping | No hang or sustained oscillation; flags may light and clear on reset | Photo of LEDs |
| T7 Sample rate | Scope on AUD_ADCLRCK (or GPIO pin 4) | 8.138 kHz (period 122.9 us) | Scope screenshot |
| T8 Soak | 10 minutes of `stationary_noise_48k.wav` in ANC | No dropouts, no return of noise, no new flags | Notes, LED photo |
| T9 Bit-exact | Signal Tap capture (section 4) after a reset | `py/check_board_capture.py` reports T9 PASS | Exported CSV + script output |
| T10 Timing | Scope GPIO pin 1 (in_valid) and pin 2 (out_valid) | Rising edges 38 cycles = 760 ns apart (core LAT 37 + 1 accept edge); busy (pin 3) high in between | Scope screenshot |
| T11 Board NR | For each scenario `*_noise_48k.wav`: record once with SW[0] = 1, once with SW[0] = 0 | Report `python py/board_stimulus.py analyze --bypass b.wav --anc a.wav --seconds 30` for each algorithm and scenario | Recordings + table |

T11 measures the end-to-end noise reduction including the codec's analogue path. Report it next
to the simulated nr_final for the same scenario; the difference is the board's contribution
(ADC/DAC noise floor, gain mismatch between channels, PC resampling).

## 4. Signal Tap set-up for T9

1. Tools > Signal Tap Logic Analyzer, new file `quartus/anc_t9.stp`, clock `CLOCK_50`.
2. Nodes: `x_reg[11..0]`, `d_reg[11..0]`, `anc_core:u_anc_core|e_out[11..0]`, `anc_core:u_anc_core|out_valid`.
3. Storage qualifier: Input port, `out_valid` = 1 (one row per processed sample). Sample depth 8K.
4. Trigger: `core_in_valid` rising, trigger position pre = 0 %, so the buffer starts at the first sample after reset.
5. Add the `.stp` to the project, recompile, programme. Arm the analyzer, press KEY[0] with SW[1] = 0
   and stimulus playing. When the buffer is full, File > Export > CSV.
6. `python py/check_board_capture.py --csv board_evidence/t9_<algo>.csv --algo <0|1|2>`.

Because capture starts from reset, the integer model starts from zero state and must match every
captured e[n]. Remove the `.stp` from the project for the final timing build (Signal Tap adds
logic and changes slack), and note this in the build manifest.

## 5. Record

Keep everything in `board_evidence/` (photos, recordings, CSV exports, scope screenshots and a
filled copy of the table above with PASS / FAIL and the date), and add the measured values to
`claims.md` as RAW only after the files are committed.
