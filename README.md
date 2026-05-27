# SIA-Licensed Night Security Jobs

A Python automation that scrapes 11 UK job boards for genuine **night-shift** security roles requiring an **SIA Door Supervisor** licence, filters aggressively for South London commute areas, deduplicates, ranks, and emits a single UTF-8 TXT report.

Manual execution only. No scheduler, no daemon.

## Targeted roles

Door Supervisor · Security Officer (Night) · Static Security Guard · Night Concierge · Corporate Security Officer · Gatehouse Security · Front Desk Security · Concierge Security

## Filter rules (hard)

- **SIA mention required** (explicit): `SIA Licence`, `Door Supervisor licence`, `Highfield Level 2`, etc.
- **Night only**: rejects rotating, flexible, event/festival, zero-hours, self-employed, expired listings.
- **Location**: SE / SW / SM / CR / BR postcodes, OR a known London-area place name (Croydon, Bromley, Sidcup, etc.) within ≤60 min commute.
- **Recency**: posted within last 7 days.
- **4-on-4-off rota preferred** (boosts ranking; not required).

## Job sources (Playwright scrapers)

Reed · Indeed UK · CV-Library · Totaljobs · LinkedIn · Hays · Randstad UK · Matchtech · CareerStructure · ICE Recruit · Morson Group

> Status: Reed selectors hardened and verified live. The other 10 sites use best-guess selectors from the original spec; each may need DOM iteration on first real run (see `docs/superpowers/plans/`).

## Requirements

- Python 3.11 or later (tested on 3.14.3)
- Chromium installed for Playwright: `python -m playwright install chromium`
- Windows / macOS / Linux

## Install

```bash
git clone git@github.com:nandosouto-dot/SIA-LICENSED-JOBS.git
cd SIA-LICENSED-JOBS
python -m venv venv
# Activate (pick the one matching your shell):
venv\Scripts\Activate.ps1       # Windows PowerShell
venv\Scripts\activate.bat       # Windows cmd
source venv/bin/activate        # macOS / Linux
pip install -r requirements.txt
python -m playwright install chromium
```

## Usage

```bash
# Default: full unattended run (headless, all 8 roles × 11 sites)
python main.py

# Visible browser (enables manual CAPTCHA solving)
python main.py --visible

# Limit to one site, one role (debugging)
python main.py --visible --roles "Door Supervisor" --sites reed

# Pipeline test without network (uses tests/fixture.json)
python main.py --dry-run

# Subsets via CSV
python main.py --sites reed,indeed,cv-library --roles "Door Supervisor,Night Concierge"
```

## Output

- TXT report: `output/YYYYMMDD HHmmss - Door Supervisor Job Search.txt` (UTF-8)
- Per-run main log: `logs/run_YYYYMMDD_HHmmss.log`
- Per-scraper error logs: `logs/<scraper>_YYYYMMDD_HHmmss.log`

End-of-run summary printed to stdout:

```
Total jobs found: N
Accepted: N
Rejected by filter: N (title=N, recency=N, location=N, shift=N, SIA=N, exclusion=N)
Duplicates removed: N
Failed page loads: N
Execution time: HH:MM:SS
Output: <path>
```

## Project layout

```
.
├── main.py                       # orchestrator + CLI
├── config.py                     # all tunables
├── requirements.txt
├── scrapers/                     # BaseScraper + 11 site implementations
├── core/
│   ├── playwright_engine.py      # stealth, persistent profile, retries, CAPTCHA
│   ├── parser.py                 # JSON-LD JobPosting extractor
│   ├── filter.py                 # title, recency, location, SIA, shift, exclusion
│   ├── dedupe.py                 # rapidfuzz + URL canonicalisation
│   ├── ranking.py                # postcode + salary + role-type scoring
│   └── location.py               # postcode prefix + commute hints
├── utils/
│   ├── helpers.py                # date normaliser, salary parser, text cleaner
│   └── logger.py
├── tests/
│   └── fixture.json              # dry-run sample data
├── docs/superpowers/
│   ├── specs/                    # design spec
│   └── plans/                    # implementation plan
├── output/                       # generated reports (gitignored)
├── logs/                         # per-run logs (gitignored)
└── browser_profile/              # persistent Chromium profile (gitignored)
```

## Architecture notes

**Sequential, two-pass pipeline.** Pass 1 collects search-result rows (cheap fields only) from every site. Cheap filters (title-relevance, recency, location) drop the bulk. Pass 2 visits each surviving job's URL to extract the full description, then expensive filters (SIA, night-shift, exclusions) make the final cut. Pass 1 is fast and bulk; Pass 2 is slow and small.

**Anti-bot**: `playwright-stealth` + persistent Chromium profile + `--disable-http2` for Totaljobs/CareerStructure compatibility. Optional residential proxy via `JOB_SEARCH_PROXY` env var. CAPTCHA detection pauses for manual solve in visible mode.

**Failure isolation**: each scraper wrapped in `try/except` in main loop — one site's failure never aborts the run. Per-scraper errors go to their own log file.

## Iteration playbook (when a scraper returns 0)

1. `python _debug_<site>.py` — a small throwaway script that dumps the first 3 raw job dicts + saves the search-results HTML to `_debug_<site>_page.html`.
2. Inspect the saved HTML to find current selectors (sites change DOM frequently).
3. Update `scrapers/<site>.py` selectors.
4. Re-run.

The `_debug_*.py` and `_debug_*_page.html` patterns are gitignored — safe to keep around for next iteration.
