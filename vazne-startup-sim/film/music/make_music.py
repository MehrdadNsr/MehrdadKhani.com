#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_music.py -- procedural cinematic "inspirational documentary" soundtrack bed.

Pure Python + numpy (no scipy). Renders a 48 kHz / stereo / 16-bit WAV designed to sit
UNDER narration: smooth, not busy, no harsh highs, 1-4 kHz speech band kept sparse.

Usage:
  python3 make_music.py --sections sections.json --out music.wav [--seed 7] [--bpm 92] [--stats]

sections.json: list of {"start": s, "end": s, "mood": <mood>, "intensity": 0..1}
  mood in: quiet, hopeful, tense, low, build, triumph, warm, end
"""
from __future__ import annotations

import argparse
import bisect
import json
import math
import sys
import time
import wave

import numpy as np

SR = 48000            # sample rate
CR = 200              # control rate for gain/mood curves (Hz)
F32 = np.float32
MOODS = ["quiet", "hopeful", "tense", "low", "build", "triumph", "warm", "end"]

# ----------------------------------------------------------------------------- music data
# Key: D minor. Voicings as MIDI note numbers, chosen for smooth voice leading.
CHORDS = {
    "Dm": dict(pad=[50, 53, 57, 62], top=69, bass=38, pluck=[62, 65, 69, 74, 77]),
    "Bb": dict(pad=[50, 53, 58, 62], top=65, bass=34, pluck=[62, 65, 70, 74, 77]),
    "F":  dict(pad=[48, 53, 57, 60], top=69, bass=41, pluck=[60, 65, 69, 72, 77]),
    "C":  dict(pad=[48, 52, 55, 60], top=67, bass=36, pluck=[60, 64, 67, 72, 76]),
}
PROG_MAIN = ["Dm", "Bb", "F", "C"]        # i - VI - III - VII
PROG_TRIUMPH = ["F", "C", "Dm", "Bb"]     # III - VII - i - VI (major lift)
PROG_SPARSE = ["Dm", "Bb"]                # i - VI

# Relative layer levels (pre-master; the master normalises the integrated RMS afterwards)
LEVEL = dict(pad=0.06, bass=0.045, pluck=0.11, shimmer=0.014, kick=0.08, boom=0.14,
             hat=0.015, riser=0.05, swell=0.10, wet=0.34)

ARP_A = [0, 2, 3, 2, 1, 2, 4, 3]
ARP_B = [0, 2, 3, 2, 1, 3, 4, 3]


def prog_for_mood(m):
    if m == "triumph":
        return PROG_TRIUMPH
    if m in ("quiet", "low", "end"):
        return PROG_SPARSE
    return PROG_MAIN


def mtof(m):
    return 440.0 * 2.0 ** ((m - 69) / 12.0)


# ----------------------------------------------------------------------------- DSP helpers
def good_size(n):
    """Smallest 5-smooth integer >= n (fast FFT length)."""
    n = int(n)
    if n <= 1:
        return 1
    best = 1 << (n - 1).bit_length()
    p5 = 1
    while p5 < best:
        p35 = p5
        while p35 < best:
            c = p35
            while c < n:
                c <<= 1
            if c < best:
                best = c
            p35 *= 3
        p5 *= 5
    return best


def rc(x):
    """Raised cosine 0..1 -> 0..1 (clipped)."""
    return 0.5 - 0.5 * np.cos(np.pi * np.clip(x, 0.0, 1.0))


def smoothstep(x, a, b):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def polyblep_saw(ph, dt):
    """Band-limited (PolyBLEP) sawtooth from phase in [0,1)."""
    y = 2.0 * ph - 1.0
    m1 = ph < dt
    t1 = ph[m1] / dt
    y[m1] -= (t1 + t1 - t1 * t1 - 1.0)
    m2 = ph > 1.0 - dt
    t2 = (ph[m2] - 1.0) / dt
    y[m2] -= (t2 * t2 + t2 + t2 + 1.0)
    return y


def H_lp(fc, order=1):
    return lambda f: (1.0 / (1.0 + 1j * f / fc)) ** order


def H_hp(fc, order=1):
    return lambda f: ((1j * f / fc) / (1.0 + 1j * f / fc)) ** order


def fft_apply(x, Hfunc, pad=8192):
    """Apply a frequency response H(f) to x along the last axis (FFT, zero-padded)."""
    n = x.shape[-1]
    nfft = good_size(n + pad)
    X = np.fft.rfft(x, nfft, axis=-1)
    f = np.fft.rfftfreq(nfft, 1.0 / SR)
    return np.fft.irfft(X * Hfunc(f), nfft, axis=-1)[..., :n]


def fir_convolve_full(x, h):
    """Overlap-add FFT convolution of a long 1-D signal with kernel h; returns len(x)+len(h)-1."""
    x = np.asarray(x, dtype=np.float64)
    n, m = len(x), len(h)
    L = max(32768, good_size(6 * m))
    nfft = good_size(L + m - 1)
    Hf = np.fft.rfft(h, nfft)
    y = np.zeros(n + m - 1, np.float64)
    for s in range(0, n, L):
        blk = x[s:s + L]
        yb = np.fft.irfft(np.fft.rfft(blk, nfft) * Hf, nfft)
        k = len(blk) + m - 1
        y[s:s + k] += yb[:k]
    return y


def exp_lp_kernel(fc, order=2, length=2048):
    """Causal 1-pole lowpass impulse response (cascaded `order` times), unity DC gain."""
    a = 1.0 - math.exp(-2.0 * math.pi * fc / SR)
    h = a * (1.0 - a) ** np.arange(length)
    out = h
    for _ in range(order - 1):
        out = np.convolve(out, h)[:length]
    return out / out.sum()


def noise_sweep(rng, n, f0, f1, order=2, channels=2, hp=None):
    """White noise with a lowpass whose cutoff sweeps f0 -> f1 across n samples
    (three fixed banks cross-faded, so it is fully vectorised)."""
    x = rng.standard_normal((channels, n))
    fm = math.sqrt(f0 * f1)
    p = 2.0 * np.arange(n) / max(1, n - 1)
    w = [np.clip(1 - p, 0, 1), np.clip(1 - np.abs(p - 1), 0, 1), np.clip(p - 1, 0, 1)]
    nfft = good_size(n + 8192)
    X = np.fft.rfft(x, nfft, axis=-1)
    f = np.fft.rfftfreq(nfft, 1.0 / SR)
    if hp is not None:
        X = X * H_hp(hp, 1)(f)
    y = np.zeros((channels, n))
    for wi, fc in zip(w, (f0, fm, f1)):
        y += np.fft.irfft(X * H_lp(fc, order)(f), nfft, axis=-1)[:, :n] * wi
    return y


# ----------------------------------------------------------------------------- sections / curves
def load_sections(path):
    with open(path) as fh:
        raw = json.load(fh)
    if not isinstance(raw, list) or not raw:
        raise SystemExit("sections.json must be a non-empty list")
    raw = sorted(raw, key=lambda s: float(s["start"]))
    out = []
    for s in raw:
        mood = str(s["mood"]).lower()
        if mood not in MOODS:
            raise SystemExit(f"unknown mood {mood!r}; expected one of {MOODS}")
        start = out[-1]["end"] if out else 0.0
        if abs(start - float(s["start"])) > 1e-6:
            print(f"[warn] section start {s['start']} adjusted to {start:.3f} (sections must be contiguous)",
                  file=sys.stderr)
        end = float(s["end"])
        if end <= start:
            continue
        inten = min(1.0, max(0.0, float(s.get("intensity", 0.5))))
        out.append(dict(start=start, end=end, mood=mood, intensity=inten))
    if not out:
        raise SystemExit("no usable sections")
    return out


def section_at(sections, t):
    for s in sections:
        if s["start"] <= t < s["end"]:
            return s
    return sections[-1]


def build_curves(sections, total, ramp=3.0):
    """Per-control-frame intensity + mood weights with raised-cosine ramps, and derived layer curves."""
    n = int(math.ceil(total * CR)) + 2
    t = np.arange(n) / CR
    K = len(sections)
    W = []
    for k, s in enumerate(sections):
        w = np.ones(n)
        ln = s["end"] - s["start"]
        if k > 0:
            p = sections[k - 1]
            rw = max(0.5, min(ramp, 0.8 * ln, 0.8 * (p["end"] - p["start"])))
            w *= rc((t - (s["start"] - rw / 2)) / rw)
        if k < K - 1:
            q = sections[k + 1]
            rw = max(0.5, min(ramp, 0.8 * ln, 0.8 * (q["end"] - q["start"])))
            w *= 1.0 - rc((t - (s["end"] - rw / 2)) / rw)
        W.append(w)
    Ws = np.sum(W, axis=0)
    Ws[Ws < 1e-9] = 1.0
    W = [w / Ws for w in W]
    I = np.zeros(n)
    mw = {m: np.zeros(n) for m in MOODS}
    for w, s in zip(W, sections):
        I += w * s["intensity"]
        mw[s["mood"]] += w
    c = {"I": I}
    for m in MOODS:
        c["w_" + m] = mw[m]
    g = lambda m: c["w_" + m]

    # --- derived per-layer control curves -------------------------------------------------
    c["pad_gain"] = (0.62 + 0.38 * I) * (1.0 - 0.2 * g("low"))
    b = np.clip((I - 0.1) / 0.8, 0, 1) - 0.15 * g("tense") - 0.10 * g("low") + 0.10 * g("triumph")
    c["bright"] = np.clip(b, 0.0, 1.0)             # 0 -> 400 Hz ... 1 -> 2500 Hz (log)
    p = 2.0 * c["bright"]
    c["bank0"] = np.clip(1 - p, 0, 1)
    c["bank1"] = np.clip(1 - np.abs(p - 1), 0, 1)
    c["bank2"] = np.clip(p - 1, 0, 1)
    c["voice3"] = smoothstep(I, 0.05, 0.40)
    c["voice4"] = smoothstep(I, 0.50, 0.85) * (1.0 - 0.5 * g("tense"))
    c["bass_gain"] = 0.75 + 0.25 * I
    c["bass_pulse"] = 0.55 * (g("build") + g("triumph"))
    lvl = dict(quiet=0.80, hopeful=0.80, tense=0.50, low=0.45, build=0.90, triumph=1.0, warm=0.80, end=0.75)
    c["pluck_gain"] = sum(g(m) * lvl[m] for m in MOODS) * (0.7 + 0.3 * I)
    c["shimmer_gain"] = smoothstep(I, 0.55, 0.85)
    c["drum_gain"] = I * (g("build") + g("triumph") + 0.35 * g("hopeful"))
    c["hat_gain"] = I * (0.6 * g("build") + 1.0 * g("triumph"))
    return c


def up(curve, start, n):
    """Upsample a control-rate curve to per-sample values for samples [start, start+n)."""
    pos = (start + np.arange(n, dtype=np.float64)) * (CR / SR)
    i0 = np.floor(pos).astype(np.int64)
    np.clip(i0, 0, len(curve) - 2, out=i0)
    fr = (pos - i0).astype(F32)
    return (curve[i0] * (1.0 - fr) + curve[i0 + 1] * fr).astype(F32)


def at(curve, t):
    i = int(round(t * CR))
    return float(curve[min(len(curve) - 1, max(0, i))])


# ----------------------------------------------------------------------------- harmonic grid
def make_slots(sections, total, beat):
    """Chord slots: 2 bars each; progression picked from the mood at the slot midpoint."""
    slot_len = 8.0 * beat
    nslots = max(1, int(math.ceil(total / slot_len - 1e-9)))
    slots = []
    sec_first = {}                                   # progression phase restarts at each section
    for j in range(nslots):
        s0 = j * slot_len
        s1 = min(total, s0 + slot_len)
        sec = section_at(sections, (s0 + s1) / 2)
        key = (sec["start"], sec["mood"])
        j0 = sec_first.setdefault(key, j)
        prog = prog_for_mood(sec["mood"])
        slots.append(dict(start=s0, end=s1, chord=prog[(j - j0) % len(prog)]))
    if len(slots) > 1 and slots[-1]["end"] - slots[-1]["start"] < 0.4 * slot_len:
        slots[-2]["end"] = total
        slots.pop()
    slots[-1]["chord"] = "Dm"                       # always resolve home
    if len(slots) > 1 and slots[-2]["chord"] == "Dm":
        slots[-2]["end"] = total
        slots.pop()
    return slots


def chord_at(slots, starts, t):
    i = bisect.bisect_right(starts, t) - 1
    return slots[max(0, i)]["chord"]


# ----------------------------------------------------------------------------- mixing bus
class Bus:
    def __init__(self, N):
        self.N = N
        self.main = np.zeros((2, N), F32)   # dry
        self.send = np.zeros((2, N), F32)   # reverb send

    def add(self, x, start, main=1.0, send=1.0):
        n = x.shape[-1]
        a = max(0, start)
        b = min(self.N, start + n)
        if b <= a:
            return
        seg = x[..., a - start:b - start]
        if seg.ndim == 1:
            seg = seg[None, :]
        if main:
            self.main[:, a:b] += seg * main
        if send:
            self.send[:, a:b] += seg * send


# ----------------------------------------------------------------------------- layers
def render_pad_and_shimmer(ctx, bus):
    """PAD: 3 detuned saw/tri unison voices per chord note, 1-pole LP (3 banks cross-faded by
    intensity), slow attack/release, chorus.  SHIMMER: octave-up triangle pad with tremolo."""
    N, c, slots, rng = ctx["N"], ctx["c"], ctx["slots"], ctx["rng"]
    pad = np.zeros((2, N), F32)
    ATT, REL, PRE = 1.5, 2.0, 0.6
    banks = (400.0, 1000.0, 2500.0)
    pans = ((0.85, 0.35), (0.62, 0.62), (0.35, 0.85))
    for sl in slots:
        t0 = max(0.0, sl["start"] - PRE)
        t1 = sl["end"] + REL
        a = int(t0 * SR)
        b = min(N, int(t1 * SR))
        n = b - a
        if n <= 0:
            continue
        tt = np.arange(n) / SR
        rel_at = sl["end"] - t0
        env = rc(tt / ATT) * (1.0 - rc((tt - rel_at) / REL))
        ch = CHORDS[sl["chord"]]
        notes = ch["pad"] + [ch["top"]]
        v3 = up(c["voice3"], a, n)
        v4 = up(c["voice4"], a, n)
        L = np.zeros(n)
        R = np.zeros(n)
        idx = np.arange(n, dtype=np.float64)
        for vi, m in enumerate(notes):
            f = mtof(m)
            vg = v3 if vi == 3 else (v4 if vi == 4 else None)
            for k, cents in enumerate((-6.0, 0.0, 6.0)):
                fk = f * 2.0 ** ((cents + rng.uniform(-1.5, 1.5)) / 1200.0)
                dt = fk / SR
                ph = (rng.random() + dt * idx) % 1.0
                w = 0.6 * polyblep_saw(ph, dt) + 0.4 * (2.0 * np.abs(2.0 * ph - 1.0) - 1.0)
                if vg is not None:
                    w *= vg
                gl, gr = pans[(k + vi) % 3]
                L += gl * w
                R += gr * w
        breath = 1.0 + 0.05 * np.sin(2 * np.pi * 0.08 * (tt + t0))
        X = np.stack([L, R]) * (env * breath)
        wts = [up(c["bank%d" % i], a, n) for i in range(3)]
        nfft = good_size(n + 8192)
        Xf = np.fft.rfft(X, nfft, axis=-1)
        f = np.fft.rfftfreq(nfft, 1.0 / SR)
        Y = np.zeros((2, n))
        for i, fc in enumerate(banks):
            if wts[i].max() < 1e-3:
                continue
            Y += np.fft.irfft(Xf * (1.0 / (1.0 + 1j * f / fc)), nfft, axis=-1)[:, :n] * wts[i]
        Y *= up(c["pad_gain"], a, n) * LEVEL["pad"]
        pad[:, a:b] += Y.astype(F32)

        # ---- shimmer (only when intensity is high) ----
        sg_cr = c["shimmer_gain"][int(a * CR / SR): int(b * CR / SR) + 2]
        if sg_cr.size and sg_cr.max() > 1e-3:
            sg = up(c["shimmer_gain"], a, n)
            envs = rc(tt / 2.5) * (1.0 - rc((tt - rel_at) / REL))
            Ls = np.zeros(n)
            Rs = np.zeros(n)
            for vi, m in enumerate(notes[1:]):
                f0 = mtof(m + 12)
                for k, cents in enumerate((-5.0, 5.0)):
                    fk = f0 * 2.0 ** ((cents + rng.uniform(-1.0, 1.0)) / 1200.0)
                    ph = (rng.random() + (fk / SR) * idx) % 1.0
                    w = 2.0 * np.abs(2.0 * ph - 1.0) - 1.0
                    gl, gr = (0.8, 0.45) if k == 0 else (0.45, 0.8)
                    Ls += gl * w
                    Rs += gr * w
            trem = 1.0 - 0.35 * (0.5 - 0.5 * np.cos(2 * np.pi * 0.28 * (tt + t0) + 0.7))
            Xs = np.stack([Ls, Rs]) * (envs * trem * sg * LEVEL["shimmer"])
            Xs = fft_apply(Xs, H_lp(3000.0, 2))
            bus.add(Xs, a, main=0.5, send=1.2)

    pad = chorus(pad)
    bus.add(pad, 0, main=1.0, send=1.0)


def chorus(x, base_ms=11.0, depth_ms=3.0, rate=0.25, mix=0.45, block=1 << 20):
    """Subtle stereo chorus: short modulated delay (8-14 ms), different LFO phase per channel."""
    N = x.shape[1]
    out = np.empty_like(x)
    for ch in range(2):
        xc = x[ch]
        phase0 = 0.0 if ch == 0 else np.pi / 2 + 0.3
        for s in range(0, N, block):
            e = min(N, s + block)
            n = np.arange(s, e, dtype=np.float64)
            lfo = np.sin(2 * np.pi * rate * n / SR + phase0)
            d = (base_ms + depth_ms * lfo) * (SR / 1000.0)
            idx = n - d
            i0 = np.floor(idx).astype(np.int64)
            fr = (idx - i0).astype(F32)
            np.clip(i0, 0, N - 2, out=i0)
            delayed = xc[i0] * (1.0 - fr) + xc[i0 + 1] * fr
            out[ch, s:e] = (xc[s:e] + mix * delayed) / (1.0 + mix)
    return out


def render_bass(ctx, bus):
    """SUB BASS: phase-continuous sine at chord root (octave below), beat pulse in build/triumph."""
    N, c, slots, beat = ctx["N"], ctx["c"], ctx["slots"], ctx["beat"]
    starts = np.array([sl["start"] for sl in slots])
    roots = np.array([mtof(CHORDS[sl["chord"]]["bass"]) for sl in slots])
    x = np.zeros(N, np.float64)
    ph = 0.0
    B = 1 << 20
    for s0 in range(0, N, B):
        s1 = min(N, s0 + B)
        n = s1 - s0
        t = np.arange(s0, s1, dtype=np.float64) / SR
        si = np.searchsorted(starts, t, side="right") - 1
        f = roots[np.clip(si, 0, len(roots) - 1)]
        phase = ph + 2 * np.pi * np.cumsum(f) / SR
        ph = phase[-1] % (2 * np.pi)
        bp = np.mod(t, beat)
        pulse = np.exp(-4.0 * bp / beat) * rc(bp / 0.015)
        depth = up(c["bass_pulse"], s0, n)
        env = (1.0 - depth) + depth * pulse
        tone = np.sin(phase) + 0.2 * np.sin(2.0 * phase)
        x[s0:s1] = tone * env * up(c["bass_gain"], s0, n) * LEVEL["bass"]
    kern = exp_lp_kernel(120.0, order=2, length=2048)
    y = fir_convolve_full(x, kern)[:N]
    bus.add(y.astype(F32), 0, main=1.0, send=0.0)


class PluckBank:
    """Additive piano-like tone templates (fundamental + 2nd/3rd/4th partials decaying faster)."""

    def __init__(self):
        self.cache = {}
        self.NL = int(2.0 * SR)
        self.tt = np.arange(self.NL) / SR
        self.shape = rc(self.tt / 0.004) * (1.0 - rc((self.tt - 1.7) / 0.3))

    def get(self, midi):
        if midi in self.cache:
            return self.cache[midi]
        f = mtof(midi)
        tt = self.tt
        scale = (f / 440.0) ** -0.25
        B = 0.0004

        def partial(nh, amp, tau):
            fn = nh * f * math.sqrt(1.0 + B * nh * nh)
            return amp * np.sin(2 * np.pi * fn * tt) * np.exp(-tt / (tau * scale))

        base = partial(1, 1.0, 0.5) * self.shape
        harm = (partial(2, 0.5, 0.30) + partial(3, 0.22, 0.20) + partial(4, 0.08, 0.14)) * self.shape
        self.cache[midi] = (base.astype(F32), harm.astype(F32))
        return self.cache[midi]


def pluck_events(ctx):
    """Deterministic note list: (time, midi, velocity, pan) per bar according to the bar's mood."""
    sections, slots, c, rng = ctx["sections"], ctx["slots"], ctx["c"], ctx["rng"]
    beat, bar, total = ctx["beat"], ctx["bar"], ctx["total"]
    starts = [sl["start"] for sl in slots]
    nbars = int(math.ceil(total / bar))
    ev = []

    def pan_alt(e):
        return (0.22 if e % 2 == 0 else -0.22) + rng.uniform(-0.08, 0.08)

    for k in range(nbars):
        tb = k * bar
        mood = section_at(sections, tb + bar / 2)["mood"]
        tones = CHORDS[chord_at(slots, starts, tb + 0.01)]["pluck"]
        I = at(c["I"], tb)
        if mood in ("hopeful", "build", "triumph"):
            pat = ARP_A if k % 2 == 0 else ARP_B
            for e in range(8):
                if mood == "hopeful" and e in (5, 7) and rng.random() < 0.5:
                    continue
                vel = 0.55 + 0.35 * I + rng.uniform(-0.12, 0.12)
                if e % 2 == 1:
                    vel *= 0.85
                ev.append((tb + e * beat / 2 + rng.uniform(-0.004, 0.004), tones[pat[e]], vel, pan_alt(e)))
        elif mood in ("quiet", "warm", "end"):
            if mood == "warm":
                hits = [(0, 3), (2, 1), (3, 2)] if k % 2 == 0 else [(0, 3), (2, 2)]
            elif mood == "quiet":
                hits = [(0, 3), (2, 1)] if k % 2 == 0 else [(0, 2)]
            else:
                hits = [(0, 3), (2, 1)] if k % 2 == 0 else [(0, 2)]
            for bt, ti in hits:
                vel = 0.45 + 0.30 * I + rng.uniform(-0.10, 0.10)
                ev.append((tb + bt * beat + rng.uniform(-0.006, 0.006), tones[ti], vel, pan_alt(bt)))
        elif mood == "tense":
            for e in range(8):
                vel = (0.50 if e % 2 == 0 else 0.32) + rng.uniform(-0.05, 0.05)
                midi = tones[2] if (k % 4) != 3 else tones[4]
                ev.append((tb + e * beat / 2 + rng.uniform(-0.003, 0.003), midi, vel, 0.15 * (1 if e % 2 else -1)))
        elif mood == "low":
            if k % 2 == 0:
                ev.append((tb + rng.uniform(-0.005, 0.005), tones[0], 0.40 + rng.uniform(-0.05, 0.05), 0.0))
    return ev


def render_plucks(ctx, bus):
    c, N = ctx["c"], ctx["N"]
    bank = PluckBank()
    for (t, midi, vel, pan) in pluck_events(ctx):
        g = at(c["pluck_gain"], t) * LEVEL["pluck"]
        if g < 1e-4:
            continue
        base, harm = bank.get(midi)
        x = (vel * g) * (base + (0.5 + 0.6 * vel) * harm)
        gl = math.sqrt(0.5 * (1.0 - pan))
        gr = math.sqrt(0.5 * (1.0 + pan))
        bus.add(np.stack([x * gl, x * gr]), int(t * SR), main=1.0, send=1.0)


def kick_template(f0=150.0, f1=45.0, sweep=0.06, tau=0.075, length=0.45):
    n = int(length * SR)
    tt = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-tt / (sweep / 3.0))
    ph = 2 * np.pi * np.cumsum(f) / SR
    env = rc(tt / 0.0015) * np.exp(-tt / tau) * (1.0 - rc((tt - (length - 0.06)) / 0.06))
    x = np.sin(ph) * env
    x = np.tanh(1.6 * x) / math.tanh(1.6)
    return (x / np.abs(x).max()).astype(F32)


def hat_template(rng):
    n = int(0.04 * SR)
    tt = np.arange(n) / SR
    x = rng.standard_normal(n)
    x = fft_apply(x, lambda f: H_hp(6000.0, 2)(f) * H_lp(12000.0, 2)(f))
    x *= rc(tt / 0.0015) * np.exp(-tt / 0.010) * (1.0 - rc((tt - 0.03) / 0.01))
    return (x / np.abs(x).max()).astype(F32)


def render_drums(ctx, bus):
    """Kick + soft hats (build/triumph, light kick in hopeful); reverse swell + boom into triumph."""
    sections, c, rng = ctx["sections"], ctx["c"], ctx["rng"]
    beat, bar, total = ctx["beat"], ctx["bar"], ctx["total"]
    kick = kick_template()
    boom = kick_template(f0=120.0, f1=38.0, sweep=0.15, tau=0.40, length=1.8)
    hats = [hat_template(rng) for _ in range(3)]
    nbars = int(math.ceil(total / bar))
    for k in range(nbars):
        tb = k * bar
        mood = section_at(sections, tb + bar / 2)["mood"]
        kicks, hatv = [], None
        if mood == "hopeful":
            kicks = [(0, 0.8)]
        elif mood == "build":
            kicks = [(0, 1.0), (2, 0.85)] + ([(3.5, 0.55)] if k % 2 == 1 else [])
            hatv = (0.45, 0.30)
        elif mood == "triumph":
            kicks = [(0, 1.0), (1, 0.7), (2, 0.9), (3, 0.7)] + ([(3.5, 0.5)] if k % 4 == 3 else [])
            hatv = (0.55, 0.35)
        for bt, v in kicks:
            t = tb + bt * beat
            g = at(c["drum_gain"], t)
            if g < 1e-3:
                continue
            bus.add(kick * F32(v * g * LEVEL["kick"]), int(t * SR), main=1.0, send=0.15)
        if hatv:
            for e in range(8):
                t = tb + e * beat / 2 + rng.uniform(-0.003, 0.003)
                g = at(c["hat_gain"], t)
                if g < 1e-3:
                    continue
                v = (hatv[0] if e % 2 == 0 else hatv[1]) * rng.uniform(0.85, 1.15)
                h = hats[int(rng.integers(3))] * F32(v * g * LEVEL["hat"])
                bus.add(np.stack([h * 0.9, h * 1.1]), int(t * SR), main=1.0, send=0.8)
    # reverse swell + boom landing exactly on a boundary into "triumph"
    for k in range(1, len(sections)):
        if sections[k]["mood"] == "triumph" and sections[k - 1]["mood"] != "triumph":
            tb = sections[k]["start"]
            amp = sections[k]["intensity"]
            n = int(2.0 * SR)
            a = int(tb * SR) - n
            tt = np.arange(n) / SR
            env = (tt / 2.0) ** 2.2 * (1.0 - rc((tt - 1.99) / 0.01))
            x = noise_sweep(rng, n, 250.0, 2500.0, order=2, channels=2, hp=150.0)
            bus.add(x * (env * amp * LEVEL["swell"]), a, main=0.7, send=1.0)
            bus.add(boom * F32(amp * LEVEL["boom"]), int(tb * SR), main=1.0, send=0.3)


def render_risers(ctx, bus):
    """RISER: very subtle filtered-noise rise across tense/build sections."""
    sections, rng = ctx["sections"], ctx["rng"]
    for s in sections:
        if s["mood"] not in ("tense", "build"):
            continue
        T = s["end"] - s["start"]
        n = int(T * SR)
        if n < SR:
            continue
        a = int(s["start"] * SR)
        tt = np.arange(n) / SR
        env = (tt / T) ** 2 * rc(tt / 2.0) * (1.0 - rc((tt - (T - 0.8)) / 0.8))
        amp = LEVEL["riser"] * (0.5 + 0.5 * s["intensity"])
        x = noise_sweep(rng, n, 300.0, 3000.0, order=2, channels=2, hp=200.0)
        bus.add(x * (env * amp), a, main=0.8, send=1.0)


# ----------------------------------------------------------------------------- master
def reverb_ir(rng, rt60=2.2, predelay=0.02):
    """Synthetic stereo IR: exponentially decaying noise, HF decays faster; energy-normalised."""
    n = int(rt60 * SR)
    tt = np.arange(n) / SR
    tau = rt60 / 6.91
    pd = int(predelay * SR)
    ir = np.zeros((2, pd + n))
    for ch in range(2):
        noise = rng.standard_normal(n)
        low = fft_apply(noise, lambda f: H_lp(1500.0, 1)(f) * H_hp(120.0, 2)(f)) * np.exp(-tt / tau)
        high = fft_apply(noise, lambda f: H_hp(1500.0, 1)(f) * H_lp(5000.0, 2)(f)) * np.exp(-tt / (0.55 * tau))
        x = (low + 0.7 * high) * rc(tt / 0.005)
        ir[ch, pd:] = x
    e = math.sqrt(float((ir ** 2).sum(axis=1).mean()))
    return ir / e


def master_eq_kernel(m=8191):
    """Linear-phase FIR: -3 dB dip @3 kHz (1 oct wide), soft LP (-3 dB @12 kHz), HP @25 Hz."""
    nfft = 65536
    f = np.fft.rfftfreq(nfft, 1.0 / SR)
    fs = np.maximum(f, 1.0)
    dip = 1.0 - (1.0 - 10 ** (-3 / 20)) * np.exp(-0.5 * (np.log2(fs / 3000.0) / 0.4247) ** 2)
    lp = 1.0 / np.sqrt(1.0 + (f / 12000.0) ** 8)
    hp = (fs / 25.0) ** 2 / np.sqrt(1.0 + (fs / 25.0) ** 4)
    hp[0] = 0.0
    H = dip * lp * hp
    h = np.fft.irfft(H, nfft)
    h = np.roll(h, m // 2)[:m]
    h *= np.hanning(m)
    return h


def soft_limit_inplace(x, ceiling=10 ** (-1 / 20), knee=0.6, block=1 << 21):
    for ch in range(x.shape[0]):
        for s in range(0, x.shape[1], block):
            blk = x[ch, s:s + block]
            ax = np.abs(blk)
            m = ax > knee
            if m.any():
                over = ax[m]
                blk[m] = np.sign(blk[m]) * (knee + (ceiling - knee) * np.tanh((over - knee) / (ceiling - knee)))


def rms_of(x):
    xr = x.ravel()
    return math.sqrt(float(np.dot(xr, xr)) / xr.size)


def master(bus, rng, N, verbose=True):
    t0 = time.time()
    ir = reverb_ir(rng)
    mix = bus.main.astype(np.float64)
    for ch in range(2):
        mix[ch] += LEVEL["wet"] * fir_convolve_full(bus.send[ch], ir[ch])[:N]
    if verbose:
        print(f"  reverb            {time.time() - t0:6.1f}s", file=sys.stderr)
    t0 = time.time()
    h = master_eq_kernel()
    d = len(h) // 2
    for ch in range(2):
        mix[ch] = fir_convolve_full(mix[ch], h)[d:d + N]
    mix -= mix.mean(axis=1, keepdims=True)
    if verbose:
        print(f"  master EQ         {time.time() - t0:6.1f}s", file=sys.stderr)
    fi, fo = int(2.0 * SR), int(4.0 * SR)
    fi, fo = min(fi, N // 2), min(fo, N // 2)
    mix[:, :fi] *= rc(np.arange(fi) / fi)
    mix[:, N - fo:] *= 1.0 - rc(np.arange(fo) / fo)
    target = 10 ** (-20 / 20)
    for _ in range(2):
        r = rms_of(mix)
        if r > 0:
            mix *= target / r
        soft_limit_inplace(mix)
    return mix


def write_wav(path, x, seed=12345):
    """16-bit PCM stereo with TPDF dither."""
    rng = np.random.default_rng(seed)
    N = x.shape[1]
    out = np.empty((N, 2), np.int16)
    B = 1 << 20
    for s in range(0, N, B):
        e = min(N, s + B)
        v = x[:, s:e].T * 32767.0
        v += rng.random(v.shape) - rng.random(v.shape)
        np.clip(np.rint(v), -32768, 32767, out=v)
        out[s:e] = v.astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(out.tobytes())


# ----------------------------------------------------------------------------- render
def section_rms_rows(x, sections):
    rows = []
    for s in sections:
        seg = x[:, int(s["start"] * SR):int(s["end"] * SR)]
        r = rms_of(seg) if seg.size else 0.0
        pk = float(np.abs(seg).max()) if seg.size else 0.0
        rows.append((20 * math.log10(max(r, 1e-9)), 20 * math.log10(max(pk, 1e-9))))
    return rows


def render(sections, seed=7, bpm=92.0, stats=False, verbose=True):
    total = sections[-1]["end"]
    N = int(round(total * SR))
    beat = 60.0 / bpm
    rng = np.random.default_rng(seed)
    c = build_curves(sections, total)
    slots = make_slots(sections, total, beat)
    ctx = dict(sections=sections, total=total, N=N, beat=beat, bar=4 * beat, rng=rng, c=c, slots=slots)
    if verbose:
        print(f"render: {total:.1f}s, {N} samples, bpm {bpm}, seed {seed}", file=sys.stderr)
        print("chords: " + " ".join(f"{sl['chord']}@{sl['start']:.1f}" for sl in slots), file=sys.stderr)
    bus = Bus(N)
    layers = [("pad+shimmer", render_pad_and_shimmer), ("bass", render_bass), ("plucks", render_plucks),
              ("drums", render_drums), ("riser", render_risers)]
    table = {}
    for name, fn in layers:
        t0 = time.time()
        if stats:
            tmp = Bus(N)
            fn(ctx, tmp)
            table[name] = section_rms_rows(tmp.main, sections)
            bus.main += tmp.main
            bus.send += tmp.send
            del tmp
        else:
            fn(ctx, bus)
        if verbose:
            print(f"  {name:<17} {time.time() - t0:6.1f}s", file=sys.stderr)
    mix = master(bus, rng, N, verbose)
    if stats:
        table["MIX(final)"] = section_rms_rows(mix, sections)
        names = list(table)
        print("\nper-layer RMS/peak (dBFS) per section  [layers pre-master; MIX after normalisation]")
        print(f"{'section':<26}" + "".join(f"{n:>14}" for n in names))
        for i, s in enumerate(sections):
            lab = f"{s['start']:5.0f}-{s['end']:<5.0f} {s['mood']:<8}{s['intensity']:.2f}"
            print(f"{lab:<26}" + "".join(f"{table[n][i][0]:7.1f}/{table[n][i][1]:6.1f}" for n in names))
    return mix


def main(argv=None):
    ap = argparse.ArgumentParser(description="Procedural cinematic soundtrack bed (numpy only).")
    ap.add_argument("--sections", required=True, help="JSON list of {start,end,mood,intensity}")
    ap.add_argument("--out", required=True, help="output WAV (48 kHz stereo 16-bit)")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--bpm", type=float, default=92.0)
    ap.add_argument("--stats", action="store_true", help="print per-layer/per-section RMS table")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)
    t0 = time.time()
    sections = load_sections(a.sections)
    mix = render(sections, seed=a.seed, bpm=a.bpm, stats=a.stats, verbose=not a.quiet)
    write_wav(a.out, mix)
    peak = float(np.abs(mix).max())
    print(f"wrote {a.out}: {mix.shape[1] / SR:.2f}s, peak {20 * math.log10(max(peak, 1e-9)):.2f} dBFS, "
          f"RMS {20 * math.log10(rms_of(mix)):.2f} dBFS, {time.time() - t0:.1f}s", file=sys.stderr)


if __name__ == "__main__":
    main()
