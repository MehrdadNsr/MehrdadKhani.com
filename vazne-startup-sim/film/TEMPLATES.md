# Vazne film — scene template catalog (for screenwriters)

Output format: a JSON object {"fps":30,"scenes":[...]}. Each scene:
{
  "id": "short_ascii_id",
  "type": one of the types below,
  "year": 0..10 (float ok, e.g. 1.5) — drives the bottom 10-year progress track,
  "date": "short Persian date label shown top-left, e.g. 'مهر ۱۴۰۵ · Oct 2026' or 'ماه ۳' or 'سال ۴ · ۱۴۰۹'",
  "p": 0..1 — cumulative probability he is still on the path (shown as a small bar), or null to hide,
  "mood": one of quiet | hopeful | tense | low | build | triumph | warm | end | ai — background colour + music cue,
  "narration": "Persian voice-over line(s) for this scene, natural spoken Persian, 1–3 sentences. Scene duration is derived from this (TTS length + padding). Leave empty for purely visual beats.",
  "min_dur": optional minimum seconds,
  "params": { ... per type ... }
}
Persian on-screen strings may use inline emphasis: *word* → amber highlight, **word** → green, ~word~ → red, ^word^ → blue. Western digits are auto-converted to Persian digits inside Persian strings. Keep on-screen text SHORT (it is a phone screen): headlines ≤ 8 words per line, ≤ 3 lines.

## Types and params
- title: {kicker, title (default "وزنه"), subtitle, date}. Opening card with the plate logo.
- chapter: {num, label ("سال"|"فصل"|"ماه"), title, sub}. Big number chapter card.
- text: {kicker?, kickerColor? (blue|mint|red), lines: [..2–4 short lines..], size? ("small"|"large"), align? ("center"), caption?}. Kinetic typography, word-by-word reveal. The workhorse for narration beats.
- montage: {kicker?, items:[{date, text, tone? ("bad"|"good")}] (4–6 items), caption?}. Rapid dated beats — use for "months where nothing happens" or fast sequences.
- counter: {kicker?, items:[{value, label, color? (amber|mint|red|blue), prefix?, suffix?, decimals?, from?}] (1–3 items), caption?}. Big count-up numbers.
- chart: {title, sub?, points:[numbers], xlabels:[..3–5 labels..], ymax?, color? (hex), kind? ("line"|"bar"), valuePrefix?, valueSuffix?, caption?}. Animated line/bar chart.
- timeline / checklist: {title?, items:[{text, sub?, state: "done"|"now"|"next"|"fail"}] (3–7 items), caption?}. Vertical checklist.
- quote: {text, author, source, stars (0–5), caption?}. A review/quote card with stars.
- decision: {kicker?, question, options:[{text, p (0–1), chosen? true, tag?}] (2–3 options), caption?}. A fork with probability bars; the chosen option is highlighted.
- low: {time ("02:47"), timeLabel, lines:[..2–3 lines..], caption?}. Dark rainy low point with a clock.
- year: {year, label?, headline, tiles:[{value, label, color?, prefix?, suffix?, decimals?}] (exactly 4), lines:[..1–2 lines..]}. Year summary card with 4 stat tiles.
- map: {title?, nodes:[{name, sub?, x (0–920), y (0–1000), r?, color?, t? (seconds)}], edges:[[i,j],...], caption?}. Abstract constellation of places/people.
- chat: {title (group/person name), sub?, messages:[{from, text, me? true, ai? true}] (3–6 messages), caption?}. Full-screen messenger conversation (gym group, DM with a coach, etc.).
- phone: {screen: "log"|"playstore"|"chat"|"scan"|"notif"|"stats", data:{...}, caption?, kicker?, scale?}. Phone mockup.
   - log data: {day, rows:[{n (exercise fa), c (code e.g. "LP-04"), s ("4×12"), prev ("80"), now ("82.5")}]}
   - playstore data: {rating ("4.8"|"—"), installs ("12"|"1K+"|"10K+"), status (pill text, English ok), live (bool)}
   - chat data: {messages:[{me?, ai?, text}]} (AI coach inside the app)
   - scan data: {paperTitle, paperLines:[..], rows:[{n,c,s}]} (handwritten paper → parsed rows)
   - notif data: {time ("07:12"), date, items:[{app, t (title), b (body), when?}]} (lock-screen notifications)
   - stats data: {tiles:[{v, l}]} (4 tiles)
- end: {title, lines:[..2–3 lines..], small:[..1–3 tiny credit lines..]}. Closing card.

Rhythm guidance: average 7–9 s per scene; a 5.5–6.5 min film is ~42–52 scenes. Alternate text beats with visual beats (phone/chat/counter/chart) — never more than two `text` scenes in a row. Every year 1–10 must appear at least once (year 1 gets ~45% of screen time, years 2–3 ~25%, years 4–10 ~30%).
