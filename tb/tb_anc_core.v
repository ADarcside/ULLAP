`timescale 1ns/1ps
// -----------------------------------------------------------------------------
// Self-checking testbench for anc_core (bit-exact against the Python reference).
//
//   +vec=<prefix>   golden vectors <prefix>.vec  (x d y_exp e_exp, hex, one line per sample)
//                                  <prefix>.w    (final coefficients, hex, L lines)
//                   optional       <prefix>.flg  (expected sticky sat_flags, one hex number)
//   +maxn=<N>       optional, use only the first N lines of the .vec file
//
// Parameters (override with -P / -G on the command line) must match the vector set:
//   W L ALGO MU_INT K ACC_W EPS_EXP
//
// Checks: y_out/e_out of every sample, out_valid count and latency, final
// coefficients (hierarchical read of dut.w[]), sticky saturation flags
// (without .flg: flags w,g,e,y,acc must stay 0; bit0 'in' is tied to 0 in RTL).
// Prints exactly one line "TB_RESULT PASS ..." or "TB_RESULT FAIL ..." and ends
// with $finish(0) / $finish(1).  Simulator exit codes for $finish are not
// portable, so scripts must grep the TB_RESULT line.
// -----------------------------------------------------------------------------
module tb_anc_core;
    parameter integer W       = 11;
    parameter integer L       = 32;
    parameter integer ALGO    = 2;
    parameter integer MU_INT  = 512;
    parameter integer K       = 4;
    parameter integer ACC_W   = 2*W + $clog2(L);
    parameter integer EPS_EXP = 10;
    parameter integer NMAX    = 4096;

    localparam integer LAT_EXP = (ALGO == 0) ? (L + 3) : (L + 5);   // pipelined core (was L+1 / L+3)

    reg                  clk;
    reg                  rst_n;
    reg                  in_valid;
    reg                  freeze;
    reg  signed [W-1:0]  x_in, d_in;
    wire                 out_valid;
    wire signed [W-1:0]  y_out, e_out;
    wire [5:0]           sat_flags;
    wire                 busy;

    anc_core #(.W(W), .L(L), .ALGO(ALGO), .MU_INT(MU_INT), .K(K),
               .ACC_W(ACC_W), .EPS_EXP(EPS_EXP)) dut (
        .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .freeze(freeze), .x_in(x_in), .d_in(d_in),
        .out_valid(out_valid), .y_out(y_out), .e_out(e_out),
        .sat_flags(sat_flags), .busy(busy));

    // ---------------------------------------------------------------- vectors
    reg [W-1:0] vx [0:NMAX-1];
    reg [W-1:0] vd [0:NMAX-1];
    reg [W-1:0] vy [0:NMAX-1];
    reg [W-1:0] ve [0:NMAX-1];
    reg [W-1:0] vw [0:L-1];
    reg [0:0]          vfrz [0:NMAX-1];
    reg                have_frz;

    reg [8*256-1:0] prefix;
    reg [8*264-1:0] fname;
    integer fd, rc, nsamp, maxn, nw, k;
    reg [W-1:0] t0, t1, t2, t3;
    reg [31:0]  flg_exp;
    reg         have_flg;
    reg         partial;

    // ---------------------------------------------------------------- clock / counters
    initial clk = 1'b0;
    always #5 clk = ~clk;

    integer cyc;                 // clock edges seen so far (incremented in the checker block)
    initial cyc = 0;

    // ---------------------------------------------------------------- checker
    integer n_out, n_in, y_bad, e_bad, w_bad, lat_bad, cnt_bad, lat_seen;
    integer accept_edge [0:NMAX-1];
    initial begin n_out = 0; n_in = 0; y_bad = 0; e_bad = 0; w_bad = 0; lat_bad = 0; cnt_bad = 0; lat_seen = -1; end

    integer bcnt, bmax;            // consecutive busy cycles of the current sample / maximum seen
    initial begin bcnt = 0; bmax = 0; end

    always @(posedge clk) begin
        cyc = cyc + 1;
        if (busy) bcnt = bcnt + 1;
        else begin
            if (bcnt > bmax) bmax = bcnt;
            bcnt = 0;
        end
        if (rst_n && out_valid) begin
            if (n_out >= n_in) begin
                cnt_bad = cnt_bad + 1;                    // out_valid without a pending sample
            end else begin
                if (y_out !== vy[n_out]) begin
                    y_bad = y_bad + 1;
                    if (y_bad <= 5) $display("MISMATCH y  n=%0d got=%h exp=%h", n_out, y_out, vy[n_out]);
                end
                if (e_out !== ve[n_out]) begin
                    e_bad = e_bad + 1;
                    if (e_bad <= 5) $display("MISMATCH e  n=%0d got=%h exp=%h", n_out, e_out, ve[n_out]);
                end
                // out_valid sampled here was registered at the previous edge (cyc-1)
                if ((cyc - 1) - accept_edge[n_out] != LAT_EXP) begin
                    lat_bad = lat_bad + 1;
                    if (lat_bad <= 3) $display("LATENCY n=%0d got=%0d exp=%0d", n_out,
                                               (cyc - 1) - accept_edge[n_out], LAT_EXP);
                end
                lat_seen = (cyc - 1) - accept_edge[n_out];
            end
            n_out = n_out + 1;
        end
    end

    // ---------------------------------------------------------------- stimulus
    integer n, ok_flags, nfail;
    initial begin
        in_valid = 1'b0; x_in = 0; d_in = 0; rst_n = 1'b0;
        if (!$value$plusargs("vec=%s", prefix)) begin
            $display("TB_RESULT FAIL missing +vec=<prefix>");
            $finish(1);
        end
        maxn = NMAX;
        partial = 1'b0;
        if ($value$plusargs("maxn=%d", maxn)) partial = 1'b1;
        if (maxn > NMAX) maxn = NMAX;

        // read golden vectors
        fname = {prefix, ".vec"};
        fd = $fopen(fname, "r");
        if (fd == 0) begin $display("TB_RESULT FAIL cannot open %0s", fname); $finish(1); end
        nsamp = 0;
        rc = 4;
        while (rc == 4 && nsamp < maxn) begin
            rc = $fscanf(fd, "%h %h %h %h\n", t0, t1, t2, t3);
            if (rc == 4) begin
                vx[nsamp] = t0; vd[nsamp] = t1; vy[nsamp] = t2; ve[nsamp] = t3;
                nsamp = nsamp + 1;
            end
        end
        $fclose(fd);

        fname = {prefix, ".w"};
        fd = $fopen(fname, "r");
        if (fd == 0) begin $display("TB_RESULT FAIL cannot open %0s", fname); $finish(1); end
        nw = 0;
        rc = 1;
        while (rc == 1 && nw < L) begin
            rc = $fscanf(fd, "%h\n", t0);
            if (rc == 1) begin vw[nw] = t0; nw = nw + 1; end
        end
        $fclose(fd);

        have_flg = 1'b0; flg_exp = 0;
        fname = {prefix, ".flg"};
        fd = $fopen(fname, "r");
        if (fd != 0) begin
            rc = $fscanf(fd, "%h\n", flg_exp);
            if (rc == 1) have_flg = 1'b1;
            $fclose(fd);
        end

        have_frz = 1'b0;
        fname = {prefix, ".frz"};
        fd = $fopen(fname, "r");
        if (fd != 0) begin
            have_frz = 1'b1;
            for (k = 0; k < nsamp; k = k + 1) begin
                rc = $fscanf(fd, "%b\n", t0);
                vfrz[k] = t0[0];
            end
            $fclose(fd);
        end

        if (nsamp == 0 || nw != L) begin
            $display("TB_RESULT FAIL bad vector files nsamp=%0d nw=%0d (L=%0d)", nsamp, nw, L);
            $finish(1);
        end
        // the .w file holds the coefficients after the LAST line of the .vec file, so the final
        // coefficient check is only valid when the whole file is used (+maxn= makes it a smoke test)

        repeat (4) @(posedge clk);
        #1 rst_n = 1'b1;
        repeat (2) @(posedge clk);

        freeze = 1'b0;
        for (n = 0; n < nsamp; n = n + 1) begin
            @(negedge clk);
            while (busy) @(negedge clk);
            x_in = vx[n]; d_in = vd[n];
            freeze = have_frz ? vfrz[n] : 1'b0;
            in_valid = 1'b1;
            accept_edge[n] = cyc + 1;                     // the next posedge samples in_valid
            n_in = n_in + 1;
            @(negedge clk);
            in_valid = 1'b0;
            freeze = 1'b0;
            x_in = {W{1'bx}}; d_in = {W{1'bx}};            // data only meaningful during the strobe
        end
        // drain: wait until the core is idle and the last output was seen
        @(negedge clk);
        while (busy) @(negedge clk);
        repeat (4) @(posedge clk);
        #1;

        // final coefficient check (hierarchical reference into the DUT)
        if (!partial) begin
            for (k = 0; k < L; k = k + 1) begin
                if (dut.w[k] !== vw[k]) begin
                    w_bad = w_bad + 1;
                    if (w_bad <= 5) $display("MISMATCH w[%0d] got=%h exp=%h", k, dut.w[k], vw[k]);
                end
            end
        end else begin
            $display("NOTE: partial run (%0d samples): final-coefficient check skipped", nsamp);
        end

        // saturation flags
        if (have_flg) ok_flags = ((sat_flags & 6'h3E) === (flg_exp[5:0] & 6'h3E));
        else          ok_flags = ((sat_flags & 6'h3E) === 6'h00);
        if (!ok_flags) $display("MISMATCH sat_flags got=%b exp=%b (have_flg=%0d)", sat_flags,
                                have_flg ? flg_exp[5:0] : 6'b0, have_flg);

        nfail = y_bad + e_bad + w_bad + lat_bad + cnt_bad + (ok_flags ? 0 : 1) + ((n_out != nsamp) ? 1 : 0);
        if (nfail == 0)
            $display("TB_RESULT PASS vec=%0s ALGO=%0d W=%0d L=%0d samples=%0d y_bad=0 e_bad=0 w_bad=0 flags=%b lat=%0d busy_cycles=%0d",
                     prefix, ALGO, W, L, nsamp, sat_flags, lat_seen, bmax);
        else begin
            $display("TB_RESULT FAIL vec=%0s ALGO=%0d W=%0d L=%0d samples=%0d y_bad=%0d e_bad=%0d w_bad=%0d lat_bad=%0d cnt_bad=%0d n_out=%0d flags_ok=%0d",
                     prefix, ALGO, W, L, nsamp, y_bad, e_bad, w_bad, lat_bad, cnt_bad, n_out, ok_flags);
            $finish(1);
        end
        $finish(0);
    end

    // watchdog
    initial begin
        #(64'd200000000);
        $display("TB_RESULT FAIL timeout");
        $finish(1);
    end
endmodule
