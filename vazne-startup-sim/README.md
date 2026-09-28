# وزنه — شبیه‌سازی ده‌ساله‌ی استارتاپ و فیلم مسیر زندگی

این پوشه نتیجه‌ی یک شب شبیه‌سازیه: **۱۲ مسیر** برای این‌که اپ وزنه از یک ای‌پی‌کی روی گوشی مهرداد به یک کسب‌وکار تبدیل بشه، هر کدوم ده سال «زندگی» شد؛ **۴ داور** با نگاه‌های متفاوت امتیاز دادن؛ شدنی‌ترین مسیر انتخاب و به یک خط زمانی ۲۷ مرحله‌ای تبدیل شد؛ و از روی اون یک **فیلم عمودی (۹:۱۶) حدود ۸ دقیقه‌ای** با راوی فارسی ساخته شد.

## چی این‌جاست

| فایل | چیه |
|---|---|
| `01-simulation-12-paths.md` | هر ۱۲ مسیر: روایت ده‌ساله، جدول نقاط عطف، دوراهی‌ها، حرف داورها، رتبه‌بندی |
| `02-chosen-path-10-year-plan.md` | مسیر انتخاب‌شده: چرا، خط زمانی ۲۷ مرحله‌ای با اعداد و احتمال، چک‌لیست هفته‌ی اول، خط قرمزها |
| `03-screenplay.md` | فیلم‌نامه‌ی صحنه‌به‌صحنه با زمان‌بندی، متن راوی و متن روی صفحه |
| `04-suno-lyrics.md` | ترانه برای Suno (متن کامل، استایل پیشنهادی، نگاشت به فیلم، نسخه‌ی کوتاه) |
| `output/` | ویدیوها و خروجی‌ها (نسخه‌ی ۷۲۰p در ریپو؛ نسخه‌های ۱۰۸۰p کامل جداگانه ارسال شده) |
| `html-film/` | نسخه‌ی HTML قابل‌پخش فیلم (با صدا) — `index.html` رو با یک سرور ساده باز کن |
| `film/` | موتور رندر: `film.html` + `engine.js` + `templates.js` (۱۶ قالب صحنه)، `render.js` (کروم → فریم → ffmpeg)، `tts.py` (راوی فارسی)، `mux.py` (میکس)، `music/make_music.py` (موسیقی رویه‌ای)، `build_film.py` (کل خط تولید)، `TEMPLATES.md` |
| `data/` | داسیه‌ی ورودی شبیه‌سازی و داده‌ی خام ۱۲ مسیر (JSON) |

## نسخه‌های فیلم

- `vazne-10-years-NARRATED-1080x1920.mp4` — با راوی فارسی و موسیقی پس‌زمینه (آماده‌ی استوری).
- `vazne-10-years-VOICE-ONLY-1080x1920.mp4` — فقط راوی، بدون موسیقی؛ برای این‌که آهنگ Suno رو زیرش بذاری.
- `vazne-10-years-SILENT-1080x1920.mp4` — کاملاً بی‌صدا؛ برای این‌که صدای خودت رو روش بذاری.
- `vazne-10-years-preview-720p.mp4` — نسخه‌ی سبک برای مرور سریع.

## گذاشتن آهنگ Suno روی فیلم

```bash
# آهنگ زیر راوی، با کم‌شدن خودکار حجم موسیقی وقتی راوی حرف می‌زنه
ffmpeg -i vazne-10-years-VOICE-ONLY-1080x1920.mp4 -i suno.mp3 -filter_complex \
 "[1:a]volume=-10dB,apad[m];[0:a]asplit[v1][v2];[m][v2]sidechaincompress=threshold=0.02:ratio=5:attack=60:release=900[md];[md][v1]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5[a]" \
 -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -shortest vazne-with-suno.mp4

# فقط آهنگ روی نسخه‌ی بی‌صدا
ffmpeg -i vazne-10-years-SILENT-1080x1920.mp4 -i suno.mp3 -map 0:v -map 1:a -c:v copy -c:a aac -shortest vazne-music-only.mp4
```

توی CapCut هم همین کار با «Add audio» روی نسخه‌ی VOICE-ONLY و کم‌کردن حجم موسیقی به حدود ۲۰٪ انجام می‌شه.

## دوباره‌ساختن فیلم (اگه فیلم‌نامه رو عوض کردی)

```bash
pip install imageio-ffmpeg edge-tts numpy
export NODE_PATH=/usr/local/lib/node_modules   # جایی که playwright نصبه
python3 film/build_film.py output/screenplay.json output/build
python3 film/export_html.py output/build html-film
```

`film/TEMPLATES.md` قالب‌های صحنه و پارامترهاشون رو توضیح می‌ده؛ فیلم‌نامه یک JSON از همین صحنه‌هاست.
