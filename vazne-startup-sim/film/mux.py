#!/usr/bin/env python3
"""Mix narration clips (at scene starts) with a music bed (ducked under the voice) and mux onto the silent video.
Usage: python3 mux.py scenes_timed.json video_silent.mp4 music.wav|none out.mp4 [--music-db -13] [--voice-db 1.5]
"""
import json, subprocess, sys, os
FF = subprocess.check_output(['python3','-c','import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())']).decode().strip()
a = sys.argv[1:]
def opt(k, d): return a[a.index(k)+1] if k in a else d
scenes, video, music, out = a[0], a[1], a[2], a[3]
MDB = float(opt('--music-db', '-11')); VDB = float(opt('--voice-db', '3'))
has_music = music and music != 'none' and os.path.exists(music)
data = json.load(open(scenes, encoding='utf-8'))
t = 0.0; clips = []
for s in data['scenes']:
    s['start'] = t; t += s['dur']
    if s.get('tts') and os.path.exists(s['tts']): clips.append((s['start'] + s.get('tts_lead', 0.6), s['tts']))
total = t
inputs = ['-i', video] + (['-i', music] if has_music else [])
for _, p in clips: inputs += ['-i', p]
base = 2 if has_music else 1
fc, labels = [], []
for k, (st, p) in enumerate(clips):
    ms = int(st * 1000)
    fc.append(f"[{base+k}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,volume={VDB}dB,adelay={ms}|{ms}[v{k}]")
    labels.append(f"[v{k}]")
if labels:
    fc.append(''.join(labels) + f"amix=inputs={len(labels)}:normalize=0:dropout_transition=0,apad=whole_dur={total:.3f},atrim=0:{total:.3f}[voice]")
else:
    fc.append(f"anullsrc=r=48000:cl=stereo,atrim=0:{total:.3f}[voice]")
if has_music:
    fc.append(f"[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,volume={MDB}dB,apad=whole_dur={total:.3f},atrim=0:{total:.3f}[m]")
    fc.append("[voice]asplit=2[vo][vk]")
    fc.append("[m][vk]sidechaincompress=threshold=0.015:ratio=5:attack=60:release=1000:makeup=1[md]")
    fc.append("[md][vo]amix=inputs=2:normalize=0:dropout_transition=0[mixed]")
    fc.append("[mixed]loudnorm=I=-16:TP=-1.5:LRA=11[aout]")
else:
    fc.append("[voice]loudnorm=I=-16:TP=-1.5:LRA=11[aout]")
cmd = [FF, '-y', '-hide_banner', '-loglevel', 'error'] + inputs + ['-filter_complex', ';'.join(fc), '-map', '0:v', '-map', '[aout]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-shortest', out]
subprocess.check_call(cmd)
print('wrote', out, 'total', round(total, 2), 'clips', len(clips), 'music', has_music)
