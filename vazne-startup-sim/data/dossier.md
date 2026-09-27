# DOSSIER: Mehrdad (Mer) Khani — as of 27 Sep 2026

## Who he is
- Persian speaker from Iran (Tehran/Karaj). Now lives in Mississauga, Ontario, Canada (Greater Toronto Area). Writes casually in Persian; prefers plain, warm, direct language.
- Biotechnologist / bioprocess & downstream purification specialist. 6+ years GMP pharma manufacturing (CinnaGen in Iran 2021–2023; Eurofins CDMO Alphora in Mississauga Dec 2023 – May 2026 as API Production Technician on continental rotating shifts, acted as co-lead). Public resume says the Eurofins role ended May 2026, so in Sep 2026 he is likely between roles or in a new one; treat his day-job situation as a branch (employed on shifts vs. job-hunting).
- Preparing for the PTE English test (he built himself a "PTE email trainer" web tool) and plans a CAPM certification. This strongly suggests he is on the Canadian permanent-residence path (Express Entry) and may NOT yet be a PR. Immigration status is unknown: treat "work permit vs PR" as a real branch. A closed work permit can restrict self-employment income; PR removes that. He may not be eligible for programs that require PR/citizenship.
- Does NOT write code. He builds software by briefing AI coding agents (Claude Code, Codex) with detailed specs and verifiers. He is good at writing specs, QA thinking, validation mindset (comes from GMP/process validation). He learns tools fast (built a personal site with blog, SEO, Cloudflare Turnstile; builds AI short films with Higgsfield/Seedance; uses Suno for music).
- Goes to the gym regularly and knows the regulars ("بچه‌های باشگاه"). Gym is his main real-world community besides work and the Iranian diaspora in the GTA (Toronto, North York, Richmond Hill, Mississauga have a very large Persian community).
- Money: a technician salary at best; no savings signal; no investors; no co-founder. Time: shift work eats energy; realistic 8–15 focused hours/week on the project.
- Personality signals: ambitious, wants to "go big", but asks for the MOST FEASIBLE path, not the most glamorous. Likes simulations, systems, structured plans. Emotional, motivated by story.

## The product: Vazne (وزنه = "the weight / plate")
- Android workout-logging app. Prototype stage, distributed as APK only (not yet on Google Play). No iOS.
- Core: user imports or types their training program; each exercise gets a unique code matched to an exercise bank; weights/reps logged per session with previous-session memory ("what did I lift last time"); tapping an exercise shows a how-to picture/cues.
- Offline-first: bank, photos, cues, logging work fully offline. Only two features go online, both optional: (1) scan a handwritten training program photo → text → matched exercises (AI OCR), (2) AI coach chat (bottom-right button) that sees the open page + user history, stores chat on-device, harnessed to training questions only. AI via Claude/OpenAI API through a backend proxy (POST /chat, POST /scan); no keys in the APK.
- Differentiators vs Strong/Hevy/Jefit: handwritten-program scan (gyms in Iran and many immigrant-run gyms still hand out paper programs), Persian-language-first UX + exercise names in Persian and English, previous-session memory, AI coach with context. Weaknesses: no iOS, one-person AI-built codebase, no brand, no marketing budget, generic-looking category with strong incumbents.
- Potential users: (a) Persian-speaking gym-goers in Canada/diaspora (hundreds of thousands in GTA/Vancouver), (b) Iran (tens of millions of gym-goers; but sanctions block Google Play payments/most ad monetization; APK sideloading via Cafe Bazaar/Myket is normal there), (c) English-speaking beginners who get paper programs from trainers, (d) trainers/coaches who write programs by hand and want clients to log.

## Canada facts to use correctly (label estimates as estimates)
- Google Play developer account: USD 25 one-time. New personal developer accounts must run a closed test with at least 12 testers opted-in for 14 continuous days before applying for production access. Identity verification required. Health/fitness apps have data-safety form obligations; AI chat needs a privacy policy.
- Apple: USD 99/year, needs a Mac or cloud Mac; iOS is out of scope initially.
- Ontario sole proprietorship registration ≈ CAD 60 (Ontario Business Registry) for 5 years; federal incorporation ≈ CAD 200 online + annual filing; HST registration mandatory once revenue > CAD 30k in 4 consecutive quarters. Business bank account: CAD 0–30/month.
- Support ecosystem in GTA: Futurpreneur Canada (18–39, loans up to ~CAD 75k with BDC, needs PR/citizen), NRC IRAP (for incorporated Canadian companies with employees), SR&ED tax credits, DMZ at TMU, MaRS, Creative Destruction Lab, Velocity (Waterloo), Founder Institute, Startup Visa program (only relevant for immigration; needs a designated organization). Ontario Small Business Enterprise Centres offer Starter Company Plus (grants ~CAD 5k, needs PR status typically).
- Payments: Google Play billing (15% fee up to USD 1M/yr), Stripe for web subscriptions. Canadian consumer fitness-app pricing: CAD 4.99–9.99/month or CAD 39.99–69.99/year. Typical retention of workout loggers: ~30–40% day-7, 10–15% day-30, single digits at month 6, unless habit-forming and social.
- Sanctions: no Google Play billing or Stripe for users inside Iran; Iranian users can still install APKs; monetization inside Iran requires Iranian payment gateways and an Iranian legal presence — not feasible for him from Canada without a partner.

## Hard constraints for every simulation
- He never becomes a full-time coder; all product work is via AI agents and his QA. Budget his time realistically (8–15 h/week while employed; more if between jobs but with financial stress).
- Money out of pocket: assume he can afford CAD 100–300/month on the project without pain, maybe CAD 1–3k one-off for something important.
- No iOS in year 1. Offline-first must survive.
- Everything must be something he can actually start THIS week from Mississauga.
