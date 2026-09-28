#!/usr/bin/env python3
"""End-to-end film build.
Usage: python3 build_film.py screenplay.json OUT_DIR [--skip-render] [--skip-music] [--fps 30] [--jpegq 88] [--stills-only]
Steps: validate → tts (timing) → music sections → music → render silent → mux → 720p preview → stills.
"""
import json, os, sys, subprocess, shutil, re
HERE = os.path.dirname(os.path.abspath(__file__))
MUSIC_DIR = os.path.join(os.path.dirname(HERE), 'music')
FF = subprocess.check_output(['python3','-c','import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())']).decode().strip()
a = sys.argv[1:]
def opt(k, d): return a[a.index(k)+1] if k in a else d
src, out = a[0], a[1]
FPS = opt('--fps','30'); JQ = opt('--jpegq','88')
os.makedirs(out, exist_ok=True)
ENV = dict(os.environ, SSL_CERT_FILE='/root/.ccr/ca-bundle.crt', NODE_PATH='/opt/node22/lib/node_modules')

REQ = {
 'title': ['title'], 'chapter': ['num','title'], 'text': ['lines'], 'montage': ['items'], 'counter': ['items'], 'chart': ['title','points'],
 'timeline': ['items'], 'checklist': ['items'], 'quote': ['text'], 'decision': ['question','options'], 'low': ['lines'], 'year': ['year','headline','tiles'],
 'map': ['nodes'], 'chat': ['messages'], 'phone': ['screen'], 'end': ['title'],
}
MOOD_MAP = {'quiet':'quiet','hopeful':'hopeful','tense':'tense','low':'low','build':'build','triumph':'triumph','warm':'warm','end':'end','ai':'hopeful'}
INT = {'quiet':0.2,'hopeful':0.38,'tense':0.46,'low':0.2,'build':0.56,'triumph':0.72,'warm':0.46,'end':0.28}

def validate(data):
    errs = []; ids = set()
    for i, s in enumerate(data['scenes']):
        t = s.get('type'); p = s.get('params') or {}
        if t not in REQ: errs.append(f"scene {i} {s.get('id')}: unknown type {t}"); continue
        for k in REQ[t]:
            if k not in p: errs.append(f"scene {i} {s.get('id')} ({t}): missing param {k}")
        if s.get('id') in ids: s['id'] = f"{s.get('id')}_{i}"
        ids.add(s.get('id'))
        if s.get('mood') not in MOOD_MAP: s['mood'] = 'hopeful'
        if t == 'year' and len(p.get('tiles', [])) != 4: errs.append(f"scene {i} year: tiles must be 4 (got {len(p.get('tiles',[]))})")
        if t == 'decision':
            for o in p.get('options', []): o.setdefault('p', 0.33)
        if t in ('timeline','checklist'):
            for it in p.get('items', []): it.setdefault('state','done')
        if t == 'phone' and p.get('screen') not in ('log','playstore','chat','scan','notif','stats'): errs.append(f"scene {i} phone: bad screen {p.get('screen')}")
    words = sum(len((s.get('narration') or '').split()) for s in data['scenes'])
    print(f"validate: {len(data['scenes'])} scenes, narration {words} words, errors: {len(errs)}")
    for e in errs: print('  -', e)
    return errs

data = json.load(open(src, encoding='utf-8'))
if 'scenes' not in data and 'final' in data: data = data['final']
data.setdefault('fps', int(FPS))
errs = validate(data)
if any('unknown type' in e or 'missing param' in e for e in errs) and '--force' not in a:
    print('fix the errors above (or pass --force)'); sys.exit(2)
clean = os.path.join(out, 'screenplay_clean.json'); json.dump(data, open(clean,'w',encoding='utf-8'), ensure_ascii=False, indent=1)

# 1) TTS + timing
timed = os.path.join(out, 'scenes_timed.json')
subprocess.check_call(['python3', os.path.join(HERE,'tts.py'), clean, timed, os.path.join(out,'narration')], env=ENV)
T = json.load(open(timed, encoding='utf-8'))
total = sum(s['dur'] for s in T['scenes']); print(f"film length: {total:.1f}s = {total/60:.2f} min")

# 2) music sections from moods
secs = []; t = 0.0
for s in T['scenes']:
    m = MOOD_MAP.get(s.get('mood'),'hopeful'); yr = s.get('year') or 0
    inten = min(0.75, INT[m] + 0.015*yr)
    if secs and secs[-1]['mood'] == m and abs(secs[-1]['intensity']-inten) < 0.08: secs[-1]['end'] = round(t + s['dur'], 3)
    else: secs.append({'start': round(t,3), 'end': round(t+s['dur'],3), 'mood': m, 'intensity': round(inten,2)})
    t += s['dur']
# force the last section to 'end' mood
if secs[-1]['mood'] != 'end': secs[-1]['mood'] = 'end'; secs[-1]['intensity'] = 0.3
# merge very short sections (<6s) into previous
merged = []
for sec in secs:
    if merged and (sec['end']-sec['start']) < 6: merged[-1]['end'] = sec['end']
    else: merged.append(sec)
sections = os.path.join(out, 'music_sections.json'); json.dump(merged, open(sections,'w'), indent=1)
print('music sections:', len(merged))
music = os.path.join(out, 'music.wav')
if '--skip-music' not in a:
    subprocess.check_call(['python3', os.path.join(MUSIC_DIR,'make_music.py'), '--sections', sections, '--out', music, '--seed', '11', '--bpm', '72', '--quiet'])

if '--stills-only' in a:
    subprocess.check_call(['node', os.path.join(HERE,'render.js'), timed, '/dev/null', '--stills', os.path.join(out,'stills'), '--frac', '0.72'], env=ENV); sys.exit(0)
if '--skip-render' in a: sys.exit(0)
# 3) render silent master
silent = os.path.join(out, 'vazne-10-years-SILENT-1080x1920.mp4')
PAR = int(opt('--parallel', '3')); fps_i = int(FPS)
if PAR <= 1:
    subprocess.check_call(['node', os.path.join(HERE,'render.js'), timed, silent, '--fps', str(FPS), '--jpegq', str(JQ)], env=ENV)
else:
    # split on exact frame boundaries, render segments concurrently, concat losslessly
    nframes = round(total * fps_i); bounds = [round(i * nframes / PAR) for i in range(PAR + 1)]
    segs = []; procs = []
    for i in range(PAR):
        f0, f1 = bounds[i], bounds[i+1]; seg = os.path.join(out, f'seg_{i}.mp4'); segs.append(seg)
        logf = open(os.path.join(out, f'seg_{i}.log'), 'w')
        procs.append(subprocess.Popen(['node', os.path.join(HERE,'render.js'), timed, seg, '--fps', str(FPS), '--jpegq', str(JQ), '--from', repr(f0 / fps_i), '--to', repr(f1 / fps_i)], env=ENV, stdout=logf, stderr=subprocess.STDOUT))
    rc = [p.wait() for p in procs]
    print('segment exit codes', rc)
    if any(rc): sys.exit('segment render failed')
    lst = os.path.join(out, 'segs.txt'); open(lst, 'w').write(''.join(f"file '{s}'\n" for s in segs))
    subprocess.check_call([FF, '-y', '-hide_banner', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', '-movflags', '+faststart', silent])
    print('concatenated', PAR, 'segments →', silent)
# 4) mux narration + music
full = os.path.join(out, 'vazne-10-years-NARRATED-1080x1920.mp4')
subprocess.check_call(['python3', os.path.join(HERE,'mux.py'), timed, silent, music if os.path.exists(music) else 'none', full])
# narration-only version (for the user to lay Suno under)
voice_only = os.path.join(out, 'vazne-10-years-VOICE-ONLY-1080x1920.mp4')
subprocess.check_call(['python3', os.path.join(HERE,'mux.py'), timed, silent, 'none', voice_only])
# 5) 720p preview of narrated
prev = os.path.join(out, 'vazne-10-years-preview-720p.mp4')
subprocess.check_call([FF,'-y','-hide_banner','-loglevel','error','-i', full, '-vf','scale=720:1280','-c:v','libx264','-preset','medium','-crf','26','-c:a','aac','-b:a','128k','-movflags','+faststart', prev])
# 6) QA stills from the final video
st = os.path.join(out,'qa_frames'); os.makedirs(st, exist_ok=True)
subprocess.check_call([FF,'-y','-hide_banner','-loglevel','error','-i', full, '-vf','fps=1/20,scale=540:960', os.path.join(st,'f_%03d.jpg')])
for f in [silent, full, voice_only, prev]: print(f, round(os.path.getsize(f)/1e6,1), 'MB')
