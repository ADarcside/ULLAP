`timescale 1ns/1ps
// =============================================================================
// codec_model.v: Behavioral Model of Wolfson WM8731 Audio Codec
// Features:
//   1. I2C Slave: validates 11 configuration register writes vs expected ROM,
//      tracks START/STOP conditions, supports selectable NACK injection.
//   2. I2S Master: derives AUD_BCLK and AUD_LRCK from DUT AUD_XCK.
//      Configurable SKEW_NS (LRCK vs BCLK falling edge) and CLK2OUT_NS (vs XCK).
//      Supports both static module parameters and dynamic runtime updates.
//   3. DAC Capture: samples on BCLK rising edges, discards 1-cycle delay bit
//      after LRCK edge, captures 16 bits MSB-first into signed stereo words.
// =============================================================================

module codec_model #(
    parameter integer SKEW_NS    = 0,
    parameter integer CLK2OUT_NS = 0
) (
    input  wire        rst_n,

    // Dynamic Skew/Delay Configuration (Optional, defaults to parameters if dynamic_en=0)
    input  wire        cfg_dynamic_en,
    input  wire [31:0] cfg_skew_ns,
    input  wire [31:0] cfg_clk2out_ns,

    // Clock and Audio Lines from/to DUT
    input  wire        aud_xck,      // 12.5 MHz MCLK from FPGA top
    output wire        aud_bclk,     // 3.125 MHz BCLK to FPGA top
    output wire        aud_adclrck,  // 48.8 kHz ADC sample clock to FPGA
    output wire        aud_daclrck,  // 48.8 kHz DAC sample clock to FPGA
    output wire        aud_adcdat,   // ADC serial audio data to FPGA
    input  wire        aud_dacdat,   // DAC serial audio data from FPGA

    // I2C Configuration Bus
    input  wire        i2c_sclk,
    inout  wire        i2c_sdat,

    // Testbench Control and Status
    input  wire        nack_inject,
    output reg  [3:0]  i2c_writes_acked,
    output reg         i2c_protocol_error,

    // ADC Sample Feed (Driven by TB)
    input  wire signed [15:0] adc_left_in,
    input  wire signed [15:0] adc_right_in,
    output reg                sample_start,

    // DAC Capture Outputs (Observed by TB)
    output reg  signed [15:0] dac_left_out,
    output reg  signed [15:0] dac_right_out,
    output reg                dac_valid
);

    // =========================================================================
    // 1. I2C Slave Model
    // =========================================================================
    localparam NUM_EXPECTED_REGS = 11;
    reg [15:0] expected_rom [0:NUM_EXPECTED_REGS-1];
    initial begin
        expected_rom[0]  = {7'h0F, 9'b0_0000_0000}; // R15: Reset
        expected_rom[1]  = {7'h06, 9'b0_0000_0000}; // R6: Power Down
        expected_rom[2]  = {7'h00, 9'b0_0001_0111}; // R0: Left Line In
        expected_rom[3]  = {7'h01, 9'b0_0001_0111}; // R1: Right Line In
        expected_rom[4]  = {7'h02, 9'b0_0111_1001}; // R2: Left HP Out
        expected_rom[5]  = {7'h03, 9'b0_0111_1001}; // R3: Right HP Out
        expected_rom[6]  = {7'h04, 9'b0_0001_0010}; // R4: Analogue Path
        expected_rom[7]  = {7'h05, 9'b0_0000_0000}; // R5: Digital Path
        expected_rom[8]  = {7'h07, 9'b0_0100_0010}; // R7: Digital Audio Format
        expected_rom[9]  = {7'h08, 9'b0_0000_0000}; // R8: Sampling Rate
        expected_rom[10] = {7'h09, 9'b0_0000_0001}; // R9: Active
    end

    reg i2c_ack_drive;
    assign i2c_sdat = i2c_ack_drive ? 1'b0 : 1'bz;

    reg [7:0] i2c_shift;
    reg [3:0] i2c_bit_count;
    reg [1:0] i2c_byte_index;
    reg [7:0] rx_byte1, rx_byte2, rx_byte3;
    reg       i2c_bus_busy;

    initial begin
        i2c_writes_acked   = 4'd0;
        i2c_protocol_error = 1'b0;
        i2c_ack_drive      = 1'b0;
        i2c_bit_count      = 4'd0;
        i2c_byte_index     = 2'd0;
        i2c_bus_busy       = 1'b0;
    end

    // START condition detection: SDAT falling while SCLK is high
    always @(negedge i2c_sdat) begin
        if (i2c_sclk === 1'b1) begin
            i2c_bus_busy   <= 1'b1;
            i2c_bit_count  <= 4'd0;
            i2c_byte_index <= 2'd0;
        end
    end

    // STOP condition detection: SDAT rising while SCLK is high
    always @(posedge i2c_sdat) begin
        if (i2c_sclk === 1'b1 && i2c_bus_busy) begin
            i2c_bus_busy <= 1'b0;
            if (i2c_byte_index == 2'd3) begin
                // Check completed write
                if (rx_byte1 !== 8'h34) begin
                    i2c_protocol_error <= 1'b1;
                    $display("[CODEC_MODEL] ERROR: Expected I2C addr 0x34, got 0x%02h", rx_byte1);
                end
                if (i2c_writes_acked < NUM_EXPECTED_REGS) begin
                    if ({rx_byte2, rx_byte3} !== expected_rom[i2c_writes_acked]) begin
                        i2c_protocol_error <= 1'b1;
                        $display("[CODEC_MODEL] ERROR: Reg %0d mismatch: exp 0x%04h, got 0x%02h%02h",
                            i2c_writes_acked, expected_rom[i2c_writes_acked], rx_byte2, rx_byte3);
                    end else begin
                        if (!nack_inject)
                            i2c_writes_acked <= i2c_writes_acked + 1'b1;
                    end
                end
            end
        end
    end

    // Byte reception on SCLK posedges
    always @(posedge i2c_sclk) begin
        if (i2c_bus_busy) begin
            if (i2c_bit_count < 4'd8) begin
                i2c_shift <= {i2c_shift[6:0], i2c_sdat};
            end
            i2c_bit_count <= i2c_bit_count + 1'b1;
        end
    end

    // ACK drive on SCLK negedges
    always @(negedge i2c_sclk) begin
        if (i2c_bus_busy) begin
            if (i2c_bit_count == 4'd8) begin
                // 8 data bits received; store byte and assert ACK for 9th clock
                if (i2c_byte_index == 2'd0) rx_byte1 <= i2c_shift;
                else if (i2c_byte_index == 2'd1) rx_byte2 <= i2c_shift;
                else if (i2c_byte_index == 2'd2) rx_byte3 <= i2c_shift;

                i2c_byte_index <= i2c_byte_index + 1'b1;

                if (!nack_inject) begin
                    i2c_ack_drive <= 1'b1;
                end else begin
                    i2c_ack_drive <= 1'b0; // Inject NACK
                end
            end else if (i2c_bit_count == 4'd9) begin
                // 9th clock (ACK) completed; release bus and reset bit counter
                i2c_ack_drive <= 1'b0;
                i2c_bit_count <= 4'd0;
            end else begin
                i2c_ack_drive <= 1'b0;
            end
        end else begin
            i2c_ack_drive <= 1'b0;
        end
    end

    // =========================================================================
    // 2. I2S Master Clock & Transceiver Model
    // BASE_DLY = 100 ns guarantees all transport delays > 0
    // =========================================================================
    localparam BASE_DLY = 100;

    reg [1:0] xck_div;
    reg       int_bclk;
    reg [5:0] bclk_frame_cnt;
    reg       int_lrck;
    reg       int_adcdat;

    initial begin
        xck_div        = 2'b00;
        int_bclk       = 1'b0;
        bclk_frame_cnt = 6'd0;
        int_lrck       = 1'b0;
        int_adcdat     = 1'b0;
    end

    // 12.5 MHz XCK / 4 = 3.125 MHz BCLK
    always @(posedge aud_xck or negedge rst_n) begin
        if (!rst_n) begin
            xck_div  <= 2'b00;
            int_bclk <= 1'b0;
        end else begin
            xck_div <= xck_div + 1'b1;
            if (xck_div == 2'b01) int_bclk <= 1'b1;
            else if (xck_div == 2'b11) int_bclk <= 1'b0;
        end
    end

    // Frame counter: 64 BCLK cycles (32 Left, 32 Right)
    reg [4:0]  adc_bit_cnt;
    reg [15:0] adc_shift;

    always @(negedge int_bclk or negedge rst_n) begin
        if (!rst_n) begin
            bclk_frame_cnt <= 6'd0;
            int_lrck       <= 1'b0;
            adc_bit_cnt    <= 5'd0;
            adc_shift      <= 16'd0;
            int_adcdat     <= 1'b0;
        end else begin
            bclk_frame_cnt <= bclk_frame_cnt + 1'b1;

            if (bclk_frame_cnt == 6'd31) begin
                int_lrck    <= 1'b1; // Switch to Right Channel
                adc_bit_cnt <= 5'd0;
                int_adcdat  <= 1'b0; // 1-cycle delay bit
                adc_shift   <= adc_right_in;
            end else if (bclk_frame_cnt == 6'd63) begin
                int_lrck       <= 1'b0; // Switch to Left Channel
                bclk_frame_cnt <= 6'd0;
                adc_bit_cnt    <= 5'd0;
                int_adcdat     <= 1'b0; // 1-cycle delay bit
                adc_shift      <= adc_left_in;
            end else begin
                if (adc_bit_cnt < 5'd16) begin
                    int_adcdat  <= adc_shift[15];
                    adc_shift   <= {adc_shift[14:0], 1'b0};
                    adc_bit_cnt <= adc_bit_cnt + 1'b1;
                end else begin
                    int_adcdat <= 1'b0;
                end
            end
        end
    end

    // Strobe sample_start 2 BCLKs before Left channel start to allow clean setup time
    always @(negedge int_bclk or negedge rst_n) begin
        if (!rst_n) begin
            sample_start <= 1'b0;
        end else begin
            if (bclk_frame_cnt == 6'd61) begin
                sample_start <= 1'b1;
            end else begin
                sample_start <= 1'b0;
            end
        end
    end

    // Dynamic vs Static Delay Resolution
    integer cur_skew;
    integer cur_clk2out;
    always @(*) begin
        cur_skew    = (cfg_dynamic_en === 1'b1) ? $signed(cfg_skew_ns) : SKEW_NS;
        cur_clk2out = (cfg_dynamic_en === 1'b1) ? $signed(cfg_clk2out_ns) : CLK2OUT_NS;
    end

    reg r_aud_bclk;
    reg r_aud_adclrck;
    reg r_aud_daclrck;
    reg r_aud_adcdat;

    initial begin
        r_aud_bclk    = 1'b0;
        r_aud_adclrck = 1'b0;
        r_aud_daclrck = 1'b0;
        r_aud_adcdat  = 1'b0;
    end

    always @(int_bclk) begin
        #(BASE_DLY + cur_clk2out) r_aud_bclk = int_bclk;
    end

    always @(int_lrck) begin
        #(BASE_DLY + cur_clk2out + cur_skew) begin
            r_aud_adclrck = int_lrck;
            r_aud_daclrck = int_lrck;
        end
    end

    always @(int_adcdat) begin
        #(BASE_DLY + cur_clk2out) r_aud_adcdat = int_adcdat;
    end

    assign aud_bclk    = r_aud_bclk;
    assign aud_adclrck = r_aud_adclrck;
    assign aud_daclrck = r_aud_daclrck;
    assign aud_adcdat  = r_aud_adcdat;

    // =========================================================================
    // 3. DAC Capture
    // Sample on BCLK rising edges, discard first bit after LRCK edge,
    // take 16 bits MSB-first.
    // =========================================================================
    reg [4:0]  dac_bit_cnt;
    reg [15:0] dac_shift;
    reg        dac_capturing;
    reg        dac_curr_ch;
    reg        prev_daclrck;

    always @(posedge aud_bclk or negedge rst_n) begin
        if (!rst_n) begin
            dac_bit_cnt   <= 5'd0;
            dac_shift     <= 16'd0;
            dac_capturing <= 1'b0;
            dac_curr_ch   <= 1'b0;
            prev_daclrck  <= 1'b0;
            dac_left_out  <= 16'd0;
            dac_right_out <= 16'd0;
            dac_valid     <= 1'b0;
        end else begin
            dac_valid    <= 1'b0;
            prev_daclrck <= aud_daclrck;

            if (aud_daclrck != prev_daclrck) begin
                // First BCLK rising edge after LRCK edge: discard delay bit
                dac_bit_cnt   <= 5'd0;
                dac_shift     <= 16'd0;
                dac_capturing <= 1'b1;
                dac_curr_ch   <= aud_daclrck; // 0: Left, 1: Right
            end else if (dac_capturing) begin
                // Next 16 BCLK rising edges: sample data bits MSB first
                dac_shift   <= {dac_shift[14:0], aud_dacdat};
                dac_bit_cnt <= dac_bit_cnt + 1'b1;

                if (dac_bit_cnt == 5'd15) begin
                    dac_capturing <= 1'b0;
                    if (dac_curr_ch == 1'b0) begin
                        dac_left_out <= {dac_shift[14:0], aud_dacdat};
                    end else begin
                        dac_right_out <= {dac_shift[14:0], aud_dacdat};
                        dac_valid     <= 1'b1; // Stereo pair complete
                    end
                end
            end
        end
    end

endmodule
