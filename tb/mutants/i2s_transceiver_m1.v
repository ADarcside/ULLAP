// =============================================================================
// i2s_transceiver.v: Edge-Synchronized I2S Receiver/Transmitter for WM8731
// Target Board     : Terasic DE2-115 (Cyclone IV E EP4CE115F29C7)
// System Clock     : 50 MHz (All internal logic synchronous to 50 MHz clock)
// CDC Protection   : 2-stage synchronizers with level/edge tracking on BCLK/LRCK
// =============================================================================

module i2s_transceiver #(
    parameter integer DATA_WIDTH = 16
) (
    input  wire                  clk,            // 50 MHz master clock
    input  wire                  rst_n,          // Active-low synchronous reset

    // Physical WM8731 Hardware Pins
    input  wire                  aud_bclk,       // Bit clock from codec (Master)
    input  wire                  aud_adclrck,    // ADC sample rate clock from codec
    input  wire                  aud_adcdat,     // ADC serial audio input from codec
    input  wire                  aud_daclrck,    // DAC sample rate clock from codec
    output reg                   aud_dacdat,     // DAC serial audio output to codec

    // Parallel Sample Interface to FPGA ANC Core
    output reg  signed [15:0]    adc_left,       // Left channel ADC sample (Noise Reference x)
    output reg  signed [15:0]    adc_right,      // Right channel ADC sample (Primary Input d)
    output reg                   sample_valid,   // 1-cycle strobe when both channels ready

    input  wire signed [15:0]    dac_left,       // Left channel DAC data (Residual e or bypass)
    input  wire signed [15:0]    dac_right       // Right channel DAC data
);

    // -------------------------------------------------------------------------
    // 2-Stage CDC Synchronizers on 50 MHz Clock
    // -------------------------------------------------------------------------
    reg [2:0] bclk_sync;
    reg [2:0] adclrck_sync;
    reg [2:0] daclrck_sync;
    reg [1:0] adcdat_sync;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            bclk_sync     <= 3'b000;
            adclrck_sync  <= 3'b000;
            daclrck_sync  <= 3'b000;
            adcdat_sync   <= 2'b00;
        end else begin
            bclk_sync     <= {bclk_sync[1:0], aud_bclk};
            adclrck_sync  <= {adclrck_sync[1:0], aud_adclrck};
            daclrck_sync  <= {daclrck_sync[1:0], aud_daclrck};
            adcdat_sync   <= {adcdat_sync[0], aud_adcdat};
        end
    end

    wire bclk_rise = (bclk_sync[2:1] == 2'b01);
    wire bclk_fall = (bclk_sync[2:1] == 2'b10);

    wire adclrck_val = adclrck_sync[1]; // 0: Left, 1: Right
    wire daclrck_val = daclrck_sync[1];

    // -------------------------------------------------------------------------
    // I2S Receiver Logic (Standard I2S: 1-BCLK delay after LRCK transition)
    // -------------------------------------------------------------------------
    reg [4:0]  rx_bit_cnt;
    reg [15:0] rx_shift;
    reg        rx_channel; // 0: Left, 1: Right

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rx_bit_cnt   <= 5'd0;
            rx_shift     <= 16'd0;
            rx_channel   <= 1'b0;
            adc_left     <= 16'd0;
            adc_right    <= 16'd0;
            sample_valid <= 1'b0;
        end else begin
            sample_valid <= 1'b0; // default 1-cycle strobe

            if (bclk_rise) begin
                if (adclrck_val != rx_channel) begin
                    // LRCK level toggled: start new channel framing
                    rx_bit_cnt <= 5'd0;
                    rx_channel <= adclrck_val;
                end else begin
                    // Shift in data bits up to 16 bits
                    if (rx_bit_cnt < 5'd16) begin
                        rx_shift   <= {rx_shift[14:0], adcdat_sync[1]};
                        rx_bit_cnt <= rx_bit_cnt + 1'b1;

                        if (rx_bit_cnt == 5'd15) begin
                            if (rx_channel == 1'b0) begin
                                // Left channel complete (Reference noise x)
                                adc_left <= {rx_shift[14:0], adcdat_sync[1]};
                            end else begin
                                // Right channel complete (Primary input d) -> assert strobe
                                adc_right    <= {rx_shift[14:0], adcdat_sync[1]};
                                sample_valid <= 1'b1;
                            end
                        end
                    end
                end
            end
        end
    end

    // -------------------------------------------------------------------------
    // I2S Transmitter Logic (Transmits MSB on falling BCLK with 1-cycle delay)
    // -------------------------------------------------------------------------
    reg [4:0]  tx_bit_cnt;
    reg [15:0] tx_shift;
    reg        tx_channel;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            tx_bit_cnt <= 5'd0;
            tx_shift   <= 16'd0;
            tx_channel <= 1'b0;
            aud_dacdat <= 1'b0;
        end else begin
            if (bclk_fall) begin
                if (daclrck_val != tx_channel) begin
                    // New channel start: load parallel sample
                    tx_bit_cnt <= 5'd0;
                    tx_channel <= daclrck_val;
                    aud_dacdat <= 1'b0; // 1-cycle I2S initial delay bit
                    tx_shift   <= (daclrck_val == 1'b0) ? dac_left : dac_right;
                end else if (tx_bit_cnt < 5'd16) begin
                    // Shift out MSB first
                    aud_dacdat <= tx_shift[15];
                    tx_shift   <= {tx_shift[14:0], 1'b0};
                    tx_bit_cnt <= tx_bit_cnt + 1'b1;
                end else begin
                    aud_dacdat <= 1'b0;
                end
            end
        end
    end

endmodule
