"""Evaluation metrics. The clean signal s and true path h are known, so everything is exact.

residual r = e - s,  noise input nz = d - s.
  noise reduction (dB)  = 10log10( mean(nz^2) / mean(r^2) )   (final window = last 25 % of run)
  NR curve              = same ratio of 256-sample moving averages (amplitude-invariant)
  nr_avg (dB)           = time-average of the NR curve (log domain; used for step-size tuning)
  settling time (ms)    = time from start until the (256-sample smoothed) coefficient-error curve stays
                          <= steady state + 3 dB; steady state = mean of that curve over the last 20 % of
                          the segment. (The NR curve itself fluctuates +-5 dB from noise power alone, so it
                          is not usable for a threshold test; coefficient error is smoother.)
  tracking time (ms)    = same, measured from each abrupt event to the next event/end; mean over events
                          (0 = the event did not disturb the coefficients by more than 3 dB).
  coefficient error(dB) = 10log10(||w - h||^2 / ||h||^2), h zero-padded to L; smoothed; mean over final window.
Caveat: steady state is per run/segment, so a run that never converges can still 'settle' quickly
relative to its own poor plateau -> always read times together with nr_final / coef_db.
"""
import numpy as np

FS = 8000


def smooth(p, win=256):
    return np.convolve(p, np.ones(win) / win)[:len(p)]


def curves(sc, e, W, L, win=256):
    n = len(e)
    pn, pr = smooth((sc.d - sc.s) ** 2, win), smooth((e - sc.s) ** 2, win)
    H = np.zeros((n, L))
    for a, h in sc.h_segs:
        H[a:, :len(h)] = h
    return dict(nr=10 * np.log10((pn + 1e-20) / (pr + 1e-20)),
                res_db=10 * np.log10(pr + 1e-20), noise_db=10 * np.log10(pn + 1e-20),
                coef_db=10 * np.log10(smooth(((W - H) ** 2).sum(1) / ((H ** 2).sum(1) + 1e-20), win) + 1e-20))


def evaluate(sc, e, W, L, win=256):
    n = len(e)
    if not (np.all(np.isfinite(e)) and np.all(np.isfinite(W))):
        return dict(nr_final=-100.0, nr_all=-100.0, nr_avg=-100.0, settle_ms=np.inf, track_ms=np.inf,
                    coef_db=0.0, diverged=1)
    c = curves(sc, e, W, L, win)
    res, nz = e - sc.s, sc.d - sc.s
    nr = lambda sl: float(10 * np.log10(np.mean(nz[sl] ** 2) / (np.mean(res[sl] ** 2) + 1e-20)))
    fin = slice(int(.75 * n), n)
    edges, times = [0] + list(sc.events) + [n], []
    for a, b in zip(edges[:-1], edges[1:]):
        seg = c["coef_db"][a:b]
        ss = seg[int(.8 * len(seg)):].mean()
        bad = np.flatnonzero(seg > ss + 3.0)
        t = 0 if bad.size == 0 else bad[-1] + 1
        times.append(np.inf if t >= len(seg) else 1000.0 * t / FS)
    return dict(nr_final=nr(fin), nr_all=nr(slice(0, n)), nr_avg=float(c["nr"].mean()), settle_ms=times[0],
                track_ms=float(np.mean(times[1:])) if len(times) > 1 else np.nan,
                coef_db=float(c["coef_db"][fin].mean()), diverged=0)


def compute_mse(clean, processed):
    """Mean Square Error between reference signal and processed signal."""
    diff = np.asarray(clean) - np.asarray(processed)
    return float(np.mean(diff ** 2))


def compute_fixed_vs_float_error(e_float, e_fixed, W=16):
    """Calculate numerical discrepancy between fixed-point and floating-point outputs.

    Metrics:
      - mae: Maximum Absolute Error
      - mse: Mean Squared Error between the two outputs
      - snr_deg_db: Signal-to-Quantization-Noise Ratio 10*log10(P_float / P_diff)
      - max_err_lsb: Error magnitude measured in fixed-point LSBs (1 LSB = 2^-(W-1))
    """
    ef = np.asarray(e_float, dtype=np.float64)
    ex = np.asarray(e_fixed, dtype=np.float64)
    diff = ex - ef
    p_float = np.mean(ef ** 2)
    p_diff = np.mean(diff ** 2)
    lsb = 2.0 ** (-(W - 1))
    return {
        "mae": float(np.max(np.abs(diff))),
        "mse": float(p_diff),
        "sqnr_db": float(10.0 * np.log10((p_float + 1e-20) / (p_diff + 1e-20))),
        "max_err_lsb": float(np.max(np.abs(diff)) / lsb)
    }


def compute_snr(signal, noise):
    """Power SNR in dB."""
    ps = np.mean(np.asarray(signal) ** 2)
    pn = np.mean(np.asarray(noise) ** 2)
    return float(10.0 * np.log10((ps + 1e-20) / (pn + 1e-20)))

