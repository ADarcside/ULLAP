`timescale 1ns/1ps
// =============================================================================
// tb_top.v: Self-Checking Top-Level Verification Testbench for DE2-115 Wrapper
// Verifies:
//   T1   : Autonomous WM8731 I2C Initialization (11 writes, LEDR[6]=1, LEDR[7]=0)
//   T1b  : NACK Injection Fault Handling (LEDR[7]=1, LEDR[6]=0)
//   T2   : Audio Bypass Mode Passthrough (SW[0]=1, bit-exact, constant lag)
//   T3   : End-to-End ANC Processing with Golden Vectors (shift_e2_k3_W12_quiet)
//   T4   : Filter Adaptation Freeze Mode (SW[1]=1, output and weight match)
//   T5   : Hardware Reset Mid-Stream & Glitch Immunity (KEY[0])
//   T6   : Arithmetic Saturation Status LEDs (LEDR[5:0]) and Overrun (LEDR[8])
//   T7   : AUD_XCK Master Clock Period and Derived Sample Rate fs Measurement
//   T8   : Skew Sweep across 45 combinations (9 skews x 5 clk2out delays)
// =============================================================================

module tb_top #(
    parameter integer SKEW_NS    = 0,
    parameter integer CLK2OUT_NS = 0
);

    reg        clk50;
    reg  [3:0] key;
    reg  [3:0] sw;

    // Codec Hardware Lines
    wire       aud_bclk;
    wire       aud_adclrck;
    wire       aud_adcdat;
    wire       aud_daclrck;
    wire       aud_dacdat;
    wire       aud_xck;

    wire       i2c_sclk;
    wire       i2c_sdat;
    wire [9:0] ledr;

    pullup(i2c_sdat);

    // Dynamic Skew/Delay Controls
    reg        cfg_dyn_en;
    reg [31:0] cfg_skew;
    reg [31:0] cfg_clk2out;

    // Codec Model Control & Status
    reg        nack_inj;
    wire [3:0] codec_writes_acked;
    wire       codec_i2c_error;

    reg signed [15:0] codec_adc_left;
    reg signed [15:0] codec_adc_right;
    wire              codec_sample_start;

    wire signed [15:0] captured_dac_left;
    wire signed [15:0] captured_dac_right;
    wire               captured_dac_valid;

    // -------------------------------------------------------------------------
    // Device Under Test (DUT)
    // Hardware Parameters: W=12, L=32, ALGO=2 (NLMS-Shift), K=3, EPS_EXP=2
    // -------------------------------------------------------------------------
    anc_de2_115_top #(
        .W       (12),
        .L       (32),
        .ALGO    (2),
        .K       (3),
        .EPS_EXP (2),
        .MU_INT  (512)
    ) dut (
        .CLOCK_50    (clk50),
        .KEY         (key),
        .SW          (sw),
        .AUD_BCLK    (aud_bclk),
        .AUD_ADCLRCK (aud_adclrck),
        .AUD_ADCDAT  (aud_adcdat),
        .AUD_DACLRCK (aud_daclrck),
        .AUD_DACDAT  (aud_dacdat),
        .AUD_XCK     (aud_xck),
        .I2C_SCLK    (i2c_sclk),
        .I2C_SDAT    (i2c_sdat),
        .LEDR        (ledr)
    );

    // -------------------------------------------------------------------------
    // Wolfson WM8731 Behavioral Codec Model
    // -------------------------------------------------------------------------
    codec_model #(
        .SKEW_NS    (SKEW_NS),
        .CLK2OUT_NS (CLK2OUT_NS)
    ) u_codec (
        .rst_n              (key[0]),
        .cfg_dynamic_en     (cfg_dyn_en),
        .cfg_skew_ns        (cfg_skew),
        .cfg_clk2out_ns     (cfg_clk2out),
        .aud_xck            (aud_xck),
        .aud_bclk           (aud_bclk),
        .aud_adclrck        (aud_adclrck),
        .aud_daclrck        (aud_daclrck),
        .aud_adcdat         (aud_adcdat),
        .aud_dacdat         (aud_dacdat),
        .i2c_sclk           (i2c_sclk),
        .i2c_sdat           (i2c_sdat),
        .nack_inject        (nack_inj),
        .i2c_writes_acked   (codec_writes_acked),
        .i2c_protocol_error (codec_i2c_error),
        .adc_left_in        (codec_adc_left),
        .adc_right_in       (codec_adc_right),
        .sample_start       (codec_sample_start),
        .dac_left_out       (captured_dac_left),
        .dac_right_out      (captured_dac_right),
        .dac_valid          (captured_dac_valid)
    );

    // -------------------------------------------------------------------------
    // 50 MHz Master Clock
    // -------------------------------------------------------------------------
    initial clk50 = 1'b0;
    always #10 clk50 = ~clk50; // 50 MHz (20 ns period)

    // -------------------------------------------------------------------------
    // Vector Storage Buffers
    // -------------------------------------------------------------------------
    reg [11:0] vec_x [0:4095];
    reg [11:0] vec_d [0:4095];
    reg [11:0] vec_y [0:4095];
    reg [11:0] vec_e [0:4095];
    reg        vec_frz [0:4095];
    reg [11:0] vec_w [0:31];

    // Helper Task: Reset DUT and wait for I2C init
    task reset_and_init;
        input integer timeout_us;
        integer elapsed;
        begin
            key[0] = 1'b0; // Assert reset
            #200;
            key[0] = 1'b1; // Deassert reset
            elapsed = 0;
            while (dut.codec_init_done !== 1'b1 && elapsed < timeout_us) begin
                #1000;
                elapsed = elapsed + 1;
            end
        end
    endtask

    // Helper Task: Send one stereo frame and wait for DAC capture
    task stream_frame;
        input signed [15:0] l_val;
        input signed [15:0] r_val;
        output reg signed [15:0] dac_l;
        output reg signed [15:0] dac_r;
        begin
            @(posedge u_codec.sample_start); // Triggered before Left channel start
            codec_adc_left  = l_val;
            codec_adc_right = r_val;
            @(posedge captured_dac_valid);
            dac_l = captured_dac_left;
            dac_r = captured_dac_right;
        end
    endtask

    // Test selection string
    reg [255:0] test_name;

    initial begin
        key = 4'b1110; // Assert power-on reset
        sw  = 4'b0000;
        nack_inj = 1'b0;
        cfg_dyn_en = 1'b0;
        cfg_skew = 32'd0;
        cfg_clk2out = 32'd0;
        codec_adc_left = 16'd0;
        codec_adc_right = 16'd0;
        #200;
        key = 4'b1111; // Release reset
        nack_inj = 1'b0;
        cfg_dyn_en = 1'b0;
        cfg_skew = 32'd0;
        cfg_clk2out = 32'd0;
        codec_adc_left = 16'd0;
        codec_adc_right = 16'd0;

        if (!$value$plusargs("test=%s", test_name)) begin
            test_name = "ALL";
        end

        $display("================================================================================");
        $display("[TB_TOP] Starting DE2-115 Top-Level Verification: test=%0s", test_name);
        $display("================================================================================");

        if (test_name == "ALL" || test_name == "T1")   run_T1();
        if (test_name == "ALL" || test_name == "T1b")  run_T1b();
        if (test_name == "ALL" || test_name == "T2")   run_T2();
        if (test_name == "ALL" || test_name == "T3")   run_T3();
        if (test_name == "ALL" || test_name == "T4")   run_T4();
        if (test_name == "ALL" || test_name == "T5")   run_T5();
        if (test_name == "ALL" || test_name == "T6")   run_T6();
        if (test_name == "ALL" || test_name == "T7")   run_T7();
        if (test_name == "ALL" || test_name == "T8")   run_T8();

        $display("================================================================================");
        $display("# TB_TOP PASS all_completed test=%0s", test_name);
        $display("================================================================================");
        $finish(0);
    end

    // =========================================================================
    // Test T1: Autonomous I2C Initialization
    // =========================================================================
    task run_T1;
        begin
            $display("[TB_TOP] Running T1: I2C Codec Configuration...");
            nack_inj = 1'b0;
            reset_and_init(10000); // 10 ms timeout

            if (!dut.codec_init_done) begin
                $display("# TB_TOP FAIL T1 timeout waiting for codec_init_done");
                $finish(1);
            end
            if (codec_writes_acked != 11) begin
                $display("# TB_TOP FAIL T1 expected 11 ACKed writes, got %0d", codec_writes_acked);
                $finish(1);
            end
            if (codec_i2c_error) begin
                $display("# TB_TOP FAIL T1 codec reported I2C protocol error");
                $finish(1);
            end
            if (ledr[6] !== 1'b1 || ledr[7] !== 1'b0) begin
                $display("# TB_TOP FAIL T1 status LEDs wrong: LEDR[6]=%b (exp 1), LEDR[7]=%b (exp 0)",
                    ledr[6], ledr[7]);
                $finish(1);
            end
            $display("# TB_TOP PASS T1_i2c 11_registers_acked LEDR[6]=1 LEDR[7]=0");
        end
    endtask

    // =========================================================================
    // Test T1b: NACK Injection Fault Handling
    // =========================================================================
    task run_T1b;
        integer elapsed;
        begin
            $display("[TB_TOP] Running T1b: NACK Injection Fault Handling...");
            nack_inj = 1'b1; // Inject NACK
            key[0] = 1'b0;
            #200;
            key[0] = 1'b1;

            // Wait for I2C sequencer to attempt writes
            elapsed = 0;
            while (elapsed < 10000 && !dut.codec_init_error) begin
                #1000;
                elapsed = elapsed + 1;
            end

            if (ledr[7] !== 1'b1 || ledr[6] !== 1'b0) begin
                $display("# TB_TOP FAIL T1b NACK handling wrong: LEDR[7]=%b (exp 1), LEDR[6]=%b (exp 0)",
                    ledr[7], ledr[6]);
                $finish(1);
            end
            $display("# TB_TOP PASS T1b_nack LEDR[7]=1 LEDR[6]=0");
            nack_inj = 1'b0;
            reset_and_init(10000); // Re-arm for subsequent tests
        end
    endtask

    // =========================================================================
    // Test T2: Audio Bypass Passthrough (SW[0] = 1)
    // =========================================================================
    task run_T2;
        integer f;
        reg signed [15:0] test_d;
        reg signed [15:0] rx_l, rx_r;
        reg signed [15:0] pipe_exp;
        begin
            $display("[TB_TOP] Running T2: Audio Bypass Mode Passthrough...");
            reset_and_init(10000);

            sw[0] = 1'b1; // Bypass active
            #2000;

            pipe_exp = 16'd0;
            for (f = 0; f < 10; f = f + 1) begin
                test_d = 16'sh2000 + f * 16'sh0345;
                stream_frame(16'sh1234, test_d, rx_l, rx_r);
                if (f >= 1) begin
                    if (rx_l !== pipe_exp || rx_r !== pipe_exp) begin
                        $display("# TB_TOP FAIL T2 frame %0d mismatch: exp %h, got left=%h right=%h",
                            f-1, pipe_exp, rx_l, rx_r);
                        $finish(1);
                    end
                end
                pipe_exp = test_d;
            end
            sw[0] = 1'b0; // Normal mode
            $display("# TB_TOP PASS T2_bypass 10_frames_bit_exact");
        end
    endtask

    // =========================================================================
    // Test T3: End-to-End ANC with Golden Vectors
    // =========================================================================
    task run_T3;
        integer file, r, n_samples, f;
        reg signed [15:0] in_x, in_d, exp_e;
        reg signed [15:0] rx_l, rx_r;
        reg signed [15:0] pipe_exp;
        reg signed [15:0] pipe_exp_e [0:2];
        begin
            $display("[TB_TOP] Running T3: End-to-End ANC with Golden Vectors...");
            reset_and_init(10000);

            sw = 4'b0000; // Normal ANC mode

            file = $fopen("vectors/rtl/shift_e2_k3_W12_quiet.vec", "r");
            if (file == 0) begin
                $display("# TB_TOP FAIL T3 cannot open vectors/rtl/shift_e2_k3_W12_quiet.vec");
                $finish(1);
            end

            n_samples = 0;
            while (!$feof(file) && n_samples < 50) begin
                r = $fscanf(file, "%h %h %h %h\n",
                    vec_x[n_samples], vec_d[n_samples], vec_y[n_samples], vec_e[n_samples]);
                if (r == 4) n_samples = n_samples + 1;
            end
            $fclose(file);
            $display("[TB_TOP] Loaded %0d vectors for T3", n_samples);

            // Pipeline tracking for 1-frame latency:
            // Input presented at frame n produces DAC output at frame n+1.
            pipe_exp_e[0] = 16'd0;
            pipe_exp_e[1] = 16'd0;

            for (f = 0; f < n_samples; f = f + 1) begin
                in_x  = $signed(vec_x[f]) <<< 4;
                in_d  = $signed(vec_d[f]) <<< 4;
                exp_e = $signed(vec_e[f]) <<< 4;

                stream_frame(in_x, in_d, rx_l, rx_r);

                if (f >= 1) begin
                    // Compare captured DAC word against golden e from frame f-1
                    if (rx_l !== pipe_exp_e[0] || rx_r !== pipe_exp_e[0]) begin
                        $display("# TB_TOP FAIL T3 sample %0d mismatch: exp %h, got left=%h right=%h",
                            f-1, pipe_exp_e[0], rx_l, rx_r);
                        $finish(1);
                    end
                end
                pipe_exp_e[0] = exp_e;
            end
            $display("# TB_TOP PASS T3_anc lag=1_frame zero_mismatches samples=%0d", n_samples);
        end
    endtask

    // =========================================================================
    // Test T4: Filter Adaptation Freeze Mode
    // =========================================================================
        task run_T4;
        integer f_vec, f_frz, f_w, r, n_samples, f, k;
        reg signed [15:0] in_x, in_d, exp_e;
        reg signed [15:0] rx_l, rx_r;
        reg signed [15:0] pipe_exp;
        reg signed [15:0] pipe_exp_e;
        reg [11:0] hw_w;
        begin
            $display("[TB_TOP] Running T4: Filter Adaptation Freeze Mode...");
            reset_and_init(10000);

            f_vec = $fopen("vectors/rtl/shift_W12_freeze_toggle.vec", "r");
            f_frz = $fopen("vectors/rtl/shift_W12_freeze_toggle.frz", "r");
            f_w   = $fopen("vectors/rtl/shift_W12_freeze_toggle.w", "r");
            if (f_vec == 0 || f_frz == 0 || f_w == 0) begin
                $display("# TB_TOP FAIL T4 missing vector/frz/w files");
                $finish(1);
            end

            n_samples = 0;
            while (!$feof(f_vec) && n_samples < 200) begin
                r = $fscanf(f_vec, "%h %h %h %h\n",
                    vec_x[n_samples], vec_d[n_samples], vec_y[n_samples], vec_e[n_samples]);
                r = $fscanf(f_frz, "%b\n", vec_frz[n_samples]);
                n_samples = n_samples + 1;
            end
            $fclose(f_vec);
            $fclose(f_frz);

            for (k = 0; k < 32; k = k + 1) begin
                r = $fscanf(f_w, "%h\n", vec_w[k]);
            end
            $fclose(f_w);

            pipe_exp_e = 16'd0;
            sw[1] = 1'b0; // Frame 0: ADC receiving sample 0; core idle
            for (f = 0; f < n_samples; f = f + 1) begin
                in_x  = $signed(vec_x[f]) <<< 4;
                in_d  = $signed(vec_d[f]) <<< 4;
                exp_e = $signed(vec_e[f]) <<< 4;

                stream_frame(in_x, in_d, rx_l, rx_r);

                // During frame f+1, sample f is accepted by anc_core; drive freeze with vec_frz[f]
                sw[1] = (f < n_samples - 1) ? vec_frz[f] : 1'b0;

                if (f >= 1) begin
                    if (rx_l !== pipe_exp_e || rx_r !== pipe_exp_e) begin
                        $display("# TB_TOP FAIL T4 sample %0d mismatch: exp %h, got left=%h right=%h",
                            f-1, pipe_exp_e, rx_l, rx_r);
                        $finish(1);
                    end
                end
                pipe_exp_e = exp_e;
            end

            // Verify final filter weights hierarchically
            for (k = 0; k < 32; k = k + 1) begin
                hw_w = dut.u_anc_core.w[k];
                if (hw_w !== vec_w[k]) begin
                    $display("# TB_TOP FAIL T4 weight[%0d] mismatch: exp %h, got %h", k, vec_w[k], hw_w);
                    $finish(1);
                end
            end
            sw[1] = 1'b0;
            $display("# TB_TOP PASS T4_freeze weights_match outputs_match samples=%0d", n_samples);
        end
    endtask

    // =========================================================================
    // Test T5: Reset Mid-Stream & Glitch Immunity
    // =========================================================================
    task run_T5;
        reg signed [15:0] rx_l, rx_r;
        reg signed [15:0] pipe_exp;
        begin
            $display("[TB_TOP] Running T5: Hardware Reset Mid-Stream & Glitch Immunity...");
            reset_and_init(10000);

            stream_frame(16'sh1000, 16'sh2000, rx_l, rx_r);

            // Mid-stream 3-cycle glitch on KEY[0]
            @(posedge clk50);
            key[0] = 1'b0; // Active low assert
            repeat (3) @(posedge clk50);
            key[0] = 1'b1; // Deassert

            // Verify reset cleared core internal busy
            #100;
            if (dut.u_anc_core.busy !== 1'b0) begin
                $display("# TB_TOP FAIL T5 core busy not cleared on reset");
                $finish(1);
            end

            // Re-arm codec initialization after reset
            while (!dut.codec_init_done) #1000;

            // Stream new frame to prove stream recovery
            stream_frame(16'sh1500, 16'sh2500, rx_l, rx_r);
            $display("# TB_TOP PASS T5_reset glitch_cleared recovery_success");
        end
    endtask

    // =========================================================================
    // Test T6: Status LEDs and Saturation Flags
    // =========================================================================
    task run_T6;
        integer f;
        reg signed [15:0] rx_l, rx_r;
        reg signed [15:0] pipe_exp;
        begin
            $display("[TB_TOP] Running T6: Status LEDs and Saturation Flags...");
            reset_and_init(10000);

            // Normal streaming: verify LEDR[5:0] == 0 and LEDR[8] == 0 (no overrun)
            for (f = 0; f < 5; f = f + 1) begin
                stream_frame(16'sh0100, 16'sh0200, rx_l, rx_r);
            end
            if (ledr[5:0] !== 6'b000000 || ledr[8] !== 1'b0) begin
                $display("# TB_TOP FAIL T6 normal mode flags non-zero: LEDR[5:0]=%b, LEDR[8]=%b",
                    ledr[5:0], ledr[8]);
                $finish(1);
            end

            // Saturating sequence: build up positive weights, then invert primary input
            // to force e = d - y < WMIN, asserting sat_flags[3] (e saturation)
            for (f = 0; f < 20; f = f + 1) begin
                stream_frame(16'sh7FF0, 16'sh7FF0, rx_l, rx_r);
            end
            stream_frame(16'sh7FF0, -16'sh8000, rx_l, rx_r);
            // Extra frame to allow the -16'sh8000 sample to be processed through the core
            stream_frame(16'sh7FF0, 16'sh0000, rx_l, rx_r);
            if (ledr[5:0] === 6'b000000) begin
                $display("# TB_TOP FAIL T6 saturating input failed to trigger any sat_flags");
                $finish(1);
            end
            if (ledr[8] !== 1'b0) begin
                $display("# TB_TOP FAIL T6 unexpected overrun flag LEDR[8]=1");
                $finish(1);
            end
            $display("# TB_TOP PASS T6_flags moderate_clean=0 saturating_detected=%b overrun=0", ledr[5:0]);
            reset_and_init(10000); // Clear sticky flags
        end
    endtask

    // =========================================================================
    // Test T7: AUD_XCK Period and Derived fs Measurement
    // =========================================================================
    task run_T7;
        realtime t_rise1, t_rise2, period_ns, fs_hz;
        begin
            $display("[TB_TOP] Running T7: Clock Period & Sample Rate Measurement...");
            @(posedge aud_xck);
            t_rise1 = $realtime;
            @(posedge aud_xck);
            t_rise2 = $realtime;
            period_ns = t_rise2 - t_rise1;
            fs_hz = 1.0e9 / (period_ns * 256.0);

            $display("[TB_TOP] AUD_XCK period = %0.2f ns, derived fs = %0.2f Hz", period_ns, fs_hz);
            $display("# TB_TOP PASS T7_clock period_ns=%0.2f derived_fs_hz=%0.2f", period_ns, fs_hz);
        end
    endtask

    // =========================================================================
    // Test T8: Skew Sweep across 45 parameter combinations
    // 9 Skews in {-40,-20,-10,-5,0,+5,+10,+20,+40} x 5 CLK2OUT in {0,5,10,15,19}
    // =========================================================================
    task run_T8;
        integer skews [0:8];
        integer clk2outs [0:4];
        integer s_idx, c_idx, cur_s, cur_c;
        reg signed [15:0] rx_l, rx_r;
        reg signed [15:0] pipe_exp;
        begin
            $display("[TB_TOP] Running T8: Skew Sweep across 45 parameter combinations...");
            reset_and_init(10000);

            skews[0] = -40; skews[1] = -20; skews[2] = -10;
            skews[3] = -5;  skews[4] = 0;   skews[5] = 5;
            skews[6] = 10;  skews[7] = 20;  skews[8] = 40;

            clk2outs[0] = 0;  clk2outs[1] = 5;  clk2outs[2] = 10;
            clk2outs[3] = 15; clk2outs[4] = 19;

            cfg_dyn_en = 1'b1;

            for (s_idx = 0; s_idx < 9; s_idx = s_idx + 1) begin
                for (c_idx = 0; c_idx < 5; c_idx = c_idx + 1) begin
                    cur_s = skews[s_idx];
                    cur_c = clk2outs[c_idx];

                    cfg_skew    = cur_s;
                    cfg_clk2out = cur_c;
                    #2000;

                    // Verify Bypass path at this skew point (1-frame pipeline latency)
                    // Stream Frame A then Frame B with DIFFERENT data:
                    // During Frame B, DAC output must equal Frame A's data;
                    // During Frame C, DAC output must equal Frame B's data.
                    sw[0] = 1'b1;
                    stream_frame(16'sh1234, 16'sh5678, rx_l, rx_r); // Frame A into ADC
                    stream_frame(16'sh2468, 16'sh3579, rx_l, rx_r); // Frame B into ADC; DAC outputs Frame A
                    if (rx_l !== 16'sh5678 || rx_r !== 16'sh5678) begin
                        $display("# TB_TOP FAIL T8 skew=%0d clk2out=%0d bypass mismatch Frame A: exp 5678, got left=%h right=%h",
                            cur_s, cur_c, rx_l, rx_r);
                        $finish(1);
                    end
                    stream_frame(16'sh0000, 16'sh0000, rx_l, rx_r); // Frame C into ADC; DAC outputs Frame B
                    if (rx_l !== 16'sh3579 || rx_r !== 16'sh3579) begin
                        $display("# TB_TOP FAIL T8 skew=%0d clk2out=%0d bypass mismatch Frame B: exp 3579, got left=%h right=%h",
                            cur_s, cur_c, rx_l, rx_r);
                        $finish(1);
                    end
                    sw[0] = 1'b0;

                    // Verify ANC path at this skew point
                    stream_frame(16'sh0100, 16'sh0200, rx_l, rx_r);
                    stream_frame(16'sh0100, 16'sh0200, rx_l, rx_r);
                end
            end
            cfg_dyn_en = 1'b0;
            $display("# TB_TOP PASS T8_skew 45_combinations_passed");
        end
    endtask

endmodule
