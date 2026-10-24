`timescale 1ns/1ps
// -----------------------------------------------------------------------------
// tb_power.v: activity testbench for anc_core (switching-activity / power flow).
//
// Streams the x/d columns of a golden vector file at the board sample rate
// (one in_valid every GAP clock cycles: 6144 = 50 MHz / 8.138 kHz) and dumps a VCD
// of the core for Quartus Power Analyzer (gate-level netlist sim) or for the
// RTL toggle-count proxy in py/power_activity.py.
//
//   +vec=<prefix>   reads <prefix>.vec (x d y e, hex); only x and d are used
//   +vcd=<file>     VCD output file (default tb_power.vcd)
//   +n=<N>          samples to stream (default 2000)
// No checking is done here; bit-exactness is covered by tb_anc_core.
// -----------------------------------------------------------------------------
module tb_power;
    parameter integer W       = 12;
    parameter integer L       = 32;
    parameter integer ALGO    = 2;
    parameter integer MU_INT  = 512;
    parameter integer K       = 3;
    parameter integer ACC_W   = 2*W + $clog2(L);
    parameter integer EPS_EXP = 2;
    parameter integer GAP     = 6144;
    parameter integer NMAX    = 16384;

    reg clk, rst_n, in_valid;
    reg signed [W-1:0] x_in, d_in;
    wire out_valid, busy;
    wire signed [W-1:0] y_out, e_out;
    wire [5:0] sat_flags;

    anc_core #(.W(W), .L(L), .ALGO(ALGO), .MU_INT(MU_INT), .K(K),
               .ACC_W(ACC_W), .EPS_EXP(EPS_EXP)) dut (
        .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .freeze(1'b0), .x_in(x_in), .d_in(d_in),
        .out_valid(out_valid), .y_out(y_out), .e_out(e_out), .sat_flags(sat_flags), .busy(busy));

    initial clk = 1'b0;
    always #10 clk = ~clk;   // 50 MHz

    reg [W-1:0] vx [0:NMAX-1];
    reg [W-1:0] vd [0:NMAX-1];
    reg [W-1:0] t2, t3;
    reg [8*256-1:0] prefix, vcd;
    reg [8*264-1:0] fname;
    integer fd, rc, nsamp, nreq, i;

    initial begin
        if (!$value$plusargs("vec=%s", prefix)) begin
            $display("TB_POWER FAIL no +vec"); $finish(1);
        end
        if (!$value$plusargs("vcd=%s", vcd)) vcd = "tb_power.vcd";
        if (!$value$plusargs("n=%d", nreq)) nreq = 2000;
        $sformat(fname, "%0s.vec", prefix);
        fd = $fopen(fname, "r");
        if (fd == 0) begin $display("TB_POWER FAIL cannot open %0s", fname); $finish(1); end
        nsamp = 0;
        while (!$feof(fd) && nsamp < NMAX) begin
            rc = $fscanf(fd, "%h %h %h %h\n", vx[nsamp], vd[nsamp], t2, t3);
            if (rc == 4) nsamp = nsamp + 1;
        end
        $fclose(fd);
        if (nreq > nsamp) nreq = nsamp;

        rst_n = 1'b0; in_valid = 1'b0; x_in = 0; d_in = 0;
        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        @(posedge clk);
        $dumpfile(vcd);
        $dumpvars(0, dut);
        for (i = 0; i < nreq; i = i + 1) begin
            @(negedge clk);
            x_in = vx[i]; d_in = vd[i]; in_valid = 1'b1;
            @(negedge clk);
            in_valid = 1'b0;
            repeat (GAP - 1) @(negedge clk);
        end
        $dumpoff;
        $display("TB_POWER DONE samples=%0d gap=%0d cycles=%0d", nreq, GAP, nreq * GAP);
        $finish(0);
    end
endmodule
