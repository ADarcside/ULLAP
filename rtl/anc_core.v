// -----------------------------------------------------------------------------
// anc_core : adaptive noise canceller core (LMS / NLMS / NLMS-shift), serial
//            one-multiplier architecture, bit-exact to py/fixedpoint.py:run_fixed
//
// Portable Verilog (2001 + $clog2 from 2005).  No vendor primitives, IP, PLLs,
// RAM/DSP macros or constraints.  Spec: docs/rtl_interface.md.
//
// Arithmetic contract (F = W-1, rs(v,s) = (v + 2^(s-1)) >>> s, round half up):
//   acc = sat_ACC_W( sum_i w[i]*xv[i] )         (exact sum, saturated once)
//   y   = sat_W( rs(acc,F) );   e = sat_W( d - y )
//   P   = sum_i xv[i]^2 (exact), Q = P + 2^(2F-EPS_EXP)
//   LMS       : upd = rs( (MU_INT*e)*xv[i], F+10 )
//   NLMS      : g = sat_{W+4}( floor((2n+Q)/(2Q)) ), n = (MU_INT*e) << (2F-10)
//               upd = rs( g*xv[i], F )
//   NLMS-shift: upd = rs( e*xv[i], bitlen(Q) - F + K )
//   w[i] = sat_W( w[i] + upd )
//
// Schedule per accepted sample pair (one multiplier, now PIPELINED: operand regs -> product reg -> consume):
//   IDLE(accept) -> [P0,P1: issue x_new^2, x_old^2, ALGO!=0] -> MAC issue (L cycles) -> WAIT(2)
//   -> YE (y/e/out_valid) -> [MU issue -> WAIT(2) -> [MU2 -> DIV (ALGO 1)]] -> UPD issue (L cycles) -> WAIT(3) -> IDLE
// The power P is maintained incrementally: P += x_new^2 - x_dropped^2.  This is exact integer arithmetic,
// hence identical to recomputing sum(xv^2).  The pipeline only moves the same arithmetic into later cycles,
// so results are bit-identical to the unpipelined core (verified on all vector sets).
//
// Timing (clock edges, edge 0 = the edge that samples in_valid=1):
//   out_valid is registered high after edge LAT, LAT = L+3 (ALGO 0), L+5 (else).
//   busy stays high until the weight update is finished; in_valid pulses that
//   arrive while busy=1 are IGNORED (the caller must wait for busy=0).
//
// Adaptation freeze semantics (`freeze`):
//   `freeze` is sampled into `freeze_r` on the clock edge where `in_valid` is accepted
//   (S_IDLE state). When `freeze_r` is active, filtering continues normally (y_out,
//   e_out, output latency, and busy cycle count are completely unaffected), but
//   coefficient writes (w[i3] updates) and the coefficient saturation flag (sat_flags[5],
//   w bit) are suppressed for that sample. Tying `freeze` to 1'b0 gives bit-identical
//   behavior to a core without freeze.
//
// Extra ports vs. the minimum spec: `busy`, `freeze`.
// sat_flags bit0 ("in") is tied to 0: inputs are already W bits wide, so there
// is nothing to saturate in RTL (the Python 'in_x/in_d' counters count float ->
// fixed clipping outside the core).
// Supported range: 8 <= W <= 31, L >= 2, F + K >= EPS_EXP (ALGO 2), 2F >= 10, ACC_W <= 62
//   (default ACC_W = 2W+clog2(L) <= 62 limits W to <= 28 for L = 32; larger W needs an explicit ACC_W).
//   Python reference uses int64: bit-exact checking is only meaningful while 2W+clog2(L)+2 <= 63.
// -----------------------------------------------------------------------------
module anc_core #(
    parameter integer W        = 12,
    parameter integer L        = 32,
    parameter integer ALGO     = 2,      // 0 LMS, 1 NLMS, 2 NLMS-shift
    parameter integer MU_INT   = 512,    // round(mu*2^10), ALGO 0/1
    parameter integer K        = 3,      // mu = 2^-K, ALGO 2 (tuned together with EPS_EXP, see docs/phase1_eps_tuning.md)
    parameter integer ACC_W    = 2*W + $clog2(L),
    parameter integer EPS_EXP  = 2       // eps = 2^-EPS_EXP; 2 chosen by the Phase-1 sweep (was 10)
) (
    input  wire                 clk,
    input  wire                 rst_n,      // synchronous, active low
    input  wire                 in_valid,   // 1-cycle strobe
    input  wire                 freeze,     // adaptation freeze (sampled when in_valid is accepted; blocks w write & w sat flag; no effect on lat/busy; tie to 0 = identical to old core)
    input  wire signed [W-1:0]  x_in,
    input  wire signed [W-1:0]  d_in,
    output reg                  out_valid,
    output reg  signed [W-1:0]  y_out,
    output reg  signed [W-1:0]  e_out,
    output reg  [5:0]           sat_flags,  // {w, g, e, y, acc, in}, sticky
    output wire                 busy
);

    // ------------------------------------------------------------ constants
    localparam integer F    = W - 1;
    localparam integer CL   = $clog2(L);
    localparam integer MUW  = $clog2(MU_INT + 1) + 1;                 // signed width of MU_INT
    localparam integer GW   = W + 4;                                  // NLMS gain width
    localparam integer AW   = (W + MUW > GW) ? (W + MUW) : GW;        // multiplier A-operand width
    localparam integer PRW  = AW + W;                                 // product width
    localparam integer EXW  = 2*W + CL + 1;                           // exact accumulator width
    localparam integer AXW  = (ACC_W + 1 > EXW) ? (ACC_W + 1) : EXW;  // internal accumulator width
    localparam integer PW   = 2*W + CL + 2;                           // power register width
    localparam integer NW   = W + MUW + 2*F + 4 + CL;                 // divider dividend width
    localparam integer IW   = CL;                                     // tap counter width (counts 0..L-1)
    localparam integer CW   = $clog2(NW + 2) + 1;                     // divider counter width
    localparam integer UPS  = (ALGO == 0) ? (F + 10) : F;             // fixed update shift (ALGO 0/1)

    localparam signed [63:0] WMAX   = (64'sd1 <<< (W - 1)) - 64'sd1;
    localparam signed [63:0] WMIN   = -(64'sd1 <<< (W - 1));
    localparam signed [63:0] GMAX   = (64'sd1 <<< (GW - 1)) - 64'sd1;
    localparam signed [63:0] GMIN   = -(64'sd1 <<< (GW - 1));
    localparam signed [63:0] ACCMAX = (64'sd1 <<< (ACC_W - 1)) - 64'sd1;
    localparam signed [63:0] ACCMIN = -(64'sd1 <<< (ACC_W - 1));

    localparam signed [AW-1:0]  MU_C  = MU_INT;
    localparam signed [PW-1:0]  EPS_C = 64'sd1 <<< (2*F - EPS_EXP);
    localparam signed [AXW-1:0] HALFF = {{(AXW-1){1'b0}}, 1'b1} << (F - 1);

    localparam [3:0] S_IDLE = 4'd0, S_P0 = 4'd1, S_P1 = 4'd2, S_MAC = 4'd3, S_YE = 4'd4,
                     S_MU   = 4'd5, S_DIV = 4'd6, S_UPD = 4'd7, S_WAIT = 4'd8, S_MU2 = 4'd9;
    // operation kinds carried down the multiplier pipeline
    localparam [2:0] K_NONE = 3'd0, K_P0 = 3'd1, K_P1 = 3'd2, K_MAC = 3'd3, K_MU = 3'd4, K_UPD = 3'd5;

    // elaboration-time sanity checks (ignored by synthesis)
    // synthesis translate_off
    initial begin
        if (W < 8 || W > 31 || L < 2 || 2*F < 10 || ACC_W > 62 ||
            (ALGO == 2 && (F + K < EPS_EXP)) || ALGO < 0 || ALGO > 2) begin
            $display("anc_core: unsupported parameter combination W=%0d L=%0d ALGO=%0d K=%0d ACC_W=%0d",
                     W, L, ALGO, K, ACC_W);
            $finish;
        end
    end
    // synthesis translate_on

    // ------------------------------------------------------------ state
    reg [3:0]                    state;
    reg [IW-1:0]                 i;
    reg                          freeze_r;
    reg signed [W-1:0]           xv [0:L-1];     // xv[0] = newest sample
    reg signed [W-1:0]           w  [0:L-1];     // coefficients
    reg signed [W-1:0]           xold;           // sample dropped from the window
    reg signed [W-1:0]           d_r;
    reg signed [W-1:0]           e_r;
    reg signed [AXW-1:0]         accx;
    reg signed [PW-1:0]          pw;
    reg signed [AW-1:0]          m;              // multiplicand of the update pass
    integer                      sh_r;           // update shift (ALGO 2)

    // pipeline registers (operand -> product -> consume -> write-back)
    reg signed [AW-1:0]          ma_q;           // stage 1: registered multiplier operands
    reg signed [W-1:0]           mb_q;
    reg [2:0]                    k1;
    reg [IW-1:0]                 i1;
    reg signed [PRW-1:0]         p_q;            // stage 2: registered product
    reg [2:0]                    k2;
    reg [IW-1:0]                 i2;
    reg signed [PRW-1:0]         pm;             // product of MU_INT*e (kept for the NLMS divider set-up)
    reg signed [PRW:0]           upd_q;          // stage 3: rounded update term
    reg                          k3_upd;
    reg [IW-1:0]                 i3;
    reg [1:0]                    wc;             // wait counter
    reg [3:0]                    nxt;            // state after S_WAIT

    // divider state
    reg [NW-1:0]                 dvd;
    reg [NW:0]                   dsr;
    reg [NW:0]                   rem_r;
    reg [NW-1:0]                 quo;
    reg                          dsign;
    reg [CW-1:0]                 cnt;

    assign busy = (state != S_IDLE);

    // ------------------------------------------------------------ shared multiplier
    wire signed [W-1:0] w_cur  = w[i];
    wire signed [W-1:0] xv_cur = xv[i];
    wire signed [W-1:0] xv_new = xv[0];

    reg signed [AW-1:0] mul_a;
    reg signed [W-1:0]  mul_b;
    reg [2:0]           mul_k;
    always @* begin
        mul_a = {AW{1'b0}};
        mul_b = {W{1'b0}};
        mul_k = K_NONE;
        case (state)
            S_P0:    begin mul_a = xv_new; mul_b = xv_new; mul_k = K_P0;  end
            S_P1:    begin mul_a = xold;   mul_b = xold;   mul_k = K_P1;  end
            S_MAC:   begin mul_a = w_cur;  mul_b = xv_cur; mul_k = K_MAC; end
            S_MU:    begin mul_a = MU_C;   mul_b = e_r;    mul_k = K_MU;  end
            S_UPD:   begin mul_a = m;      mul_b = xv_cur; mul_k = K_UPD; end
            default: begin end
        endcase
    end
    // stage 2 combinational product of the REGISTERED operands (register-to-register path)
    wire signed [PRW-1:0] prod = ma_q * mb_q;

    // ------------------------------------------------------------ helpers
    function integer bitlen;           // index of leading one + 1 (0 for 0)
        input [PW-1:0] v;
        integer j;
        begin
            bitlen = 0;
            for (j = 0; j < PW; j = j + 1)
                if (v[j]) bitlen = j + 1;
        end
    endfunction

    // temporaries (blocking, used only inside the clocked block)
    reg signed [AXW-1:0]  t_acc, t_y, t_ys;
    reg signed [W:0]      t_e;
    reg signed [W-1:0]    t_ysat, t_esat;
    reg signed [PW-1:0]   t_q;
    reg signed [NW-1:0]   t_num, t_n2;
    reg [NW:0]            t_qm, t_rn;
    reg signed [NW:0]     t_qs;
    reg signed [GW-1:0]   t_g;
    integer               t_s;
    reg signed [PRW:0]    t_px, t_sum, t_half, t_upd;
    reg signed [PRW+1:0]  t_wn;
    reg signed [W-1:0]    t_wsat;
    integer               k;

    // ------------------------------------------------------------ main sequential block
    always @(posedge clk) begin
        if (!rst_n) begin
            state     <= S_IDLE;
            i         <= {IW{1'b0}};
            out_valid <= 1'b0;
            y_out     <= {W{1'b0}};
            e_out     <= {W{1'b0}};
            sat_flags <= 6'd0;
            xold      <= {W{1'b0}};
            d_r       <= {W{1'b0}};
            e_r       <= {W{1'b0}};
            accx      <= {AXW{1'b0}};
            pw        <= {PW{1'b0}};
            m         <= {AW{1'b0}};
            sh_r      <= 0;
            dvd       <= {NW{1'b0}};
            dsr       <= {(NW+1){1'b0}};
            rem_r     <= {(NW+1){1'b0}};
            quo       <= {NW{1'b0}};
            dsign     <= 1'b0;
            cnt       <= {CW{1'b0}};
            ma_q <= {AW{1'b0}}; mb_q <= {W{1'b0}}; k1 <= K_NONE; i1 <= {IW{1'b0}};
            p_q  <= {PRW{1'b0}}; k2 <= K_NONE; i2 <= {IW{1'b0}}; pm <= {PRW{1'b0}};
            upd_q <= {(PRW+1){1'b0}}; k3_upd <= 1'b0; i3 <= {IW{1'b0}};
            wc <= 2'd0; nxt <= S_IDLE;
            freeze_r <= 1'b0;
            for (k = 0; k < L; k = k + 1) begin
                xv[k] <= {W{1'b0}};
                w[k]  <= {W{1'b0}};
            end
        end else begin
            out_valid <= 1'b0;
            // ---------------------------------------------------------- free-running multiplier pipeline
            // stage 1: operand registers      (issue state selects operands, see mul_a / mul_b / mul_k)
            // stage 2: product register       (p_q <= ma_q * mb_q)
            // stage 3: consume                (power / accumulate / MU product / rounded update term)
            // stage 4: coefficient write-back (w[i3] <= sat(w[i3] + upd_q))
            ma_q <= mul_a;  mb_q <= mul_b;  k1 <= mul_k;  i1 <= i;
            p_q  <= prod;   k2 <= k1;       i2 <= i1;
            k3_upd <= 1'b0;
            case (k2)
                K_P0:  pw   <= pw + p_q;                 // + x_new^2
                K_P1:  pw   <= pw - p_q;                 // - x_dropped^2
                K_MAC: accx <= accx + p_q;
                K_MU:  begin pm <= p_q; m <= p_q[AW-1:0]; end
                K_UPD: begin
                    t_s  = (ALGO == 2) ? sh_r : UPS;
                    t_px = p_q;                            // sign-extend
                    if (t_s > PRW) begin
                        // |prod| < 2^(PRW-1) <= 2^(t_s-1): rs() is exactly 0 (see rtl_model.upd_rtl)
                        t_upd = {(PRW+1){1'b0}};
                    end else if (t_s > 0) begin
                        t_half = {{PRW{1'b0}}, 1'b1} << (t_s - 1);
                        t_sum  = t_px + t_half;
                        t_upd  = t_sum >>> t_s;
                    end else begin
                        t_upd  = t_px <<< (-t_s);
                    end
                    upd_q  <= t_upd;
                    k3_upd <= 1'b1;
                    i3     <= i2;
                end
                default: begin end
            endcase
            if (k3_upd && !freeze_r) begin
                t_wn = w[i3] + upd_q;
                if (t_wn > WMAX) begin
                    t_wsat = WMAX[W-1:0];
                    sat_flags[5] <= 1'b1;
                end else if (t_wn < WMIN) begin
                    t_wsat = WMIN[W-1:0];
                    sat_flags[5] <= 1'b1;
                end else begin
                    t_wsat = t_wn[W-1:0];
                end
                w[i3] <= t_wsat;
            end
            // ---------------------------------------------------------- control FSM
            case (state)
            // ---------------------------------------------------------- accept
            S_IDLE: begin
                if (in_valid) begin
                    xold <= xv[L-1];
                    for (k = L-1; k > 0; k = k - 1)
                        xv[k] <= xv[k-1];
                    xv[0] <= x_in;
                    freeze_r <= freeze;
                    d_r   <= d_in;
                    accx  <= {AXW{1'b0}};
                    i     <= {IW{1'b0}};
                    state <= (ALGO == 0) ? S_MAC : S_P0;
                end
            end
            // ---------------------------------------------------------- running power
            S_P0: begin                  // issue x_new^2
                state <= S_P1;
            end
            S_P1: begin                  // issue x_dropped^2
                state <= S_MAC;
            end
            // ---------------------------------------------------------- y = w.x
            S_MAC: begin                 // issue w[i]*xv[i]
                if (i == L-1) begin
                    wc    <= 2'd1;       // drain: 2 cycles
                    nxt   <= S_YE;
                    state <= S_WAIT;
                end else begin
                    i <= i + 1'b1;
                end
            end
            // ---------------------------------------------------------- y, e
            S_YE: begin
                t_acc = accx;
                if (t_acc > ACCMAX) begin
                    t_acc = ACCMAX;
                    sat_flags[1] <= 1'b1;
                end else if (t_acc < ACCMIN) begin
                    t_acc = ACCMIN;
                    sat_flags[1] <= 1'b1;
                end
                t_ys = t_acc + HALFF;
                t_y  = t_ys >>> F;
                if (t_y > WMAX) begin
                    t_ysat = WMAX[W-1:0];
                    sat_flags[2] <= 1'b1;
                end else if (t_y < WMIN) begin
                    t_ysat = WMIN[W-1:0];
                    sat_flags[2] <= 1'b1;
                end else begin
                    t_ysat = t_y[W-1:0];
                end
                t_e = d_r - t_ysat;
                if (t_e > WMAX) begin
                    t_esat = WMAX[W-1:0];
                    sat_flags[3] <= 1'b1;
                end else if (t_e < WMIN) begin
                    t_esat = WMIN[W-1:0];
                    sat_flags[3] <= 1'b1;
                end else begin
                    t_esat = t_e[W-1:0];
                end
                y_out     <= t_ysat;
                e_out     <= t_esat;
                e_r       <= t_esat;
                out_valid <= 1'b1;
                i         <= {IW{1'b0}};
                if (ALGO == 2) begin
                    t_q   = pw + EPS_C;
                    m     <= t_esat;                       // sign-extends to AW
                    sh_r  <= bitlen(t_q) - F + K;
                    state <= S_UPD;
                end else begin
                    state <= S_MU;
                end
            end
            // ---------------------------------------------------------- MU_INT * e
            S_MU: begin                  // issue MU_INT*e, then drain (m / pm are written by the consume stage)
                wc    <= 2'd1;
                nxt   <= (ALGO == 0) ? S_UPD : S_MU2;
                state <= S_WAIT;
            end
            S_WAIT: begin
                if (wc == 2'd0) state <= nxt;
                else            wc    <= wc - 2'd1;
            end
            S_MU2: begin
                begin
                    // NLMS: set up the division  floor((2n+Q)/(2Q))
                    t_q   = pw + EPS_C;
                    t_num = pm;                            // sign-extend
                    t_num = t_num <<< (2*F - 10);
                    t_n2  = (t_num <<< 1) + t_q;
                    dsign <= (t_n2 < 0);
                    dvd   <= (t_n2 < 0) ? -t_n2 : t_n2;
                    dsr   <= {t_q, 1'b0};
                    rem_r <= {(NW+1){1'b0}};
                    quo   <= {NW{1'b0}};
                    cnt   <= {CW{1'b0}};
                    state <= S_DIV;
                end
            end
            // ---------------------------------------------------------- restoring divider
            S_DIV: begin
                if (cnt == NW) begin
                    // floor(N2/D2): positive N2 -> quo; negative N2 -> -(quo + (rem != 0))
                    t_qm = {1'b0, quo} + {{NW{1'b0}}, (dsign && (rem_r != {(NW+1){1'b0}}))};
                    t_qs = dsign ? -t_qm : t_qm;
                    if (t_qs > GMAX) begin
                        t_g = GMAX[GW-1:0];
                        sat_flags[4] <= 1'b1;
                    end else if (t_qs < GMIN) begin
                        t_g = GMIN[GW-1:0];
                        sat_flags[4] <= 1'b1;
                    end else begin
                        t_g = t_qs[GW-1:0];
                    end
                    m     <= t_g;                          // sign-extends to AW
                    i     <= {IW{1'b0}};
                    state <= S_UPD;
                end else begin
                    t_rn = {rem_r[NW-1:0], dvd[NW-1]};
                    dvd  <= {dvd[NW-2:0], 1'b0};
                    if (t_rn >= dsr) begin
                        rem_r <= t_rn - dsr;
                        quo   <= {quo[NW-2:0], 1'b1};
                    end else begin
                        rem_r <= t_rn;
                        quo   <= {quo[NW-2:0], 1'b0};
                    end
                    cnt <= cnt + 1'b1;
                end
            end
            // ---------------------------------------------------------- coefficient update
            S_UPD: begin                 // issue m*xv[i]; the update itself completes in the pipeline
                if (i == L-1) begin
                    wc    <= 2'd2;       // drain: 3 cycles until the last coefficient is written
                    nxt   <= S_IDLE;
                    state <= S_WAIT;
                end else begin
                    i <= i + 1'b1;
                end
            end
            default: state <= S_IDLE;
            endcase
        end
    end

endmodule
