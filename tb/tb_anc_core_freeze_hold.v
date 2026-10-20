`timescale 1ns/1ps
// -----------------------------------------------------------------------------
// Testbench for anc_core evaluating adaptation freeze hold & toggle variants.
// Drives freeze independently of in_valid with per-sample patterns:
//   Pattern A (n % 4 == 0): freeze=1 at accept, forced 0 from next cycle on
//   Pattern B (n % 4 == 1): freeze=0 at accept, forced 1 from next cycle on
//   Pattern C (n % 4 == 2): freeze=1 only on the cycle AFTER accept
//   Pattern D (n % 4 == 3): freeze held 1 from accept through write-back
// -----------------------------------------------------------------------------
module tb_anc_core_freeze_hold;
    parameter integer W       = 12;
    parameter integer L       = 32;
    parameter integer ALGO    = 2;
    parameter integer MU_INT  = 512;
    parameter integer K       = 3;
    parameter integer ACC_W   = 29;
    parameter integer EPS_EXP = 2;
    parameter integer NMAX    = 16384;

    localparam integer LAT_EXP = (ALGO == 0) ? (L + 3) : (L + 5);

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

    integer cyc;
    initial cyc = 0;

    // ---------------------------------------------------------------- checker
    integer n_out, n_in, y_bad, e_bad, w_bad, lat_bad, cnt_bad, lat_seen;
    integer accept_edge [0:NMAX-1];
    initial begin n_out = 0; n_in = 0; y_bad = 0; e_bad = 0; w_bad = 0; lat_bad = 0; cnt_bad = 0; lat_seen = -1; end

    integer bcnt, bmax;
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
                cnt_bad = cnt_bad + 1;
            end else begin
                if (y_out !== vy[n_out]) begin
                    y_bad = y_bad + 1;
                    if (y_bad <= 5) $display("MISMATCH y  n=%0d got=%h exp=%h", n_out, y_out, vy[n_out]);
                end
                if (e_out !== ve[n_out]) begin
                    e_bad = e_bad + 1;
                    if (e_bad <= 5) $display("MISMATCH e  n=%0d got=%h exp=%h", n_out, e_out, ve[n_out]);
                end
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
        while (rc == 4 && nsamp < NMAX && (maxn == 0 || nsamp < maxn)) begin
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

        if (nsamp == 0 || nw != L) begin
            $display("TB_RESULT FAIL bad vector files nsamp=%0d nw=%0d (L=%0d)", nsamp, nw, L);
            $finish(1);
        end

        repeat (4) @(posedge clk);
        #1 rst_n = 1'b1;
        repeat (2) @(posedge clk);

        freeze = 1'b0;
        for (n = 0; n < nsamp; n = n + 1) begin
            @(negedge clk);
            while (busy) @(negedge clk);
            x_in = vx[n]; d_in = vd[n];
            in_valid = 1'b1;
            accept_edge[n] = cyc + 1;
            n_in = n_in + 1;

            // Pattern at accept (cycle 0)
            case (n % 4)
                0: freeze = 1'b1; // Pattern A: 1 at accept
                1: freeze = 1'b0; // Pattern B: 0 at accept
                2: freeze = 1'b0; // Pattern C: 0 at accept
                3: freeze = 1'b1; // Pattern D: 1 at accept
            endcase

            // Cycle 1: one cycle after accept
            @(negedge clk);
            in_valid = 1'b0;
            x_in = {W{1'bx}}; d_in = {W{1'bx}};
            case (n % 4)
                0: freeze = 1'b0; // Pattern A: forced 0 from next cycle on
                1: freeze = 1'b1; // Pattern B: forced 1 from next cycle on
                2: freeze = 1'b1; // Pattern C: freeze=1 ONLY on cycle 1
                3: freeze = 1'b1; // Pattern D: held 1 through write-back
            endcase

            // Cycle 2: two cycles after accept
            @(negedge clk);
            if ((n % 4) == 2) begin
                freeze = 1'b0;    // Pattern C: drops to 0 on cycle 2
            end

            // Wait for core to complete processing
            while (busy) @(negedge clk);
            freeze = 1'b0;
        end

        repeat (LAT_EXP + 5) @(posedge clk);

        if (!partial) begin
            for (k = 0; k < L; k = k + 1) begin
                if (dut.w[k] !== vw[k]) begin
                    w_bad = w_bad + 1;
                    if (w_bad <= 5) $display("MISMATCH w[%0d] got=%h exp=%h", k, dut.w[k], vw[k]);
                end
            end
        end

        if (n_out != nsamp) cnt_bad = cnt_bad + 1;

        if (have_flg)
            ok_flags = ((sat_flags & 6'b111110) == (flg_exp[5:0] & 6'b111110));
        else
            ok_flags = ((sat_flags & 6'b111110) == 6'b000000);

        nfail = y_bad + e_bad + w_bad + lat_bad + cnt_bad + (ok_flags ? 0 : 1);
        if (nfail == 0) begin
            $display("TB_RESULT PASS vec=%0s ALGO=%0d W=%0d L=%0d samples=%0d y_bad=0 e_bad=0 w_bad=0 flags=%06b lat=%0d busy_cycles=%0d",
                     prefix, ALGO, W, L, nsamp, sat_flags, lat_seen, bmax);
            $finish(0);
        end else begin
            $display("TB_RESULT FAIL vec=%0s ALGO=%0d W=%0d L=%0d samples=%0d y_bad=%0d e_bad=%0d w_bad=%0d lat_bad=%0d cnt_bad=%0d n_out=%0d flags_ok=%0d",
                     prefix, ALGO, W, L, nsamp, y_bad, e_bad, w_bad, lat_bad, cnt_bad, n_out, ok_flags);
            $finish(1);
        end
    end

endmodule
