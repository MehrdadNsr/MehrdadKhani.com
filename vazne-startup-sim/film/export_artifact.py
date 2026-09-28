#!/usr/bin/env python3
"""Turn an export_html folder into an artifact-ready folder (no html/head/body skeleton, Google Fonts, smaller music).
Usage: python3 export_artifact.py HTML_FOLDER ART_FOLDER BUILD_DIR"""
import os, sys, re, shutil, subprocess
src, dst, build = sys.argv[1], sys.argv[2], sys.argv[3]
FF = subprocess.check_output(['python3','-c','import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())']).decode().strip()
if os.path.exists(dst): shutil.rmtree(dst)
shutil.copytree(src, dst)
html = open(os.path.join(src,'index.html'), encoding='utf-8').read()
head = re.search(r'<head>(.*?)</head>', html, re.S).group(1)
body = re.search(r'<body>(.*?)</body>', html, re.S).group(1)
head = re.sub(r'<meta[^>]*>', '', head)
head = head.replace('<title>وزنه — فیلم مسیر ده‌ساله</title>', '<title>فیلم ده‌ساله‌ی وزنه</title>')
# Google Fonts first, local files as fallback (same family names)
gf = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;600;700;800;900&family=Lalezar&display=swap">'
head = head.replace("@font-face{font-family:'Vazir';src:url('fonts/Vazirmatn-Regular.ttf');font-weight:400}", "@font-face{font-family:'Vazir';src:local('Vazirmatn'),url('fonts/Vazirmatn-Regular.ttf');font-weight:400}")
head = head.replace("font-family:'Vazir',sans-serif", "font-family:'Vazirmatn','Vazir',sans-serif")
head = head.replace(":root{\n  --bg:#0A0D12;", ":root{ color-scheme:dark;\n  --bg:#0A0D12;")
page = gf + head.strip() + '\n' + body.strip() + '\n'
open(os.path.join(dst,'index.html'),'w',encoding='utf-8').write(page)
# smaller music for the web
music = os.path.join(build,'music.wav')
if os.path.exists(music):
    subprocess.check_call([FF,'-y','-hide_banner','-loglevel','error','-i',music,'-c:a','libmp3lame','-b:a','96k', os.path.join(dst,'music.mp3')])
size = sum(os.path.getsize(os.path.join(dp,f)) for dp,_,fs in os.walk(dst) for f in fs)
files = sorted(os.path.relpath(os.path.join(dp,f), dst) for dp,_,fs in os.walk(dst) for f in fs if f!='index.html')
print('artifact folder', dst, round(size/1e6,1), 'MB;', len(files), 'files'); print(' '.join(files)[:600])
