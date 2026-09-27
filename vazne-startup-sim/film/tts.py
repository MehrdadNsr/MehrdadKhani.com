#!/usr/bin/env python3
"""Synthesize Persian narration per scene with edge-tts, measure durations, and write a timed scenes file.
Usage: python3 tts.py screenplay.json scenes_timed.json narration_dir [--voice fa-IR-FaridNeural] [--rate -6%] [--pad 1.4] [--lead 0.6]
Each scene may have: narration (str), min_dur (float, default from type), dur (used if no narration).
"""
import json, subprocess, sys, os, shutil, asyncio, re
sys.path.insert(0, '')
import edge_tts
FF = subprocess.check_output(['python3','-c','import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())']).decode().strip()
args = sys.argv[1:]
def opt(k, d):
    return args[args.index(k)+1] if k in args else d
src, dst, ndir = args[0], args[1], args[2]
VOICE = opt('--voice', 'fa-IR-FaridNeural'); RATE = opt('--rate', '-6%'); PAD = float(opt('--pad', '1.4')); LEAD = float(opt('--lead', '0.6'))
PITCH = opt('--pitch', '-2Hz')
os.makedirs(ndir, exist_ok=True)
MIN_DUR = {'title':6,'chapter':4.5,'text':4,'phone':6,'chat':7,'counter':5,'chart':7,'timeline':6,'checklist':6,'quote':6,'decision':8,'low':6,'year':8,'map':7,'montage':6,'end':9}
def dur_of(path):
    out = subprocess.run([FF,'-i',path,'-f','null','-'],capture_output=True,text=True).stderr
    m = re.findall(r'time=(\d+):(\d+):(\d+\.\d+)', out)
    if not m: return 0.0
    h,mi,s = m[-1]; return int(h)*3600+int(mi)*60+float(s)
async def synth(text, out_mp3, out_vtt):
    com = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)
    sub = edge_tts.SubMaker()
    with open(out_mp3, 'wb') as f:
        async for chunk in com.stream():
            if chunk['type'] == 'audio': f.write(chunk['data'])
            elif chunk['type'] in ('WordBoundary','SentenceBoundary'): sub.feed(chunk)
    with open(out_vtt,'w',encoding='utf-8') as f: f.write(sub.get_srt() if hasattr(sub,'get_srt') else '')
async def main():
    data = json.load(open(src, encoding='utf-8'))
    total = 0
    for i, s in enumerate(data['scenes']):
        nar = (s.get('narration') or '').strip()
        base = os.path.join(ndir, f"{i:02d}_{s.get('id','s')}")
        mind = s.get('min_dur', MIN_DUR.get(s['type'], 5))
        if nar:
            mp3 = base + '.mp3'
            if not (os.path.exists(mp3) and os.path.getsize(mp3) > 1000 and open(base+'.txt',encoding='utf-8').read()==nar if os.path.exists(base+'.txt') else False):
                for attempt in range(4):
                    try:
                        await synth(nar, mp3, base + '.srt'); break
                    except Exception as e:
                        print('retry', i, e); await asyncio.sleep(2*(attempt+1))
                open(base+'.txt','w',encoding='utf-8').write(nar)
            d = dur_of(mp3)
            s['tts'] = os.path.abspath(mp3); s['tts_dur'] = round(d, 2); s['tts_lead'] = LEAD
            s['dur'] = round(max(mind, LEAD + d + PAD, s.get('dur', 0) if s.get('force_dur') else 0), 2)
        else:
            s['dur'] = float(s.get('dur', mind))
        total += s['dur']
        print(f"{i:02d} {s['type']:9s} {s.get('id',''):12s} tts={s.get('tts_dur',0):6.2f}s dur={s['dur']:6.2f}s  {nar[:50]}")
    print(f"TOTAL {total:.1f}s = {total/60:.2f} min")
    json.dump(data, open(dst,'w',encoding='utf-8'), ensure_ascii=False, indent=1)
asyncio.run(main())
