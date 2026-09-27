#!/usr/bin/env python3
"""verify_music.py -- numeric QA for a rendered bed.
Usage: python3 verify_music.py music.wav sections.json [--bpm 92]
"""
import argparse, json, math, sys, wave
import numpy as np

SR = 48000


def read_wav(path):
    with wave.open(path, "rb") as w:
        assert w.getframerate() == SR, w.getframerate()
        assert w.getnchannels() == 2 and w.getsampwidth() == 2
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return data.reshape(-1, 2).T.astype(np.float64) / 32768.0


def db(v):
    return 20 * math.log10(max(float(v), 1e-12))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wav"); ap.add_argument("sections"); ap.add_argument("--bpm", type=float, default=92.0)
    a = ap.parse_args()
    x = read_wav(a.wav)
    secs = json.load(open(a.sections))
    N = x.shape[1]; dur = N / SR
    ok = True
    print(f"file: {a.wav}  duration {dur:.2f}s  ({N} frames, 48 kHz stereo 16-bit)")

    nan = int(np.isnan(x).sum()) + int(np.isinf(x).sum())
    print(f"NaN/Inf samples : {nan}  -> {'OK' if nan == 0 else 'FAIL'}"); ok &= nan == 0
    peak = np.abs(x).max()
    print(f"peak            : {db(peak):7.2f} dBFS  -> {'OK' if db(peak) <= -1.0 + 0.05 else 'FAIL'} (<= -1 dBFS)"); ok &= db(peak) <= -0.95
    rms = math.sqrt(float(np.mean(x ** 2)))
    print(f"integrated RMS  : {db(rms):7.2f} dBFS  -> {'OK' if -22 <= db(rms) <= -18 else 'FAIL'} (-22..-18)"); ok &= -22 <= db(rms) <= -18
    dc = x.mean(axis=1)
    print(f"DC offset L/R   : {dc[0]:+.6f} / {dc[1]:+.6f}  -> {'OK' if np.abs(dc).max() < 1e-3 else 'FAIL'} (<1e-3)"); ok &= np.abs(dc).max() < 1e-3
    print(f"L/R RMS balance : {db(math.sqrt(np.mean(x[0]**2))):.2f} / {db(math.sqrt(np.mean(x[1]**2))):.2f} dBFS")

    # ---- click check ------------------------------------------------------------------
    d = np.abs(np.diff(x, axis=1)).max(axis=0)          # per-sample max over channels
    beat = 60.0 / a.bpm
    excl = np.zeros(N - 1, bool)
    w = int(0.015 * SR)
    for t in np.arange(0, dur, beat):                    # kick onsets sit on the beat grid
        i = int(t * SR); excl[max(0, i - 2):i + w] = True
    for s in secs:                                       # booms on section boundaries
        i = int(s["start"] * SR); excl[max(0, i - 2):i + w] = True
    dmax_all = d.max(); imax_all = int(d.argmax())
    dmax = d[~excl].max(); imax = int(np.flatnonzero(~excl)[d[~excl].argmax()])
    print(f"max |x[n]-x[n-1]| overall            : {dmax_all:.4f} at {imax_all / SR:8.3f}s")
    print(f"max |x[n]-x[n-1]| outside kick onsets : {dmax:.4f} at {imax / SR:8.3f}s  -> {'OK' if dmax < 0.1 else 'FAIL'} (<0.1)")
    ok &= dmax < 0.1
    # discontinuity detector: a step that is far above the local high-frequency activity
    win = int(0.02 * SR)
    nb = (N - 1) // win
    blk = d[:nb * win].reshape(nb, win)
    med = np.median(blk, axis=1)
    thr = np.maximum(0.004, 12.0 * med)
    flags = blk > thr[:, None]
    nflag = int(flags.sum())
    ratio = blk / np.maximum(med[:, None], 1e-6)
    ri = int(ratio.argmax()); rb, rj = divmod(ri, win)
    print(f"click detector (|diff| > max(0.004, 12x local median)): {nflag} samples flagged  "
          f"-> {'OK' if nflag == 0 else 'CHECK'}; worst ratio {ratio.max():.1f} at {(rb * win + rj) / SR:.3f}s "
          f"(|diff|={blk[rb, rj]:.4f})")
    if nflag:
        idx = np.flatnonzero(flags.ravel())[:10]
        print("   first flagged times (s):", ", ".join(f"{i / SR:.3f}" for i in idx))

    # ---- per-section table --------------------------------------------------------------
    print("\nper-section levels (dBFS):")
    print(f"{'start':>6} {'end':>6}  {'mood':<8} {'inten':>5}  {'RMS':>7} {'peak':>7}  {'crest':>5}  {'1-4k share':>10}")
    for s in secs:
        seg = x[:, int(s["start"] * SR):int(s["end"] * SR)]
        r = math.sqrt(float(np.mean(seg ** 2))); p = np.abs(seg).max()
        share = band_share(seg)
        print(f"{s['start']:6.0f} {s['end']:6.0f}  {s['mood']:<8} {s['intensity']:5.2f}  {db(r):7.1f} {db(p):7.1f}  "
              f"{db(p) - db(r):5.1f}  {100 * share[2]:9.1f}%")

    # ---- spectral balance -----------------------------------------------------------------
    sh = band_share(x)
    names = ["20-200", "200-1k", "1k-4k", "4k-12k", "12k+"]
    print("\nenergy share by band (whole file): " + ", ".join(f"{n}: {100 * v:.1f}%" for n, v in zip(names, sh)))
    print("\nRESULT:", "ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
    return 0 if ok else 1


def band_share(x, nfft=32768):
    """Average Welch power spectrum -> fraction of energy in bands."""
    win = np.hanning(nfft)
    hop = nfft
    acc = np.zeros(nfft // 2 + 1)
    cnt = 0
    for ch in range(x.shape[0]):
        for s in range(0, x.shape[1] - nfft, hop):
            X = np.fft.rfft(x[ch, s:s + nfft] * win)
            acc += np.abs(X) ** 2; cnt += 1
    if cnt == 0:
        return [0.0] * 5
    f = np.fft.rfftfreq(nfft, 1 / SR)
    tot = acc[(f >= 20)].sum() + 1e-30
    edges = [(20, 200), (200, 1000), (1000, 4000), (4000, 12000), (12000, 24000)]
    return [acc[(f >= lo) & (f < hi)].sum() / tot for lo, hi in edges]


if __name__ == "__main__":
    sys.exit(main())
