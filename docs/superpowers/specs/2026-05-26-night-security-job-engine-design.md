# Night Security Job Engine — Design Spec

**Date:** 2026-05-26
**Author:** Nando + Claude (brainstorming session)
**Status:** Approved, awaiting implementation plan

## Purpose

A Playwright-driven Python aggregator that scrapes UK job boards for genuine night-shift security roles requiring an SIA Door Supervisor licence, filters aggressively, deduplicates, ranks by location/salary, and emits a single UTF-8 TXT report.

Manual execution only. No scheduler, no daemon, no resume-from-crash.

## Decisions locked in

| Decision | Value |
|---|---|
| Scraper coverage | All 11 sites: Reed, CV-Library, Totaljobs, Indeed, LinkedIn, Hays, Randstad UK, Matchtech, CareerStructure, ICE Recruit, Morson Group |
| Anti-bot stance | Full evasion: `playwright-stealth` + persistent profile + optional proxy via env var + CAPTCHA detection with manual-solve pause in visible mode |
| Project root | `D:\Documentos\JOB_SEARCH\` |
| Recency cutoff | Posted in last 7 days |
| Per-site cap | 50 listings per site per role |
| SIA matching | Strict — must explicitly mention SIA / Door Supervisor licence / Highfield Level 2 |
| Concurrency | Sequential (one site, one role at a time) |
| Target roles | Door Supervisor, Security Officer (Night Shift), Static Security Guard, Night Concierge, Corporate Security Officer, Gatehouse Security, Front Desk Security, Concierge Security |
| Target postcodes | SE, SW, SM, CR, BR (or inferred ≤60 min commute) |

## Project layout

```
D:\Documentos\JOB_SEARCH\
├── main.py                       # orchestrator + end-of-run summary
├── config.py                     # tunables: sites, roles, postcodes, caps, recency, paths
├── requirements.txt              # playwright, playwright-stealth, beautifulsoup4, rapidfuzz, lxml
├── output/                       # generated TXT reports
├── logs/                         # per-run log file + per-scraper error logs
├── browser_profile/              # persistent Chromium profile (cookies, session)
├── scrapers/
│   ├── __init__.py
│   ├── base.py                   # BaseScraper ABC (search/parse hooks)
│   ├── reed.py    indeed.py    cv_library.py    totaljobs.py
│   ├── linkedin.py    hays.py    randstad.py    matchtech.py
│   └── careerstructure.py    ice_recruit.py    morson.py
├── core/
│   ├── playwright_engine.py      # BrowserSession ctx mgr (stealth, profile, proxy, CAPTCHA, retry)
│   ├── parser.py                 # JSON-LD JobPosting extractor + BS4 helpers
│   ├── filter.py                 # SIA, night-shift, exclusion, recency, postcode filters
│   ├── ranking.py                # score by postcode rank, salary, role-type boost
│   ├── dedupe.py                 # rapidfuzz fuzzy dedupe + URL canonicalisation
│   └── location.py               # postcode prefix membership + commute hint
└── utils/
    ├── logger.py                 # file logger to logs/, per-scraper channels
    └── helpers.py                # date normaliser, salary parser, text cleaner
```

`scrapers/base.py` is added beyond the user's original list — an abstract class needed for DRY across 11 sites. No behaviour change, pure refactor target.

## Data flow

```
main.py
  └─ for each ROLE (8 target roles):
       └─ for each SCRAPER (11 sites, isolated try/except):
            └─ engine.search(role, max=50)
                 ├─ navigate (3 retries, exp backoff 2s/4s/8s)
                 ├─ dismiss cookie banner
                 ├─ scroll to lazy-load
                 ├─ detect CAPTCHA → pause (visible) or abandon (headless)
                 └─ extract listings (JSON-LD first, DOM fallback)
       → raw_jobs list
  └─ filter pipeline (order matters — cheap checks first):
       recency (7d) → location (SE/SW/SM/CR/BR or ≤60min)
       → night-shift → SIA-explicit → exclusion rules
  └─ dedupe (fuzzy: title ≥90, company ≥95, URL canonical match)
  └─ rank (postcode priority → salary → role-type boost)
  └─ write TXT → print summary
```

## Component contracts

### `core/playwright_engine.py`
- `BrowserSession` context manager. Yields a configured Page.
- Constructor accepts: `headless: bool = True`, `proxy: str | None = None` (from env `JOB_SEARCH_PROXY`), `profile_dir: Path`.
- Methods: `goto(url, retries=3)`, `dismiss_cookies()`, `lazy_scroll(passes=3)`, `detect_captcha() -> bool`, `wait_for_human()` (blocks on stdin in visible mode, raises in headless).
- Applies `playwright-stealth` patches, `en-GB` locale, `Europe/London` timezone, realistic UA, viewport ~1366×768 with jitter.

### `scrapers/base.py`
- Abstract `BaseScraper`. Concrete subclasses implement:
  - `name: str` (used in logs and output's `Source Website`)
  - `search_url(role: str, page: int) -> str`
  - `parse_listings(page) -> list[dict]` — returns raw dicts with keys: `title`, `company`, `location`, `salary`, `date_posted`, `url`, `description`, `employment_type`, `shift_text`.
- Provides shared `run(engine, role, max_results)` that handles pagination, retries, and per-listing yield.

### `core/filter.py`
Pure functions, each returns `bool`:
- `passes_recency(date_posted, max_age_days=7)`
- `passes_location(location_text, postcodes, max_commute_min=60)`
- `passes_night_shift(text)` — accepts only explicit night/overnight/4-on-4-off; rejects rotating/flex/event.
- `passes_sia_explicit(text)` — requires literal SIA / Door Supervisor licence / Highfield mentions.
- `passes_exclusions(text)` — rejects zero-hours, self-employed, cash-in-hand, temp seasonal, event/festival, expired.

### `core/dedupe.py`
- `dedupe(jobs: list[dict]) -> list[dict]`. Uses rapidfuzz `WRatio` ≥90 on title, ≥95 on company, plus canonical URL equality (strip query params, trailing slashes, fragment).

### `core/ranking.py`
- `score(job) -> float`. Composite of: postcode priority rank (SE=5, SW=4, ...), salary midpoint, role-type boost (+10 static/corporate/concierge/gatehouse/reception).
- `rank(jobs) -> list[dict]` sorted desc.

### `core/location.py`
- `postcode_prefix(location_text) -> str | None`
- `in_target_area(prefix) -> bool`
- `commute_estimate(prefix) -> str` — static lookup table to "≈X min" strings; no live API call.

### `utils/helpers.py`
- `normalise_date(raw: str) -> date | None` — handles "Posted 2 days ago", "Yesterday", "3 hours ago", "12/05/2026", ISO strings.
- `parse_salary(raw: str) -> tuple[int | None, int | None]` — extracts (min, max) GBP per annum.
- `clean_text(raw: str) -> str` — strips HTML, collapses whitespace, normalises unicode.

## `main.py` CLI flags

```
python main.py                  # default: headless, full run
python main.py --visible        # show browser window (enables CAPTCHA manual-solve)
python main.py --dry-run        # skip scraping, run filter/dedupe/rank on tests/fixture.json
python main.py --sites reed,indeed   # limit to a subset of scrapers (debugging)
python main.py --roles "Door Supervisor"   # limit to a subset of roles
```

All flags optional. Sensible defaults match a full unattended run.

## Rota extraction

The `Rota` output field is derived in the filter/parse layer (not at the scraper) from `shift_text` + `description`:
- Contains `4 on 4 off` / `4-on-4-off` / `four on four off` → `4-on-4-off`
- Contains other rota patterns (`5 on 3 off`, `3 on 3 off`, etc.) → `Other`
- No rota pattern detected → `Unknown`

## Output format

Filename: `YYYYMMDD HHmmss - Door Supervisor Job Search.txt` (spaces and dash, not underscores), saved to `output/`. Encoding UTF-8 (LF, not CRLF).

Per-job block:
```
 * Company: <name>
 * Job Title: <title>
 * Date Posted: <DD/MM/YYYY>
 * Shift Type: Night
 * Rota: 4-on-4-off / Other / Unknown
 * Employment Type: Permanent / Contract
 * Salary: <if available>
 * Location: <job location>
 * Commute Estimate: <approx travel time>
 * Source Website: <site name>
 * Application URL: <direct link>
```
Blank line between jobs. No header, no footer in the file. Summary printed to stdout only.

## Execution summary (stdout)

```
Total jobs found: N
Accepted: N
Rejected by filter: N (recency=N, location=N, shift=N, SIA=N, exclusion=N)
Duplicates removed: N
Failed page loads: N
Execution time: HH:MM:SS
Output: output/<filename>
```

## Error handling

- Each scraper invocation in `main.py` wrapped in `try/except Exception`. Failure logs to `logs/<scraper>_<timestamp>.log`. Run continues.
- `engine.goto` retries 3× with exponential backoff (2s, 4s, 8s) before raising `NavigationError`.
- CAPTCHA detection looks for: `iframe[src*="recaptcha"]`, `#challenge-form`, `[id^="datadome"]`, `iframe[title*="cloudflare"]`. Visible mode → blocks on `input("CAPTCHA detected on <site>. Solve in browser and press Enter…")`. Headless → logs, raises `CaptchaBlocked`, scraper abandons that site for the run.
- Per-run log captures: scraper start/end, listings found, listings dropped at each filter stage with reason, errors with full tracebacks.

## Anti-bot configuration

- `playwright-stealth` patches navigator fingerprints (webdriver flag, plugins array, languages, etc.).
- Persistent context rooted at `browser_profile/` so cookies/session persist between runs (drops re-challenge frequency on repeat visits to the same site).
- Optional residential proxy via `JOB_SEARCH_PROXY` env var (format `http://user:pass@host:port`). Skipped silently if unset.
- Headers: realistic UA, `Accept-Language: en-GB,en;q=0.9`, viewport 1366×768 with ±30px jitter, locale `en-GB`, timezone `Europe/London`.
- Per-action delays randomised 800–2400ms. Inter-navigation delay 1500–4000ms.

## Testing approach

No formal pytest suite for v1 — this is an operator tool.

- `core/filter.py` and `core/dedupe.py` are pure-function modules. Each gets a few assertions in a `if __name__ == "__main__":` block so they're self-checkable: `python -m core.filter`.
- `main.py --dry-run` runs the filter/dedupe/rank pipeline against a saved JSON fixture of raw scraped data without hitting the network. Lets us iterate on filter logic without burning real scraping cycles.

## YAGNI / explicit non-goals

- No database, no SQLite, no resume-from-crash.
- No email, Slack, or push notification.
- No per-job auto-apply automation.
- No proxy rotation logic — single proxy at most.
- No CAPTCHA-solving service integration.
- Commute estimate is a static prefix → minutes lookup table, not a live Google Maps call.

## Python version note

User spec calls for Python 3.14. As of 2026-05, Playwright and lxml wheels for 3.14 on Windows are not yet broadly published. Implementation will target **3.11+** syntactically (3.14-compatible) and confirm what `python --version` reports in the user's environment during the first plan step. If 3.14 wheels are missing, fall back to 3.12 — both work identically for this codebase.

## Dependencies

```
playwright>=1.45
playwright-stealth>=1.0.6
beautifulsoup4>=4.12
lxml>=5.0
rapidfuzz>=3.5
```

Chromium assumed already installed via `python -m playwright install chromium` per user spec — installer step is not part of the runtime.
