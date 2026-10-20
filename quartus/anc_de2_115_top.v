// =============================================================================
// anc_de2_115_top.v: Complete Hardware Top-Level for Terasic DE2-115
// Target Device   : Altera/Intel Cyclone IV E EP4CE115F29C7
// Target Board    : Terasic DE2-115 Development Board
// Audio Codec     : Wolfson WM8731 (Line-In / Mic ADC -> Line-Out DAC)
// Architecture    : 50 MHz Synchronous System Clock Domain, Edge-Synced I2S,
//                   Autonomous I2C Initializer, Zero-Latency Bypass Path.
// =============================================================================

module anc_de2_115_top #(
    parameter integer W     = 12,    // Hardware word length (Q1.11 signed)
    parameter integer L     = 32,    // 32-tap adaptive filter
    parameter integer ALGO  = 2,     // 0: LMS, 1: NLMS, 2: NLMS-shift (Hardware Recommended)
    parameter integer K     = 3,     // Step size mu = 2^-3 = 0.125 (tuned with EPS_EXP)
    parameter integer EPS_EXP = 2,   // Regulariser eps = 2^-2 (Phase-1 sweep)
    parameter integer MU_INT = 512   // Step size for LMS/NLMS: round(mu * 1024)
) (
    input  wire        CLOCK_50,     // 50 MHz master oscillator (PIN_Y2)
    input  wire [3:0]  KEY,          // Pushbuttons (Active low): KEY[0] = Reset
    input  wire [3:0]  SW,           // Slide Switches: SW[0] = Bypass, SW[1] = Freeze

    // WM8731 Audio Codec Hardware Interface
    input  wire        AUD_BCLK,     // Audio Bit Clock from codec (PIN_F2)
    input  wire        AUD_ADCLRCK,  // ADC Sample Rate Clock from codec (PIN_C2)
    input  wire        AUD_ADCDAT,   // ADC Serial Data from codec (PIN_D2)
    input  wire        AUD_DACLRCK,  // DAC Sample Rate Clock from codec (PIN_E3)
    output wire        AUD_DACDAT,   // DAC Serial Data to codec (PIN_D1)
    output wire        AUD_XCK,      // Codec Master Clock from FPGA (PIN_E1)

    // I2C Configuration Bus
    output wire        I2C_SCLK,     // I2C Clock (PIN_B7)
    inout  wire        I2C_SDAT,     // I2C Data (PIN_A8)

    // Status / Diagnostic LEDs
    output wire [9:0]  LEDR          // Red LEDs for status/diagnostics
);

    wire rst_n = KEY[0];
    wire bypass_active = SW[0];      // 1: Direct audio passthrough (zero latency)
    wire freeze_active = SW[1];      // 1: Freeze filter adaptation

    // -------------------------------------------------------------------------
    // 1. WM8731 Master Clock (AUD_XCK): 50 MHz / 4 = 12.5 MHz
    // -------------------------------------------------------------------------
    reg [1:0] xck_cnt;
    always @(posedge CLOCK_50 or negedge rst_n) begin
        if (!rst_n)
            xck_cnt <= 2'b00;
        else
            xck_cnt <= xck_cnt + 1'b1;
    end
    assign AUD_XCK = xck_cnt[1];

    // -------------------------------------------------------------------------
    // 2. Autonomous I2C Codec Configuration Engine
    // -------------------------------------------------------------------------
    wire codec_init_done;
    wire codec_init_error;

    wm8731_i2c_init u_i2c_init (
        .clk        (CLOCK_50),
        .rst_n      (rst_n),
        .i2c_sclk   (I2C_SCLK),
        .i2c_sdat   (I2C_SDAT),
        .init_done  (codec_init_done),
        .init_error (codec_init_error)
    );

    // -------------------------------------------------------------------------
    // 3. I2S Audio Transceiver (Synchronous to CLOCK_50)
    // -------------------------------------------------------------------------
    wire signed [15:0] adc_left_raw;   // Left Channel ADC = Reference Noise x[n]
    wire signed [15:0] adc_right_raw;  // Right Channel ADC = Primary Input d[n] (Speech + Noise)
    wire               sample_strobe;

    reg  signed [15:0] dac_left_data;
    reg  signed [15:0] dac_right_data;

    i2s_transceiver #(
        .DATA_WIDTH(16)
    ) u_i2s_codec (
        .clk          (CLOCK_50),
        .rst_n        (rst_n),
        .aud_bclk     (AUD_BCLK),
        .aud_adclrck  (AUD_ADCLRCK),
        .aud_adcdat   (AUD_ADCDAT),
        .aud_daclrck  (AUD_DACLRCK),
        .aud_dacdat   (AUD_DACDAT),
        .adc_left     (adc_left_raw),
        .adc_right    (adc_right_raw),
        .sample_valid (sample_strobe),
        .dac_left     (dac_left_data),
        .dac_right    (dac_right_data)
    );

    // -------------------------------------------------------------------------
    // 4. Sample Formatting & ANC Core Handshake
    // -------------------------------------------------------------------------
    // Scale 16-bit incoming samples to signed W-bit format (top W bits)
    wire signed [W-1:0] x_core_in = adc_left_raw[15 -: W];
    wire signed [W-1:0] d_core_in = adc_right_raw[15 -: W];

    reg  signed [W-1:0] x_reg;
    reg  signed [W-1:0] d_reg;
    reg                 core_in_valid;
    wire signed [W-1:0] y_out;
    wire signed [W-1:0] e_out;
    wire                anc_out_valid;
    wire [5:0]          anc_sat_flags;
    wire                anc_busy;
    reg                 overrun_flag;

    always @(posedge CLOCK_50 or negedge rst_n) begin
        if (!rst_n) begin
            x_reg         <= {W{1'b0}};
            d_reg         <= {W{1'b0}};
            core_in_valid <= 1'b0;
            overrun_flag  <= 1'b0;
        end else begin
            core_in_valid <= 1'b0; // default 1-cycle strobe

            if (sample_strobe && codec_init_done && !freeze_active) begin
                if (anc_busy) begin
                    overrun_flag <= 1'b1; // Sample arrived while core was busy
                end else begin
                    x_reg         <= x_core_in;
                    d_reg         <= d_core_in;
                    core_in_valid <= 1'b1;
                end
            end
        end
    end

    // -------------------------------------------------------------------------
    // 5. Portable Adaptive Noise Cancellation Core Instance
    // -------------------------------------------------------------------------
    anc_core #(
        .W       (W),
        .L       (L),
        .ALGO    (ALGO),
        .MU_INT  (MU_INT),
        .K       (K),
        .EPS_EXP (EPS_EXP)
    ) u_anc_core (
        .clk       (CLOCK_50),
        .rst_n     (rst_n),
        .in_valid  (core_in_valid),
        .freeze    (1'b0),
        .x_in      (x_reg),
        .d_in      (d_reg),
        .out_valid (anc_out_valid),
        .y_out     (y_out),
        .e_out     (e_out),
        .sat_flags (anc_sat_flags),
        .busy      (anc_busy)
    );

    // -------------------------------------------------------------------------
    // 6. Audio Output Selection & Zero-Latency Bypass Logic
    // -------------------------------------------------------------------------
    // Convert W-bit e_out back to 16-bit signed DAC format
    localparam PAD_BITS = 16 - W;
    wire signed [15:0] dac_anc_out = {e_out, {PAD_BITS{1'b0}}};
    reg  signed [15:0] anc_out_latched;

    always @(posedge CLOCK_50 or negedge rst_n) begin
        if (!rst_n) begin
            anc_out_latched <= 16'd0;
        end else if (anc_out_valid) begin
            anc_out_latched <= dac_anc_out;
        end
    end

    // Audio Mux: Bypass transmits raw primary input d[n] with ZERO filter delay
    always @(*) begin
        if (bypass_active) begin
            dac_left_data  = adc_right_raw; // Passthrough raw primary speech+noise
            dac_right_data = adc_right_raw;
        end else begin
            dac_left_data  = anc_out_latched; // Cancelled residual output e[n]
            dac_right_data = anc_out_latched;
        end
    end

    // -------------------------------------------------------------------------
    // 7. Status LEDs
    // -------------------------------------------------------------------------
    assign LEDR[5:0] = anc_sat_flags;   // Sticky arithmetic saturation flags {w,g,e,y,acc,in}
    assign LEDR[6]   = codec_init_done; // Green/ON when codec I2C init succeeds
    assign LEDR[7]   = codec_init_error;// ON if I2C NACK occurs
    assign LEDR[8]   = overrun_flag;    // ON if audio frame lost
    assign LEDR[9]   = bypass_active;   // ON when bypass switch SW[0] is active

endmodule
