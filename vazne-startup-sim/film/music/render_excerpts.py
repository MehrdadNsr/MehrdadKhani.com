#!/usr/bin/env python3
"""render_excerpts.py -- 20-second audition excerpt of every mood (same seed/bpm as the main render)."""
import argparse, json, math, sys, wave
import numpy as np
import make_music as mm

DEMO_INTENSITY = dict(quiet=0.2, hopeful=0.4, tense=0.5, low=0.25, build=0.65, triumph=0.9, warm=0.5, end=0.3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--bpm", type=float, default=92.0)
    ap.add_argument("--length", type=float, default=20.0)
    ap.add_argument("--prefix", default="excerpt_")
    a = ap.parse_args()
    files = []
    for mood in mm.MOODS:
        secs = [dict(start=0.0, end=a.length, mood=mood, intensity=DEMO_INTENSITY[mood])]
        path = f"{a.prefix}{mood}.wav"
        json.dump(secs, open(f"{a.prefix}{mood}.json", "w"))
        mix = mm.render(secs, seed=a.seed, bpm=a.bpm, verbose=False)
        mm.write_wav(path, mix)
        pk = 20 * math.log10(max(float(np.abs(mix).max()), 1e-9))
        r = 20 * math.log10(mm.rms_of(mix))
        print(f"{path:<22} {a.length:5.1f}s  mood={mood:<8} intensity={DEMO_INTENSITY[mood]:.2f}  peak {pk:6.2f} dBFS  RMS {r:6.2f} dBFS")
        files.append(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
