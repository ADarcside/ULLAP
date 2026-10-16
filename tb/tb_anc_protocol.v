`timescale 1ns/1ps
// -----------------------------------------------------------------------------
// Protocol / corner-case testbench for anc_core (no golden vectors needed).
//   Test 1: in_valid pulses (garbage data) while busy=1 must be ignored: DUT A (clean stimulus) and DUT B
//           (same accepted samples + garbage strobes during busy) must be cycle-identical.
//   Test 2: synchronous reset in the middle of a weight update: afterwards busy/out_valid/sat_flags/w are
//           clear and DUT B behaves exactly like DUT C, which was never used (fresh from reset).
// Prints one line "TB_PROTO PASS ..." or "TB_PROTO FAIL ...".  Params must be set with -P/-G like tb_anc_core.
// STATUS: written in a session without any Verilog simulator; see docs/verification.md.
// -----------------------------------------------------------------------------
module tb_anc_protocol;
    parameter integer W      = 11;
    parameter integer L      = 8;
    parameter integer ALGO   = 2;
    parameter integer MU_INT = 512;
    parameter integer K      = 4;
    parameter integer ACC_W  = 2*W + $clog2(L);

    reg clk;
    reg rstA, rstB, rstC;
    reg vA, vB, vC;
    reg signed [W-1:0] xA, dA, xB, dB, xC, dC;
    wire ovA, ovB, ovC, bA, bB, bC;
    wire signed [W-1:0] yA, eA, yB, eB, yC, eC;
    wire [5:0] fA, fB, fC;

    anc_core #(.W(W), .L(L), .ALGO(ALGO), .MU_INT(MU_INT), .K(K), .ACC_W(ACC_W)) dutA (
        .clk(clk), .rst_n(rstA), .in_valid(vA), .x_in(xA), .d_in(dA),
        .out_valid(ovA), .y_out(yA), .e_out(eA), .sat_flags(fA), .busy(bA));
    anc_core #(.W(W), .L(L), .ALGO(ALGO), .MU_INT(MU_INT), .K(K), .ACC_W(ACC_W)) dutB (
        .clk(clk), .rst_n(rstB), .in_valid(vB), .x_in(xB), .d_in(dB),
        .out_valid(ovB), .y_out(yB), .e_out(eB), .sat_flags(fB), .busy(bB));
    anc_core #(.W(W), .L(L), .ALGO(ALGO), .MU_INT(MU_INT), .K(K), .ACC_W(ACC_W)) dutC (
        .clk(clk), .rst_n(rstC), .in_valid(vC), .x_in(xC), .d_in(dC),
        .out_valid(ovC), .y_out(yC), .e_out(eC), .sat_flags(fC), .busy(bC));

    initial clk = 1'b0;
    always #5 clk = ~clk;

    integer seed, errs, nout_ab, nout_bc, chk_ab, chk_bc, i, j, k;

    // continuous cycle-by-cycle comparison
    always @(posedge clk) begin
        if (chk_ab) begin
            if (ovA !== ovB || bA !== bB) begin errs = errs + 1; if (errs <= 5) $display("MISMATCH A/B timing t=%0t", $time); end
            else if (ovA === 1'b1) begin
                nout_ab = nout_ab + 1;
                if (yA !== yB || eA !== eB || fA !== fB) begin errs = errs + 1; if (errs <= 5) $display("MISMATCH A/B data t=%0t", $time); end
            end
        end
        if (chk_bc) begin
            if (ovB !== ovC || bB !== bC) begin errs = errs + 1; if (errs <= 5) $display("MISMATCH B/C timing t=%0t", $time); end
            else if (ovB === 1'b1) begin
                nout_bc = nout_bc + 1;
                if (yB !== yC || eB !== eC || fB !== fC) begin errs = errs + 1; if (errs <= 5) $display("MISMATCH B/C data t=%0t", $time); end
            end
        end
    end

    initial begin
        seed = 12345; errs = 0; nout_ab = 0; nout_bc = 0; chk_ab = 0; chk_bc = 0;
        rstA = 1'b0; rstB = 1'b0; rstC = 1'b0; vA = 1'b0; vB = 1'b0; vC = 1'b0;
        xA = 0; dA = 0; xB = 0; dB = 0; xC = 0; dC = 0;
        repeat (4) @(negedge clk);
        rstA = 1'b1; rstB = 1'b1;                       // C stays in reset until test 2
        repeat (2) @(negedge clk);

        // ---------------- test 1: in_valid while busy is ignored
        chk_ab = 1;
        // 1a: continuous garbage strobes on B for the whole busy period
        for (i = 0; i < 30; i = i + 1) begin
            @(negedge clk);
            while (bA || bB) @(negedge clk);
            xA = $random(seed); dA = $random(seed);
            xB = xA; dB = dA; vA = 1'b1; vB = 1'b1;
            @(negedge clk);
            vA = 1'b0; vB = 1'b0;
            while (bB) begin                            // garbage strobes on B for the whole busy period
                xB = $random(seed); dB = $random(seed); vB = 1'b1;
                @(negedge clk);
            end
            vB = 1'b0;
        end
        // 1b: single-cycle strobe at cycle 1 and cycle LAT while busy
        for (i = 0; i < 15; i = i + 1) begin
            @(negedge clk);
            while (bA || bB) @(negedge clk);
            xA = $random(seed); dA = $random(seed);
            xB = xA; dB = dA; vA = 1'b1; vB = 1'b1;
            @(negedge clk);
            vA = 1'b0; vB = 1'b1; xB = $random(seed); dB = $random(seed); // cycle 1 strobe on B
            @(negedge clk);
            vB = 1'b0;
            while (bB) @(negedge clk);
        end
        repeat (4) @(negedge clk);
        chk_ab = 0;
        if (nout_ab != 45) begin errs = errs + 1; $display("MISMATCH test1 out count %0d != 45", nout_ab); end
        for (k = 0; k < L; k = k + 1)
            if (dutA.w[k] !== dutB.w[k]) begin errs = errs + 1; $display("MISMATCH test1 w[%0d]", k); end

        // ---------------- test 2: reset at different points during an update
        // sweep reset point from cycle 1 to cycle L+10 across all internal phases
        for (j = 1; j <= (L + 10); j = j + 2) begin
            xB = $random(seed); dB = $random(seed); vB = 1'b1;
            @(negedge clk); vB = 1'b0;
            repeat (j) @(negedge clk);
            rstB = 1'b0; rstC = 1'b0;
            repeat (3) @(negedge clk);
            if (bB !== 1'b0 || ovB !== 1'b0 || fB !== 6'd0) begin
                errs = errs + 1; $display("MISMATCH test2: state after reset at offset %0d", j);
            end
            for (k = 0; k < L; k = k + 1)
                if (dutB.w[k] !== {W{1'b0}} || dutB.xv[k] !== {W{1'b0}}) begin
                    errs = errs + 1; $display("MISMATCH test2: w/xv[%0d] not cleared at offset %0d", k, j);
                end
            rstB = 1'b1; rstC = 1'b1;
            repeat (2) @(negedge clk);
            chk_bc = 1;
            nout_bc = 0;
            for (i = 0; i < 10; i = i + 1) begin
                @(negedge clk);
                while (bB || bC) @(negedge clk);
                xB = $random(seed); dB = $random(seed); xC = xB; dC = dB; vB = 1'b1; vC = 1'b1;
                @(negedge clk);
                vB = 1'b0; vC = 1'b0;
            end
            @(negedge clk);
            while (bB || bC) @(negedge clk);
            repeat (2) @(negedge clk);
            chk_bc = 0;
            if (nout_bc != 10) begin errs = errs + 1; $display("MISMATCH test2 post-reset out count %0d != 10 at offset %0d", nout_bc, j); end
            for (k = 0; k < L; k = k + 1)
                if (dutB.w[k] !== dutC.w[k]) begin errs = errs + 1; $display("MISMATCH test2 w[%0d] at offset %0d", k, j); end
        end

        // ---------------- test 3: back-to-back accepted samples (0 idle cycles between busy=0 and in_valid=1)
        rstA = 1'b0; rstB = 1'b0;
        repeat (3) @(negedge clk);
        rstA = 1'b1; rstB = 1'b1;
        repeat (2) @(negedge clk);
        chk_ab = 1;
        nout_ab = 0;
        for (i = 0; i < 30; i = i + 1) begin
            @(negedge clk);
            while (bA || bB) @(negedge clk);
            xA = $random(seed); dA = $random(seed);
            xB = xA; dB = dA; vA = 1'b1; vB = 1'b1;
            @(negedge clk);
            vA = 1'b0; vB = 1'b0;
        end
        @(negedge clk);
        while (bA || bB) @(negedge clk);
        repeat (4) @(negedge clk);
        chk_ab = 0;
        if (nout_ab != 30) begin errs = errs + 1; $display("MISMATCH test3 out count %0d != 30", nout_ab); end
        for (k = 0; k < L; k = k + 1)
            if (dutA.w[k] !== dutB.w[k]) begin errs = errs + 1; $display("MISMATCH test3 w[%0d]", k); end

        if (errs == 0) $display("TB_PROTO PASS ALGO=%0d W=%0d L=%0d", ALGO, W, L);
        else           $display("TB_PROTO FAIL errs=%0d ALGO=%0d W=%0d L=%0d", errs, ALGO, W, L);
        $finish;
    end

    initial begin
        #(64'd50000000);
        $display("TB_PROTO FAIL timeout");
        $finish;
    end
endmodule
