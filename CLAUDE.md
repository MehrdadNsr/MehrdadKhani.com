# CLAUDE.md

Mehrdad Khani's personal site (mehrdadkhani.com): a portfolio, a technical bioprocessing blog, and a PTE email trainer tool.

## Working rules (agreed with Mehrdad)

### Agents and usage
- Do the work yourself in the main session. Site edits, SEO fixes, blog posts and trainer changes don't need subagents.
- When a subagent does help, it runs on the same model as the main session. Don't switch subagents to a smaller or cheaper model; quality matters more than the saving.
- Ask before any multi-agent run (a Workflow, or more than two or three subagents at once). Say how many agents, roughly how many tokens, and what each one does, then wait for a yes. Set a token budget on the run.
- Keep an approved run lean: few agents, a cap on web searches per agent, and verification only for the claims the answer leads with.
- Don't switch to a pricier model than the session default unless Mehrdad asks for it. For a hard problem, raise the effort level first.

## Project
- Plain HTML, CSS and JS with no build step or package manager. GitHub Pages serves the repo root (`CNAME`, `.nojekyll`).
- Pages: `index.html` (portfolio, `ProfilePage`/`Person` JSON-LD), `blog.html`, 11 `post-*.html` articles, `404.html`, and `pte-email-trainer.html`. The trainer is a single-file tool: visitors bring their own Claude, OpenAI or Gemini API key, stored in `localStorage`.
- Shared `styles.css` and `script.js`; images live in `images/` as WebP.
- Each post carries `Article` and `BreadcrumbList` JSON-LD, Open Graph tags and the GA4 tag. When adding or renaming a post, update `blog.html`, `sitemap.xml` and all of those.
- The contact form posts to Formspree. Cloudflare Turnstile is wired up but stays off until `TURNSTILE_SITE_KEY` is set in `index.html`.
- Some posts cover viral clearance and viral inactivation. If Claude Code shows a model-switch notice from Anthropic's biology safeguards, tell Mehrdad instead of working around it.
