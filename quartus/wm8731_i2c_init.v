// =============================================================================
// wm8731_i2c_init.v: Autonomous I2C Initializer for Wolfson WM8731 Audio Codec
// Target Board    : Terasic DE2-115 (Cyclone IV E EP4CE115F29C7)
// System Clock    : 50 MHz
// I2C Clock       : ~40 kHz (generated via internal divider)
// =============================================================================

module wm8731_i2c_init (
    input  wire clk,         // 50 MHz system clock
    input  wire rst_n,       // Active-low synchronous reset
    output reg  i2c_sclk,    // I2C clock output to codec
    inout  wire i2c_sdat,    // I2C bidirectional open-drain data
    output reg  init_done,   // High when all 11 registers successfully configured
    output reg  init_error   // High if any transfer NACK received
);

    // -------------------------------------------------------------------------
    // Configuration Register ROM (WM8731: 7-bit register address, 9-bit data)
    // -------------------------------------------------------------------------
    localparam NUM_REGS = 11;
    reg [15:0] config_rom [0:NUM_REGS-1];

    initial begin
        // R15: Reset Codec
        config_rom[0]  = {7'h0F, 9'b0_0000_0000};
        // R6: Power Down Control (Power up all blocks: Line In, Mic, ADC, DAC, OSC, OUT)
        config_rom[1]  = {7'h06, 9'b0_0000_0000};
        // R0: Left Line In (Unmute, 0 dB default gain)
        config_rom[2]  = {7'h00, 9'b0_0001_0111};
        // R1: Right Line In (Unmute, 0 dB default gain)
        config_rom[3]  = {7'h01, 9'b0_0001_0111};
        // R2: Left Headphone Out (0 dB volume, zero-cross detect)
        config_rom[4]  = {7'h02, 9'b0_0111_1001};
        // R3: Right Headphone Out (0 dB volume, zero-cross detect)
        config_rom[5]  = {7'h03, 9'b0_0111_1001};
        // R4: Analogue Audio Path (DAC select, mic mute, bypass disable)
        config_rom[6]  = {7'h04, 9'b0_0001_0010};
        // R5: Digital Audio Path (De-emphasis off, HPF enable)
        config_rom[7]  = {7'h05, 9'b0_0000_0000};
        // R7: Digital Audio Format: I2S format, 16-bit, Master mode (codec drives BCLK/LRCK)
        config_rom[8]  = {7'h07, 9'b0_0100_0010};
        // R8: Sampling Rate Control: Normal mode, 256fs (48 kHz / 8 kHz)
        config_rom[9]  = {7'h08, 9'b0_0000_0000};
        // R9: Active Control: Activate digital core
        config_rom[10] = {7'h09, 9'b0_0000_0001};
    end

    // -------------------------------------------------------------------------
    // I2C Timing & Quarter-Clock State Machine
    // 50 MHz / 1250 = 40 kHz I2C clock (Quarter phase period = 312 cycles)
    // -------------------------------------------------------------------------
    localparam Q_PERIOD = 312;
    reg [9:0] clk_div;
    reg       q_pulse;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            clk_div <= 10'd0;
            q_pulse <= 1'b0;
        end else if (clk_div == Q_PERIOD - 1) begin
            clk_div <= 10'd0;
            q_pulse <= 1'b1;
        end else begin
            clk_div <= clk_div + 1'b1;
            q_pulse <= 1'b0;
        end
    end

    // -------------------------------------------------------------------------
    // Open-Drain SDAT Driver
    // -------------------------------------------------------------------------
    reg sdat_out;
    assign i2c_sdat = sdat_out ? 1'bz : 1'b0;

    // -------------------------------------------------------------------------
    // Sequence State Machine
    // Byte 1: Device Address (0x34: 7-bit 0x1A + Write bit 0)
    // Byte 2: Register Address [6:0] + Data[8]
    // Byte 3: Data [7:0]
    // -------------------------------------------------------------------------
    localparam S_IDLE    = 4'd0;
    localparam S_START   = 4'd1;
    localparam S_BYTE    = 4'd2;
    localparam S_ACK     = 4'd3;
    localparam S_STOP    = 4'd4;
    localparam S_NEXT    = 4'd5;
    localparam S_DONE    = 4'd6;

    reg [3:0]  state;
    reg [1:0]  phase;          // 0: SCL low, 1: SCL mid-low, 2: SCL high, 3: SCL mid-high
    reg [3:0]  reg_idx;
    reg [1:0]  byte_idx;       // 0: DevAddr, 1: RegAddr+D8, 2: Data[7:0]
    reg [2:0]  bit_idx;
    reg [7:0]  tx_byte;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state      <= S_IDLE;
            phase      <= 2'd0;
            reg_idx    <= 4'd0;
            byte_idx   <= 2'd0;
            bit_idx    <= 3'd7;
            tx_byte    <= 8'h00;
            sdat_out   <= 1'b1;
            i2c_sclk   <= 1'b1;
            init_done  <= 1'b0;
            init_error <= 1'b0;
        end else if (q_pulse) begin
            case (state)
                S_IDLE: begin
                    sdat_out <= 1'b1;
                    i2c_sclk <= 1'b1;
                    if (reg_idx < NUM_REGS) begin
                        state <= S_START;
                        phase <= 2'd0;
                    end else begin
                        init_done <= 1'b1;
                        state     <= S_DONE;
                    end
                end

                S_START: begin
                    // Generate I2C START: SDAT goes low while SCLK is high
                    case (phase)
                        2'd0: begin sdat_out <= 1'b1; i2c_sclk <= 1'b1; phase <= 2'd1; end
                        2'd1: begin sdat_out <= 1'b0; i2c_sclk <= 1'b1; phase <= 2'd2; end
                        2'd2: begin sdat_out <= 1'b0; i2c_sclk <= 1'b0; phase <= 2'd3; end
                        2'd3: begin
                            byte_idx <= 2'd0;
                            bit_idx  <= 3'd7;
                            tx_byte  <= 8'h34; // WM8731 I2C write address
                            state    <= S_BYTE;
                            phase    <= 2'd0;
                        end
                    endcase
                end

                S_BYTE: begin
                    // Send 8 data bits: SCLK low -> set data -> SCLK high -> SCLK low
                    case (phase)
                        2'd0: begin
                            sdat_out <= tx_byte[bit_idx];
                            i2c_sclk <= 1'b0;
                            phase    <= 2'd1;
                        end
                        2'd1: begin i2c_sclk <= 1'b1; phase <= 2'd2; end
                        2'd2: begin i2c_sclk <= 1'b1; phase <= 2'd3; end
                        2'd3: begin
                            i2c_sclk <= 1'b0;
                            phase    <= 2'd0;
                            if (bit_idx == 3'd0) begin
                                state <= S_ACK;
                            end else begin
                                bit_idx <= bit_idx - 1'b1;
                            end
                        end
                    endcase
                end

                S_ACK: begin
                    // Release SDAT for 9th clock cycle to sample slave ACK
                    case (phase)
                        2'd0: begin sdat_out <= 1'b1; i2c_sclk <= 1'b0; phase <= 2'd1; end
                        2'd1: begin
                            i2c_sclk <= 1'b1;
                            if (i2c_sdat == 1'b1) init_error <= 1'b1; // NACK
                            phase    <= 2'd2;
                        end
                        2'd2: begin i2c_sclk <= 1'b1; phase <= 2'd3; end
                        2'd3: begin
                            i2c_sclk <= 1'b0;
                            phase    <= 2'd0;
                            if (byte_idx == 2'd0) begin
                                byte_idx <= 2'd1;
                                bit_idx  <= 3'd7;
                                tx_byte  <= {config_rom[reg_idx][15:9], config_rom[reg_idx][8]};
                                state    <= S_BYTE;
                            end else if (byte_idx == 2'd1) begin
                                byte_idx <= 2'd2;
                                bit_idx  <= 3'd7;
                                tx_byte  <= config_rom[reg_idx][7:0];
                                state    <= S_BYTE;
                            end else begin
                                state <= S_STOP;
                            end
                        end
                    endcase
                end

                S_STOP: begin
                    // Generate I2C STOP: SDAT goes high while SCLK is high
                    case (phase)
                        2'd0: begin sdat_out <= 1'b0; i2c_sclk <= 1'b0; phase <= 2'd1; end
                        2'd1: begin sdat_out <= 1'b0; i2c_sclk <= 1'b1; phase <= 2'd2; end
                        2'd2: begin sdat_out <= 1'b1; i2c_sclk <= 1'b1; phase <= 2'd3; end
                        2'd3: begin
                            state   <= S_NEXT;
                            phase   <= 2'd0;
                        end
                    endcase
                end

                S_NEXT: begin
                    reg_idx <= reg_idx + 1'b1;
                    state   <= S_IDLE;
                end

                S_DONE: begin
                    sdat_out  <= 1'b1;
                    i2c_sclk  <= 1'b1;
                    init_done <= 1'b1;
                end
            endcase
        end
    end

endmodule
