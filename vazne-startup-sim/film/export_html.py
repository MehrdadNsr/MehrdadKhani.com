#!/usr/bin/env python3
"""Export a self-contained playable HTML film folder.
Usage: python3 export_html.py BUILD_DIR OUT_FOLDER   (BUILD_DIR has scenes_timed.json, narration/*.mp3, music.wav)
"""
import json, os, sys, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
FF = subprocess.check_output(['python3','-c','import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())']).decode().strip()
build, out = sys.argv[1], sys.argv[2]
os.makedirs(os.path.join(out,'fonts'), exist_ok=True); os.makedirs(os.path.join(out,'audio'), exist_ok=True)
for f in ['engine.js','templates.js','player.js']: shutil.copy(os.path.join(HERE,f), out)
for f in os.listdir(os.path.join(HERE,'fonts')): shutil.copy(os.path.join(HERE,'fonts',f), os.path.join(out,'fonts',f))
html = open(os.path.join(HERE,'film.html'), encoding='utf-8').read()
html = html.replace('<script src="templates.js"></script>', '<script src="templates.js"></script>\n<script src="player.js"></script>')
html = html.replace('<title>Vazne — 10 Year Simulation</title>', '<title>وزنه — فیلم مسیر ده‌ساله</title>\n<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">')
html = html.replace('html,body{width:1080px;height:1920px;overflow:hidden;', 'html,body{width:100%;height:100%;overflow:hidden;')
html = html.replace('#stage{position:absolute;inset:0;overflow:hidden}', '#stage{position:absolute;left:0;top:0;width:1080px;height:1920px;overflow:hidden;transform-origin:top left}')
open(os.path.join(out,'index.html'),'w',encoding='utf-8').write(html)
data = json.load(open(os.path.join(build,'scenes_timed.json'), encoding='utf-8'))
t = 0
for s in data['scenes']:
    s['start'] = t; t += s['dur']
    if s.get('tts') and os.path.exists(s['tts']):
        name = os.path.basename(s['tts']); shutil.copy(s['tts'], os.path.join(out,'audio',name)); s['tts_url'] = 'audio/'+name
    s.pop('tts', None)
json.dump(data, open(os.path.join(out,'scenes_timed.json'),'w',encoding='utf-8'), ensure_ascii=False)
music = os.path.join(build,'music.wav')
if os.path.exists(music):
    subprocess.check_call([FF,'-y','-hide_banner','-loglevel','error','-i',music,'-t',f'{t:.3f}','-c:a','libmp3lame','-b:a','160k', os.path.join(out,'music.mp3')])
size = sum(os.path.getsize(os.path.join(dp,f)) for dp,_,fs in os.walk(out) for f in fs)
print('exported', out, round(size/1e6,1), 'MB', 'duration', round(t,1))
