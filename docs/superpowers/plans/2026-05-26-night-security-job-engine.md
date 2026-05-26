# Night Security Job Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Playwright-driven Python aggregator that scrapes 11 UK job boards for genuine night-shift SIA Door Supervisor roles, filters aggressively, deduplicates, ranks by location/salary, and emits a single UTF-8 TXT report.

**Architecture:** Sequential pipeline. `main.py` orchestrates: for each target role → for each of 11 site scrapers (BaseScraper subclasses driven by a shared Playwright engine with stealth + persistent profile + CAPTCHA detection) → collect raw listings → run through filter pipeline → dedupe → rank → write TXT. Each scraper failure is isolated; the run continues.

**Tech Stack:** Python 3.14.3 (confirmed installed), Playwright 1.60 sync API, playwright-stealth, BeautifulSoup4, rapidfuzz, lxml.

**Estimated effort:** ~32 tasks. The 11 scraper tasks (Phase 4) require live inspection of each target site to find selectors — budget extra time per scraper for DOM discovery.

**Git note:** Project root `D:\Documentos\JOB_SEARCH\` is **not** currently a git repo. Run `git init` as Task 0.0 if you want per-task commits (recommended). Otherwise skip the commit steps marked *(if using git)*.

**Spec reference:** [docs/superpowers/specs/2026-05-26-night-security-job-engine-design.md](../specs/2026-05-26-night-security-job-engine-design.md)

---

## Phase 0: Scaffold

### Task 0.0: (Optional) Initialise git

**Files:** N/A

- [ ] **Step 1: Init repo + .gitignore**

```bash
cd D:\Documentos\JOB_SEARCH
git init
```

- [ ] **Step 2: Write .gitignore**

Create `.gitignore`:
```
__pycache__/
*.pyc
*.pyo
output/
logs/
browser_profile/
.env
*.egg-info
.pytest_cache/
```

- [ ] **Step 3: Initial commit**

```bash
git add .gitignore docs/
git commit -m "chore: initial scaffold + design spec"
```

### Task 0.1: Directory scaffold

**Files:**
- Create directories: `scrapers/`, `core/`, `utils/`, `output/`, `logs/`, `browser_profile/`

- [ ] **Step 1: Make directories**

```bash
mkdir -p scrapers core utils output logs browser_profile
```

- [ ] **Step 2: Create package __init__ files**

Write three empty files:
- `scrapers/__init__.py` (empty)
- `core/__init__.py` (empty)
- `utils/__init__.py` (empty)

- [ ] **Step 3: Commit** *(if using git)*

```bash
git add scrapers/__init__.py core/__init__.py utils/__init__.py
git commit -m "chore: package scaffold"
```

### Task 0.2: requirements.txt + install missing deps

**Files:**
- Create: `requirements.txt`

- [ ] **Step 1: Write requirements.txt**

```
playwright>=1.45,<2.0
playwright-stealth>=1.0.6
beautifulsoup4>=4.12
lxml>=5.0
rapidfuzz>=3.5
```

- [ ] **Step 2: Install**

```bash
python -m pip install -r requirements.txt
```

Expected: `playwright`, `beautifulsoup4`, `lxml` already satisfied; `playwright-stealth` and `rapidfuzz` install fresh.

- [ ] **Step 3: Verify imports**

```bash
python -c "from playwright.sync_api import sync_playwright; import playwright_stealth, bs4, rapidfuzz, lxml; print('OK')"
```

Expected output: `OK`

- [ ] **Step 4: Commit** *(if using git)*

```bash
git add requirements.txt
git commit -m "chore: pin runtime dependencies"
```

---

## Phase 1: Foundation modules (config + utils)

### Task 1.1: config.py

**Files:**
- Create: `config.py`

- [ ] **Step 1: Write config.py**

```python
"""Central configuration. All tunables live here."""

from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / "output"
LOG_DIR = PROJECT_ROOT / "logs"
BROWSER_PROFILE_DIR = PROJECT_ROOT / "browser_profile"

for d in (OUTPUT_DIR, LOG_DIR, BROWSER_PROFILE_DIR):
    d.mkdir(parents=True, exist_ok=True)

# Target roles (search keywords)
TARGET_ROLES = [
    "Door Supervisor",
    "Security Officer Night Shift",
    "Static Security Guard",
    "Night Concierge",
    "Corporate Security Officer",
    "Gatehouse Security",
    "Front Desk Security",
    "Concierge Security",
]

# Postcode priority — lower index = higher priority
POSTCODE_PRIORITY = ["SE", "SW", "SM", "CR", "BR"]

# Static commute estimate by postcode prefix (rough London inner→outer)
COMMUTE_ESTIMATES = {
    "SE": "20-40 min",
    "SW": "25-45 min",
    "SM": "35-55 min",
    "CR": "30-50 min",
    "BR": "35-55 min",
    "E":  "40-60 min",
    "EC": "30-50 min",
    "N":  "45-60 min",
    "NW": "40-60 min",
    "W":  "35-55 min",
    "WC": "30-50 min",
    "DA": "40-60 min",
    "KT": "45-60 min",
    "TW": "45-60 min",
}

# Filter thresholds
RECENCY_DAYS = 7
PER_SITE_CAP = 50
MAX_COMMUTE_MIN = 60

# Boost keywords for ranking (case-insensitive substring match)
ROLE_BOOST_KEYWORDS = [
    "static", "corporate", "concierge", "gatehouse",
    "reception", "front desk",
]

# Exclusion keywords (case-insensitive substring match in description)
EXCLUSION_KEYWORDS = [
    "rotating day/night", "rotating days/nights", "rotating shifts",
    "flexible shifts", "event security", "festival security",
    "temporary seasonal", "seasonal work", "zero hours", "zero-hours",
    "self-employed", "self employed", "cash in hand", "cash-in-hand",
    "no longer accepting applications", "this job has expired",
]

# Night shift positive markers
NIGHT_KEYWORDS = [
    "night shift", "nights only", "night-only", "overnight",
    "permanent nights", "night work", "10pm", "11pm", "12am",
    "22:00", "23:00", "00:00",
]

# Day/rotating markers that DISQUALIFY (must absence of these implied night)
DAY_KEYWORDS = [
    "day shift", "days only", "9am-5pm", "9-5", "monday to friday",
    "mon-fri", "office hours",
]

# SIA explicit markers (at least one required)
SIA_KEYWORDS = [
    "sia licence", "sia license", "sia door supervisor",
    "door supervisor licence", "door supervisor license",
    "highfield level 2 door supervisor", "level 2 door supervisor",
    "sia ds", "ds licence", "ds license",
]

# Rota classification patterns (regex-style raw, case-insensitive)
ROTA_4_ON_4_OFF_PATTERNS = [
    r"4\s*on\s*4\s*off", r"4-on-4-off", r"four\s+on\s+four\s+off",
]

# User agent for Playwright
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Delays (milliseconds)
ACTION_DELAY_MIN_MS = 800
ACTION_DELAY_MAX_MS = 2400
NAV_DELAY_MIN_MS = 1500
NAV_DELAY_MAX_MS = 4000

# Output filename pattern
OUTPUT_FILENAME_FMT = "%Y%m%d %H%M%S - Door Supervisor Job Search.txt"
```

- [ ] **Step 2: Smoke-test the module loads**

```bash
python -c "import config; print('roles:', len(config.TARGET_ROLES), 'cap:', config.PER_SITE_CAP)"
```

Expected: `roles: 8 cap: 50`

- [ ] **Step 3: Commit** *(if using git)*

```bash
git add config.py
git commit -m "feat(config): central configuration module"
```

### Task 1.2: utils/logger.py

**Files:**
- Create: `utils/logger.py`

- [ ] **Step 1: Write logger module**

```python
"""File-based logger. One main run log plus per-scraper error logs."""

import logging
import sys
from datetime import datetime
from pathlib import Path

from config import LOG_DIR

_RUN_TS = datetime.now().strftime("%Y%m%d_%H%M%S")
_MAIN_LOG_PATH = LOG_DIR / f"run_{_RUN_TS}.log"


def get_logger(name: str) -> logging.Logger:
    """Return a logger that writes to the per-run main log + stdout."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    fh = logging.FileHandler(_MAIN_LOG_PATH, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    logger.propagate = False
    return logger


def get_scraper_error_logger(scraper_name: str) -> logging.Logger:
    """Per-scraper error log file. Use for site-specific failures."""
    logger = logging.getLogger(f"scraper.{scraper_name}.errors")
    if logger.handlers:
        return logger
    logger.setLevel(logging.WARNING)
    path = LOG_DIR / f"{scraper_name}_{_RUN_TS}.log"
    fh = logging.FileHandler(path, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)
    logger.propagate = False
    return logger
```

- [ ] **Step 2: Smoke test**

```bash
python -c "from utils.logger import get_logger; get_logger('test').info('hello'); print('OK')"
```

Expected: Console shows `[INFO] test: hello`, file `logs/run_<ts>.log` exists with same line.

- [ ] **Step 3: Commit** *(if using git)*

```bash
git add utils/logger.py
git commit -m "feat(logger): per-run main log + per-scraper error channels"
```

### Task 1.3: utils/helpers.py — date normaliser (TDD)

**Files:**
- Create: `utils/helpers.py`

- [ ] **Step 1: Write the failing test (inline asserts)**

Create `utils/helpers.py` with ONLY the test block at the bottom:

```python
"""Date / salary / text helpers."""

from datetime import date, datetime, timedelta


def normalise_date(raw):
    raise NotImplementedError


if __name__ == "__main__":
    today = date.today()

    # Relative
    assert normalise_date("Posted today") == today
    assert normalise_date("Yesterday") == today - timedelta(days=1)
    assert normalise_date("2 days ago") == today - timedelta(days=2)
    assert normalise_date("Posted 3 hours ago") == today
    assert normalise_date("Posted just now") == today
    assert normalise_date("1 week ago") == today - timedelta(days=7)

    # Absolute UK
    assert normalise_date("12/05/2026") == date(2026, 5, 12)
    assert normalise_date("12-05-2026") == date(2026, 5, 12)

    # ISO
    assert normalise_date("2026-05-12") == date(2026, 5, 12)
    assert normalise_date("2026-05-12T08:30:00Z") == date(2026, 5, 12)

    # Empty / junk
    assert normalise_date("") is None
    assert normalise_date(None) is None
    assert normalise_date("blah") is None

    print("normalise_date OK")
```

- [ ] **Step 2: Run, verify it fails**

```bash
python -m utils.helpers
```

Expected: `NotImplementedError` raised on first assertion.

- [ ] **Step 3: Implement normalise_date**

Replace the body of `normalise_date` with:

```python
import re

def normalise_date(raw):
    if not raw:
        return None
    text = str(raw).strip().lower()
    today = date.today()
    if not text:
        return None
    if "just now" in text or "today" in text or "minute" in text or "hour" in text:
        return today
    if "yesterday" in text:
        return today - timedelta(days=1)
    m = re.search(r"(\d+)\s*(day|week|month|year)s?\s*ago", text)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        days = {"day": 1, "week": 7, "month": 30, "year": 365}[unit]
        return today - timedelta(days=n * days)
    # ISO with optional time
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    # UK dd/mm/yyyy or dd-mm-yyyy
    m = re.match(r"(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})", text)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        try:
            return date(y, mo, d)
        except ValueError:
            return None
    return None
```

Move the `import re` to the top of the file (with `from datetime import …`).

- [ ] **Step 4: Run, verify all pass**

```bash
python -m utils.helpers
```

Expected: `normalise_date OK`

- [ ] **Step 5: Commit** *(if using git)*

```bash
git add utils/helpers.py
git commit -m "feat(helpers): date normaliser"
```

### Task 1.4: utils/helpers.py — salary parser (TDD)

**Files:**
- Modify: `utils/helpers.py` (append)

- [ ] **Step 1: Add failing test**

Append to `utils/helpers.py` (before the `print(...)` line in `__main__`):

```python
def parse_salary(raw):
    raise NotImplementedError


# In the __main__ block, ADD these assertions before the final print:
# (full updated __main__ shown below)
```

Update the whole `__main__` block to:

```python
if __name__ == "__main__":
    # ... existing date asserts unchanged ...
    print("normalise_date OK")

    assert parse_salary("£28,000 - £32,000 per annum") == (28000, 32000)
    assert parse_salary("£14.50 per hour") == (None, None)  # hourly not annualised in v1
    assert parse_salary("28000 to 32000") == (28000, 32000)
    assert parse_salary("£30k") == (30000, 30000)
    assert parse_salary("£30k - £35k") == (30000, 35000)
    assert parse_salary("Competitive") == (None, None)
    assert parse_salary("") == (None, None)
    assert parse_salary(None) == (None, None)
    print("parse_salary OK")
```

- [ ] **Step 2: Run, verify failure**

```bash
python -m utils.helpers
```

Expected: `NotImplementedError` from `parse_salary`.

- [ ] **Step 3: Implement parse_salary**

```python
def parse_salary(raw):
    if not raw:
        return (None, None)
    text = str(raw).lower().replace(",", "").replace("£", "").strip()
    if not text or "competitive" in text or "negotiable" in text:
        return (None, None)
    # Extract numbers, treating 'k' as thousand multiplier
    matches = re.findall(r"(\d+(?:\.\d+)?)(k?)", text)
    nums = []
    for n, k in matches:
        v = float(n) * (1000 if k == "k" else 1)
        if v >= 1000:  # treat low values as hourly noise
            nums.append(int(v))
    if not nums:
        return (None, None)
    if len(nums) == 1:
        return (nums[0], nums[0])
    return (min(nums), max(nums))
```

- [ ] **Step 4: Verify pass**

```bash
python -m utils.helpers
```

Expected: `normalise_date OK` then `parse_salary OK`.

- [ ] **Step 5: Commit** *(if using git)*

```bash
git add utils/helpers.py
git commit -m "feat(helpers): salary parser"
```

### Task 1.5: utils/helpers.py — text cleaner + jitter delay

**Files:**
- Modify: `utils/helpers.py`

- [ ] **Step 1: Append test**

Add to `__main__` after `parse_salary OK`:

```python
    assert clean_text("  Hello\n\n  world  ") == "Hello world"
    assert clean_text("<p>Foo &amp; bar</p>") == "Foo & bar"
    assert clean_text("") == ""
    assert clean_text(None) == ""
    print("clean_text OK")
```

Add stubs above `__main__`:

```python
def clean_text(raw):
    raise NotImplementedError


def random_delay(min_ms, max_ms):
    """Sleep for a random duration in [min_ms, max_ms] milliseconds."""
    raise NotImplementedError
```

- [ ] **Step 2: Run, verify failure**

```bash
python -m utils.helpers
```

- [ ] **Step 3: Implement**

```python
import random
import time
from html import unescape

from bs4 import BeautifulSoup


def clean_text(raw):
    if not raw:
        return ""
    text = unescape(str(raw))
    # Strip HTML if present
    if "<" in text and ">" in text:
        text = BeautifulSoup(text, "lxml").get_text(" ")
    return " ".join(text.split())


def random_delay(min_ms, max_ms):
    time.sleep(random.uniform(min_ms / 1000, max_ms / 1000))
```

Move `import random`, `import time`, `from html import unescape`, `from bs4 import BeautifulSoup` to the top of the file with the other imports.

- [ ] **Step 4: Verify pass**

```bash
python -m utils.helpers
```

Expected: all three OK lines.

- [ ] **Step 5: Commit** *(if using git)*

```bash
git add utils/helpers.py
git commit -m "feat(helpers): text cleaner + random delay"
```

### Task 1.6: core/location.py (TDD)

**Files:**
- Create: `core/location.py`

- [ ] **Step 1: Write failing test**

```python
"""Postcode-prefix matching + commute hint."""

import re

from config import COMMUTE_ESTIMATES, MAX_COMMUTE_MIN, POSTCODE_PRIORITY

_PREFIX_RE = re.compile(r"\b([A-Z]{1,2})\d", re.IGNORECASE)


def postcode_prefix(location_text):
    raise NotImplementedError


def in_target_area(prefix):
    raise NotImplementedError


def commute_estimate(prefix):
    raise NotImplementedError


def commute_minutes_upper(prefix):
    """Upper bound of the commute estimate in minutes, or 999 if unknown."""
    raise NotImplementedError


if __name__ == "__main__":
    assert postcode_prefix("London SE1 4AB") == "SE"
    assert postcode_prefix("Croydon CR0") == "CR"
    assert postcode_prefix("Bromley, BR1 2XY") == "BR"
    assert postcode_prefix("Manchester M1 4BT") == "M"
    assert postcode_prefix("No postcode here") is None
    assert postcode_prefix("") is None
    assert postcode_prefix(None) is None

    assert in_target_area("SE") is True
    assert in_target_area("SW") is True
    assert in_target_area("M") is False
    assert in_target_area(None) is False

    assert commute_estimate("SE") == "20-40 min"
    assert commute_estimate("ZZ") == "Unknown"

    assert commute_minutes_upper("SE") == 40
    assert commute_minutes_upper("ZZ") == 999
    print("location OK")
```

- [ ] **Step 2: Run, verify failure**

```bash
python -m core.location
```

- [ ] **Step 3: Implement**

```python
def postcode_prefix(location_text):
    if not location_text:
        return None
    m = _PREFIX_RE.search(str(location_text))
    return m.group(1).upper() if m else None


def in_target_area(prefix):
    if not prefix:
        return False
    return prefix in POSTCODE_PRIORITY


def commute_estimate(prefix):
    return COMMUTE_ESTIMATES.get(prefix, "Unknown")


def commute_minutes_upper(prefix):
    est = COMMUTE_ESTIMATES.get(prefix)
    if not est:
        return 999
    m = re.search(r"(\d+)\s*min", est)
    if not m:
        return 999
    # est format "X-Y min" — pull both numbers
    nums = [int(n) for n in re.findall(r"\d+", est)]
    return max(nums) if nums else 999
```

- [ ] **Step 4: Verify pass**

```bash
python -m core.location
```

Expected: `location OK`

- [ ] **Step 5: Commit** *(if using git)*

```bash
git add core/location.py
git commit -m "feat(location): postcode prefix + commute helpers"
```

---

## Phase 2: Playwright engine

### Task 2.1: core/playwright_engine.py — BrowserSession skeleton

**Files:**
- Create: `core/playwright_engine.py`

- [ ] **Step 1: Write engine module**

```python
"""Playwright wrapper: stealth, persistent profile, retries, CAPTCHA detection."""

import os
import random
import sys
from contextlib import contextmanager

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from config import (
    ACTION_DELAY_MAX_MS, ACTION_DELAY_MIN_MS, BROWSER_PROFILE_DIR,
    NAV_DELAY_MAX_MS, NAV_DELAY_MIN_MS, USER_AGENT,
)
from utils.helpers import random_delay
from utils.logger import get_logger

log = get_logger("engine")

CAPTCHA_SELECTORS = [
    'iframe[src*="recaptcha"]',
    'iframe[title*="cloudflare" i]',
    '#challenge-form',
    '[id^="datadome"]',
    'iframe[src*="hcaptcha"]',
    'div.cf-browser-verification',
]

COOKIE_BUTTON_SELECTORS = [
    'button:has-text("Accept all")',
    'button:has-text("Accept All")',
    'button:has-text("I accept")',
    'button:has-text("Agree")',
    'button#onetrust-accept-btn-handler',
    'button[aria-label*="accept" i]',
    'button[data-testid*="accept" i]',
]


class NavigationError(Exception):
    pass


class CaptchaBlocked(Exception):
    pass


class BrowserSession:
    def __init__(self, headless=True, proxy=None):
        self.headless = headless
        self.proxy = proxy or os.environ.get("JOB_SEARCH_PROXY")
        self._pw = None
        self._context = None
        self.page = None
        self.failed_navigations = 0

    def __enter__(self):
        self._pw = sync_playwright().start()
        viewport_w = 1366 + random.randint(-30, 30)
        viewport_h = 768 + random.randint(-20, 20)
        launch_kwargs = {
            "headless": self.headless,
            "user_agent": USER_AGENT,
            "viewport": {"width": viewport_w, "height": viewport_h},
            "locale": "en-GB",
            "timezone_id": "Europe/London",
            "extra_http_headers": {"Accept-Language": "en-GB,en;q=0.9"},
        }
        if self.proxy:
            launch_kwargs["proxy"] = {"server": self.proxy}
        self._context = self._pw.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_PROFILE_DIR),
            **launch_kwargs,
        )
        self.page = self._context.new_page()
        try:
            from playwright_stealth import Stealth
            Stealth().apply_stealth_sync(self.page)
        except Exception as e:
            log.warning(f"playwright-stealth not applied: {e}")
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if self._context:
                self._context.close()
        finally:
            if self._pw:
                self._pw.stop()

    def goto(self, url, retries=3, wait_until="domcontentloaded"):
        last_err = None
        for attempt in range(1, retries + 1):
            try:
                self.page.goto(url, wait_until=wait_until, timeout=30000)
                random_delay(NAV_DELAY_MIN_MS, NAV_DELAY_MAX_MS)
                return
            except PWTimeout as e:
                last_err = e
                log.warning(f"goto attempt {attempt}/{retries} timed out: {url}")
                random_delay(2000 * attempt, 4000 * attempt)
            except Exception as e:
                last_err = e
                log.warning(f"goto attempt {attempt}/{retries} error: {e}")
                random_delay(2000 * attempt, 4000 * attempt)
        self.failed_navigations += 1
        raise NavigationError(f"Could not load {url}: {last_err}")

    def dismiss_cookies(self):
        for sel in COOKIE_BUTTON_SELECTORS:
            try:
                btn = self.page.locator(sel).first
                if btn.count() and btn.is_visible(timeout=1000):
                    btn.click(timeout=2000)
                    random_delay(ACTION_DELAY_MIN_MS, ACTION_DELAY_MAX_MS)
                    return True
            except Exception:
                continue
        return False

    def lazy_scroll(self, passes=3):
        for _ in range(passes):
            self.page.mouse.wheel(0, 1500)
            random_delay(ACTION_DELAY_MIN_MS, ACTION_DELAY_MAX_MS)

    def detect_captcha(self):
        for sel in CAPTCHA_SELECTORS:
            try:
                if self.page.locator(sel).count():
                    return True
            except Exception:
                continue
        return False

    def wait_for_human(self, site_name):
        if self.headless:
            raise CaptchaBlocked(f"CAPTCHA on {site_name} in headless mode")
        print(f"\n[CAPTCHA] Detected on {site_name}. Solve in browser then press Enter…", file=sys.stderr)
        input()
```

- [ ] **Step 2: Smoke test**

```bash
python -c "from core.playwright_engine import BrowserSession; bs=BrowserSession(headless=True); bs.__enter__(); bs.goto('https://example.com'); print(bs.page.title()); bs.__exit__(None,None,None)"
```

Expected: `Example Domain` printed.

- [ ] **Step 3: Commit** *(if using git)*

```bash
git add core/playwright_engine.py
git commit -m "feat(engine): BrowserSession with stealth, retries, CAPTCHA hook"
```

---

## Phase 3: Pipeline modules

### Task 3.1: core/parser.py — JSON-LD JobPosting extractor

**Files:**
- Create: `core/parser.py`

- [ ] **Step 1: Write failing test**

```python
"""HTML / JSON-LD extraction helpers."""

import json
from bs4 import BeautifulSoup


def extract_jsonld_jobpostings(html):
    raise NotImplementedError


if __name__ == "__main__":
    html = '''
    <html><head>
    <script type="application/ld+json">
    {"@type":"JobPosting","title":"Door Supervisor","hiringOrganization":{"name":"Acme Sec"},"jobLocation":{"address":{"addressLocality":"London SE1"}},"datePosted":"2026-05-20"}
    </script>
    <script type="application/ld+json">[
      {"@type":"JobPosting","title":"Night Concierge","hiringOrganization":"BigCorp"},
      {"@type":"Other","title":"ignore me"}
    ]</script>
    </head></html>
    '''
    out = extract_jsonld_jobpostings(html)
    titles = sorted(j.get("title") for j in out)
    assert titles == ["Door Supervisor", "Night Concierge"], titles
    print("parser OK")
```

- [ ] **Step 2: Run, verify failure**

```bash
python -m core.parser
```

- [ ] **Step 3: Implement**

```python
def extract_jsonld_jobpostings(html):
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    out = []
    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or "")
        except Exception:
            continue
        for entry in (data if isinstance(data, list) else [data]):
            if isinstance(entry, dict) and entry.get("@type") == "JobPosting":
                out.append(entry)
    return out
```

- [ ] **Step 4: Verify pass**

```bash
python -m core.parser
```

Expected: `parser OK`

- [ ] **Step 5: Commit** *(if using git)*

```bash
git add core/parser.py
git commit -m "feat(parser): JSON-LD JobPosting extractor"
```

### Task 3.2: core/filter.py — all filters (TDD)

**Files:**
- Create: `core/filter.py`

- [ ] **Step 1: Write failing test**

```python
"""Filter pipeline for raw scraped jobs."""

import re
from datetime import date, timedelta

from config import (
    DAY_KEYWORDS, EXCLUSION_KEYWORDS, MAX_COMMUTE_MIN, NIGHT_KEYWORDS,
    POSTCODE_PRIORITY, RECENCY_DAYS, ROTA_4_ON_4_OFF_PATTERNS, SIA_KEYWORDS,
)
from core.location import commute_minutes_upper, in_target_area, postcode_prefix


def passes_recency(date_posted, max_age_days=RECENCY_DAYS):
    raise NotImplementedError


def passes_location(location_text):
    raise NotImplementedError


def passes_night_shift(text):
    raise NotImplementedError


def passes_sia_explicit(text):
    raise NotImplementedError


def passes_exclusions(text):
    raise NotImplementedError


def classify_rota(text):
    raise NotImplementedError


if __name__ == "__main__":
    today = date.today()

    # recency
    assert passes_recency(today) is True
    assert passes_recency(today - timedelta(days=3)) is True
    assert passes_recency(today - timedelta(days=10)) is False
    assert passes_recency(None) is False

    # location
    assert passes_location("London SE1 4AB") is True
    assert passes_location("Croydon CR0") is True
    assert passes_location("Manchester M1") is False
    assert passes_location("") is False

    # night shift
    assert passes_night_shift("Permanent nights, 4 on 4 off") is True
    assert passes_night_shift("Day shift only, 9-5") is False
    assert passes_night_shift("Mon-Fri office hours") is False
    assert passes_night_shift("") is False
    assert passes_night_shift("rotating day/night") is True  # exclusion catches this later

    # SIA
    assert passes_sia_explicit("Must hold valid SIA Licence") is True
    assert passes_sia_explicit("Door Supervisor licence required") is True
    assert passes_sia_explicit("Highfield Level 2 Door Supervisor preferred") is True
    assert passes_sia_explicit("Security experience preferred") is False

    # exclusions
    assert passes_exclusions("Zero hours contract") is False
    assert passes_exclusions("Event security, festival work") is False
    assert passes_exclusions("Self-employed door supervisor") is False
    assert passes_exclusions("Permanent night role at static site") is True

    # rota
    assert classify_rota("4 on 4 off shifts") == "4-on-4-off"
    assert classify_rota("Four on four off pattern") == "4-on-4-off"
    assert classify_rota("3 on 3 off rota") == "Other"
    assert classify_rota("no shift info") == "Unknown"

    print("filter OK")
```

- [ ] **Step 2: Run, verify failure**

```bash
python -m core.filter
```

- [ ] **Step 3: Implement**

```python
def _lower(t):
    return (t or "").lower()


def passes_recency(date_posted, max_age_days=RECENCY_DAYS):
    if not date_posted:
        return False
    delta = (date.today() - date_posted).days
    return 0 <= delta <= max_age_days


def passes_location(location_text):
    prefix = postcode_prefix(location_text)
    if not prefix:
        return False
    if in_target_area(prefix):
        return True
    return commute_minutes_upper(prefix) <= MAX_COMMUTE_MIN


def passes_night_shift(text):
    t = _lower(text)
    if not t:
        return False
    has_night = any(k in t for k in NIGHT_KEYWORDS)
    has_day_only = any(k in t for k in DAY_KEYWORDS)
    return has_night and not has_day_only


def passes_sia_explicit(text):
    t = _lower(text)
    return any(k in t for k in SIA_KEYWORDS)


def passes_exclusions(text):
    """Returns True if job PASSES (i.e. no exclusion words present)."""
    t = _lower(text)
    return not any(k in t for k in EXCLUSION_KEYWORDS)


def classify_rota(text):
    t = _lower(text)
    for pat in ROTA_4_ON_4_OFF_PATTERNS:
        if re.search(pat, t):
            return "4-on-4-off"
    if re.search(r"\d\s*on\s*\d\s*off", t):
        return "Other"
    return "Unknown"
```

- [ ] **Step 4: Verify pass**

```bash
python -m core.filter
```

Expected: `filter OK`

- [ ] **Step 5: Commit** *(if using git)*

```bash
git add core/filter.py
git commit -m "feat(filter): recency, location, shift, SIA, exclusion, rota"
```

### Task 3.3: core/dedupe.py (TDD)

**Files:**
- Create: `core/dedupe.py`

- [ ] **Step 1: Write failing test**

```python
"""Fuzzy deduplication across raw scraped jobs."""

from urllib.parse import urlparse, urlunparse
from rapidfuzz import fuzz


def canonical_url(url):
    raise NotImplementedError


def dedupe(jobs):
    raise NotImplementedError


if __name__ == "__main__":
    assert canonical_url("https://reed.co.uk/jobs/123?utm=x") == "https://reed.co.uk/jobs/123"
    assert canonical_url("https://reed.co.uk/jobs/123/") == "https://reed.co.uk/jobs/123"
    assert canonical_url("https://reed.co.uk/jobs/123#section") == "https://reed.co.uk/jobs/123"
    assert canonical_url("") == ""
    assert canonical_url(None) == ""

    jobs = [
        {"title": "Door Supervisor", "company": "Acme Security", "url": "https://reed.co.uk/jobs/1?utm=x"},
        {"title": "Door Supervisor", "company": "Acme Security", "url": "https://reed.co.uk/jobs/1"},  # dup URL
        {"title": "Door Supervisor Nights", "company": "Acme Security Ltd", "url": "https://other.com/2"},  # fuzzy dup
        {"title": "Night Concierge", "company": "Different Co", "url": "https://other.com/3"},
    ]
    out = dedupe(jobs)
    assert len(out) == 2, [j["url"] for j in out]
    print("dedupe OK")
```

- [ ] **Step 2: Run, verify failure**

```bash
python -m core.dedupe
```

- [ ] **Step 3: Implement**

```python
def canonical_url(url):
    if not url:
        return ""
    parts = urlparse(str(url))
    path = parts.path.rstrip("/")
    return urlunparse((parts.scheme, parts.netloc, path, "", "", ""))


def dedupe(jobs):
    out = []
    for job in jobs:
        cu = canonical_url(job.get("url"))
        title = (job.get("title") or "").strip()
        company = (job.get("company") or "").strip()
        is_dup = False
        for kept in out:
            if cu and cu == canonical_url(kept.get("url")):
                is_dup = True
                break
            if (
                fuzz.WRatio(title, kept.get("title") or "") >= 90
                and fuzz.WRatio(company, kept.get("company") or "") >= 95
            ):
                is_dup = True
                break
        if not is_dup:
            out.append(job)
    return out
```

- [ ] **Step 4: Verify pass**

```bash
python -m core.dedupe
```

Expected: `dedupe OK`

- [ ] **Step 5: Commit** *(if using git)*

```bash
git add core/dedupe.py
git commit -m "feat(dedupe): fuzzy + canonical URL deduplication"
```

### Task 3.4: core/ranking.py (TDD)

**Files:**
- Create: `core/ranking.py`

- [ ] **Step 1: Write failing test**

```python
"""Composite ranking score for filtered jobs."""

from config import POSTCODE_PRIORITY, ROLE_BOOST_KEYWORDS
from core.location import postcode_prefix


def score(job):
    raise NotImplementedError


def rank(jobs):
    raise NotImplementedError


if __name__ == "__main__":
    j1 = {"location": "London SE1", "salary_min": 35000, "title": "Static Security"}
    j2 = {"location": "Bromley BR1", "salary_min": 30000, "title": "Door Supervisor"}
    j3 = {"location": "Manchester M1", "salary_min": 40000, "title": "Concierge Security"}
    assert score(j1) > score(j2)  # SE > BR
    assert score(j1) > score(j3)  # SE > M even with lower salary

    ranked = rank([j2, j3, j1])
    assert ranked[0] == j1
    print("ranking OK")
```

- [ ] **Step 2: Run, verify failure**

```bash
python -m core.ranking
```

- [ ] **Step 3: Implement**

```python
def score(job):
    s = 0.0

    # Postcode priority — top of list = biggest boost
    prefix = postcode_prefix(job.get("location"))
    if prefix in POSTCODE_PRIORITY:
        s += (len(POSTCODE_PRIORITY) - POSTCODE_PRIORITY.index(prefix)) * 1000

    # Salary midpoint
    smin = job.get("salary_min") or 0
    smax = job.get("salary_max") or smin
    s += (smin + smax) / 2 / 100  # scale so postcode dominates

    # Role-type boost
    text = ((job.get("title") or "") + " " + (job.get("description") or "")).lower()
    for kw in ROLE_BOOST_KEYWORDS:
        if kw in text:
            s += 50

    return s


def rank(jobs):
    return sorted(jobs, key=score, reverse=True)
```

- [ ] **Step 4: Verify pass**

```bash
python -m core.ranking
```

Expected: `ranking OK`

- [ ] **Step 5: Commit** *(if using git)*

```bash
git add core/ranking.py
git commit -m "feat(ranking): composite postcode+salary+role-type score"
```

---

## Phase 4: Scrapers

### Task 4.0: scrapers/base.py — abstract BaseScraper

**Files:**
- Create: `scrapers/base.py`

- [ ] **Step 1: Write base class**

```python
"""Abstract scraper. Subclasses implement search_url + parse_listings."""

from abc import ABC, abstractmethod

from config import PER_SITE_CAP
from utils.logger import get_logger, get_scraper_error_logger


class BaseScraper(ABC):
    name: str = "BASE"

    def __init__(self, engine):
        self.engine = engine
        self.log = get_logger(f"scraper.{self.name}")
        self.errlog = get_scraper_error_logger(self.name)

    @abstractmethod
    def search_url(self, role: str, page: int) -> str:
        ...

    @abstractmethod
    def parse_listings(self, page) -> list[dict]:
        """Return list of raw listing dicts. Required keys: title, company,
        location, salary, date_posted, url, description, employment_type, shift_text."""
        ...

    def run(self, role: str, max_results: int = PER_SITE_CAP) -> list[dict]:
        """Iterate through pages, dedupe by URL within this run, cap at max_results."""
        collected = []
        seen_urls = set()
        page_num = 1
        while len(collected) < max_results and page_num <= 5:
            url = self.search_url(role, page_num)
            try:
                self.engine.goto(url)
                self.engine.dismiss_cookies()
                if self.engine.detect_captcha():
                    self.engine.wait_for_human(self.name)
                self.engine.lazy_scroll(passes=2)
                listings = self.parse_listings(self.engine.page)
            except Exception as e:
                self.errlog.error(f"page {page_num} role={role}: {e}", exc_info=True)
                break
            if not listings:
                break
            for item in listings:
                u = item.get("url") or ""
                if u in seen_urls:
                    continue
                seen_urls.add(u)
                item.setdefault("source", self.name)
                collected.append(item)
                if len(collected) >= max_results:
                    break
            page_num += 1
        self.log.info(f"role={role!r} collected={len(collected)}")
        return collected
```

- [ ] **Step 2: Smoke test importability**

```bash
python -c "from scrapers.base import BaseScraper; print(BaseScraper.__abstractmethods__)"
```

Expected: `frozenset({'parse_listings', 'search_url'})`

- [ ] **Step 3: Commit** *(if using git)*

```bash
git add scrapers/base.py
git commit -m "feat(scrapers): BaseScraper abstract class"
```

### Task 4.1: scrapers/reed.py

**Files:**
- Create: `scrapers/reed.py`

- [ ] **Step 1: Manually inspect Reed**

In a browser, open `https://www.reed.co.uk/jobs/door-supervisor-jobs?pageno=1`. Identify:
- Listing container selector (currently `article.job-card_jobCard__MkcJD` or similar — confirm by inspecting)
- Title selector, company selector, location, salary, date posted, link
- Check if JSON-LD JobPosting is present in page source (View Source → search "JobPosting")

Note: Reed uses both URL-encoded role names and a `keywords=` query param. URL form: `https://www.reed.co.uk/jobs?keywords={role}&pageno={page}`.

- [ ] **Step 2: Write Reed scraper**

```python
"""Reed.co.uk scraper. Uses JSON-LD when available, DOM fallback."""

from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from core.parser import extract_jsonld_jobpostings
from scrapers.base import BaseScraper
from utils.helpers import clean_text


class ReedScraper(BaseScraper):
    name = "Reed"
    base = "https://www.reed.co.uk"

    def search_url(self, role, page):
        return f"{self.base}/jobs?keywords={quote_plus(role)}&pageno={page}"

    def parse_listings(self, page):
        html = page.content()
        jsonld = extract_jsonld_jobpostings(html)
        if jsonld:
            return [self._from_jsonld(j) for j in jsonld]
        return self._from_dom(html)

    def _from_jsonld(self, j):
        org = j.get("hiringOrganization") or {}
        loc = j.get("jobLocation") or {}
        addr = (loc.get("address") if isinstance(loc, dict) else {}) or {}
        return {
            "title": j.get("title"),
            "company": org.get("name") if isinstance(org, dict) else str(org),
            "location": addr.get("addressLocality") if isinstance(addr, dict) else "",
            "salary": j.get("baseSalary", {}).get("value") if isinstance(j.get("baseSalary"), dict) else "",
            "date_posted": j.get("datePosted"),
            "url": j.get("url"),
            "description": clean_text(j.get("description", "")),
            "employment_type": j.get("employmentType"),
            "shift_text": "",
        }

    def _from_dom(self, html):
        soup = BeautifulSoup(html, "lxml")
        out = []
        for card in soup.select('article[data-id]'):
            a = card.select_one('a[data-element="job_title"]')
            comp = card.select_one('a[data-element="company_name"]')
            loc = card.select_one('li[data-element="location"]')
            sal = card.select_one('li[data-element="salary"]')
            dt = card.select_one('div[data-element="date_posted"]')
            if not a:
                continue
            href = a.get("href", "")
            url = href if href.startswith("http") else f"{self.base}{href}"
            out.append({
                "title": clean_text(a.get_text()),
                "company": clean_text(comp.get_text()) if comp else "",
                "location": clean_text(loc.get_text()) if loc else "",
                "salary": clean_text(sal.get_text()) if sal else "",
                "date_posted": clean_text(dt.get_text()) if dt else "",
                "url": url,
                "description": "",
                "employment_type": "",
                "shift_text": "",
            })
        return out
```

- [ ] **Step 3: Smoke test (live)**

```bash
python -c "from core.playwright_engine import BrowserSession; from scrapers.reed import ReedScraper; \
with __import__('contextlib').nullcontext(BrowserSession(headless=False)) as bs: pass" 
```

Better as a small script — create temporary `_smoke_reed.py`:

```python
from core.playwright_engine import BrowserSession
from scrapers.reed import ReedScraper

with BrowserSession(headless=False) as bs:
    s = ReedScraper(bs)
    out = s.run("Door Supervisor", max_results=5)
    for j in out:
        print(j["title"], "|", j["company"], "|", j["location"])
```

```bash
python _smoke_reed.py
```

Expected: at least 1 job printed. If selectors miss, inspect the live page and update `_from_dom` selectors. Delete `_smoke_reed.py` after.

- [ ] **Step 4: Commit** *(if using git)*

```bash
git add scrapers/reed.py
git commit -m "feat(scrapers): Reed"
```

### Task 4.2: scrapers/indeed.py

**Files:**
- Create: `scrapers/indeed.py`

- [ ] **Step 1: Inspect Indeed UK**

URL pattern: `https://uk.indeed.com/jobs?q={role}&l=London&start={offset}` where offset = (page-1)*10.

Indeed is aggressive about anti-bot — likely needs CAPTCHA solve via `wait_for_human`. The persistent profile will help after first solve.

Listing selector currently: `div.job_seen_beacon` (subject to change). Title: `h2.jobTitle span[title]`. Company: `span.companyName` or `[data-testid="company-name"]`. Location: `[data-testid="text-location"]`. Salary: `[class*="salary-snippet"]`. Date: `span.date`.

- [ ] **Step 2: Write Indeed scraper**

```python
"""Indeed UK scraper. Hostile target — expect CAPTCHAs."""

from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from utils.helpers import clean_text


class IndeedScraper(BaseScraper):
    name = "Indeed"
    base = "https://uk.indeed.com"

    def search_url(self, role, page):
        offset = (page - 1) * 10
        return f"{self.base}/jobs?q={quote_plus(role)}&l=London&start={offset}"

    def parse_listings(self, page):
        soup = BeautifulSoup(page.content(), "lxml")
        out = []
        for card in soup.select("div.job_seen_beacon, li div.cardOutline"):
            title_el = card.select_one("h2.jobTitle span[title]") or card.select_one("h2.jobTitle a")
            comp_el = card.select_one('[data-testid="company-name"]') or card.select_one("span.companyName")
            loc_el = card.select_one('[data-testid="text-location"]') or card.select_one("div.companyLocation")
            sal_el = card.select_one('[class*="salary"]')
            link_el = card.select_one("h2.jobTitle a")
            date_el = card.select_one("span.date")
            if not title_el:
                continue
            href = link_el.get("href", "") if link_el else ""
            url = href if href.startswith("http") else f"{self.base}{href}"
            out.append({
                "title": clean_text(title_el.get("title") or title_el.get_text()),
                "company": clean_text(comp_el.get_text()) if comp_el else "",
                "location": clean_text(loc_el.get_text()) if loc_el else "",
                "salary": clean_text(sal_el.get_text()) if sal_el else "",
                "date_posted": clean_text(date_el.get_text()) if date_el else "",
                "url": url,
                "description": "",
                "employment_type": "",
                "shift_text": "",
            })
        return out
```

- [ ] **Step 3: Smoke test (live, visible)**

Create `_smoke_indeed.py`:

```python
from core.playwright_engine import BrowserSession
from scrapers.indeed import IndeedScraper

with BrowserSession(headless=False) as bs:
    s = IndeedScraper(bs)
    out = s.run("Door Supervisor", max_results=5)
    for j in out:
        print(j["title"], "|", j["company"], "|", j["location"])
```

Run with browser visible. If a CAPTCHA appears, solve in the visible window; the session prompt will wait. Delete file after.

- [ ] **Step 4: Commit** *(if using git)*

```bash
git add scrapers/indeed.py
git commit -m "feat(scrapers): Indeed UK"
```

### Task 4.3: scrapers/cv_library.py

**Files:**
- Create: `scrapers/cv_library.py`

- [ ] **Step 1: Inspect**

URL: `https://www.cv-library.co.uk/search-jobs?keywords={role}&page={page}`. Listing: `div.job`. Title: `a.job__title`. Company: `p.job__details-company`. Location: `p.job__details-location`. Salary: `p.job__details-salary`. Date: `p.job__details-posted`.

- [ ] **Step 2: Write scraper**

```python
"""CV-Library scraper."""

from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from utils.helpers import clean_text


class CvLibraryScraper(BaseScraper):
    name = "CV-Library"
    base = "https://www.cv-library.co.uk"

    def search_url(self, role, page):
        return f"{self.base}/search-jobs?keywords={quote_plus(role)}&page={page}"

    def parse_listings(self, page):
        soup = BeautifulSoup(page.content(), "lxml")
        out = []
        for card in soup.select("div.job, article.job-result"):
            title_el = card.select_one("a.job__title, a.job-result__title")
            comp_el = card.select_one(".job__details-company, .job-result__company")
            loc_el = card.select_one(".job__details-location, .job-result__location")
            sal_el = card.select_one(".job__details-salary, .job-result__salary")
            date_el = card.select_one(".job__details-posted, .job-result__posted")
            if not title_el:
                continue
            href = title_el.get("href", "")
            url = href if href.startswith("http") else f"{self.base}{href}"
            out.append({
                "title": clean_text(title_el.get_text()),
                "company": clean_text(comp_el.get_text()) if comp_el else "",
                "location": clean_text(loc_el.get_text()) if loc_el else "",
                "salary": clean_text(sal_el.get_text()) if sal_el else "",
                "date_posted": clean_text(date_el.get_text()) if date_el else "",
                "url": url,
                "description": "",
                "employment_type": "",
                "shift_text": "",
            })
        return out
```

- [ ] **Step 3: Smoke test**

Same pattern as Reed/Indeed — temp `_smoke_cv.py`, run, delete.

- [ ] **Step 4: Commit** *(if using git)*

```bash
git add scrapers/cv_library.py
git commit -m "feat(scrapers): CV-Library"
```

### Task 4.4: scrapers/totaljobs.py

**Files:**
- Create: `scrapers/totaljobs.py`

- [ ] **Step 1: Inspect**

URL: `https://www.totaljobs.com/jobs/{role-slug}?radius=10&location=london&page={page}`. Or simpler: `https://www.totaljobs.com/jobs?keywords={role}&location=london&page={page}`.

Listing: `div.job, article[data-at="job-item"]`. Title: `a[data-at="job-item-title"]`. Company: `[data-at="job-item-company-name"]`. Location: `[data-at="job-item-location"]`. Salary: `[data-at="job-item-salary"]`. Date: `[data-at="job-item-timeago"]`.

- [ ] **Step 2: Write scraper**

```python
"""Totaljobs scraper."""

from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from utils.helpers import clean_text


class TotaljobsScraper(BaseScraper):
    name = "Totaljobs"
    base = "https://www.totaljobs.com"

    def search_url(self, role, page):
        return f"{self.base}/jobs?keywords={quote_plus(role)}&location=london&page={page}"

    def parse_listings(self, page):
        soup = BeautifulSoup(page.content(), "lxml")
        out = []
        for card in soup.select('article[data-at="job-item"], div.job'):
            title_el = card.select_one('a[data-at="job-item-title"], a.job-title')
            comp_el = card.select_one('[data-at="job-item-company-name"], a.company')
            loc_el = card.select_one('[data-at="job-item-location"], li.location')
            sal_el = card.select_one('[data-at="job-item-salary"], li.salary')
            date_el = card.select_one('[data-at="job-item-timeago"], li.date')
            if not title_el:
                continue
            href = title_el.get("href", "")
            url = href if href.startswith("http") else f"{self.base}{href}"
            out.append({
                "title": clean_text(title_el.get_text()),
                "company": clean_text(comp_el.get_text()) if comp_el else "",
                "location": clean_text(loc_el.get_text()) if loc_el else "",
                "salary": clean_text(sal_el.get_text()) if sal_el else "",
                "date_posted": clean_text(date_el.get_text()) if date_el else "",
                "url": url,
                "description": "",
                "employment_type": "",
                "shift_text": "",
            })
        return out
```

- [ ] **Step 3: Smoke test**

Same pattern. Delete temp file.

- [ ] **Step 4: Commit** *(if using git)*

```bash
git add scrapers/totaljobs.py
git commit -m "feat(scrapers): Totaljobs"
```

### Task 4.5: scrapers/linkedin.py

**Files:**
- Create: `scrapers/linkedin.py`

- [ ] **Step 1: Inspect**

Public job search URL: `https://www.linkedin.com/jobs/search/?keywords={role}&location=London&start={offset}` where offset = (page-1)*25.

Without login the public guest view shows ~25 results per page. Listing selector: `ul.jobs-search__results-list > li` or `div.base-card`. Title: `h3.base-search-card__title`. Company: `h4.base-search-card__subtitle`. Location: `span.job-search-card__location`. Date: `time`. URL: `a.base-card__full-link`.

LinkedIn frequently blocks scraping. If 999 or login wall appears, log and abandon.

- [ ] **Step 2: Write scraper**

```python
"""LinkedIn guest job search. Likely to hit login walls."""

from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from utils.helpers import clean_text


class LinkedInScraper(BaseScraper):
    name = "LinkedIn"
    base = "https://www.linkedin.com"

    def search_url(self, role, page):
        offset = (page - 1) * 25
        return (f"{self.base}/jobs/search/?keywords={quote_plus(role)}"
                f"&location=London&f_TPR=r604800&start={offset}")

    def parse_listings(self, page):
        # If a login modal blocks content, bail.
        if "authwall" in page.url or page.locator('form.sign-in-modal').count():
            self.errlog.warning("LinkedIn auth wall encountered, abandoning")
            return []
        soup = BeautifulSoup(page.content(), "lxml")
        out = []
        for card in soup.select("div.base-card, li.jobs-search__results-list-item"):
            title_el = card.select_one("h3.base-search-card__title")
            comp_el = card.select_one("h4.base-search-card__subtitle")
            loc_el = card.select_one("span.job-search-card__location")
            date_el = card.select_one("time")
            link_el = card.select_one("a.base-card__full-link, a.base-card__full-link--link")
            if not title_el:
                continue
            url = link_el.get("href", "") if link_el else ""
            out.append({
                "title": clean_text(title_el.get_text()),
                "company": clean_text(comp_el.get_text()) if comp_el else "",
                "location": clean_text(loc_el.get_text()) if loc_el else "",
                "salary": "",
                "date_posted": (date_el.get("datetime") if date_el else "") or (clean_text(date_el.get_text()) if date_el else ""),
                "url": url,
                "description": "",
                "employment_type": "",
                "shift_text": "",
            })
        return out
```

- [ ] **Step 3: Smoke test (likely to fail)**

If auth wall blocks, that's expected — error log captures and run continues.

- [ ] **Step 4: Commit** *(if using git)*

```bash
git add scrapers/linkedin.py
git commit -m "feat(scrapers): LinkedIn guest search"
```

### Task 4.6: scrapers/hays.py

**Files:**
- Create: `scrapers/hays.py`

- [ ] **Step 1: Inspect**

URL: `https://www.hays.co.uk/job-search?q={role}&location=London&page={page}`. Listing: `div.search-result`. Title: `h2.job-title a`. Company: not always shown (Hays uses "Our client"). Location: `.location`. Salary: `.salary`. Date: `.date`.

- [ ] **Step 2: Write scraper**

```python
"""Hays Recruitment scraper."""

from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from utils.helpers import clean_text


class HaysScraper(BaseScraper):
    name = "Hays"
    base = "https://www.hays.co.uk"

    def search_url(self, role, page):
        return f"{self.base}/job-search?q={quote_plus(role)}&location=London&page={page}"

    def parse_listings(self, page):
        soup = BeautifulSoup(page.content(), "lxml")
        out = []
        for card in soup.select("div.search-result, li.search-result"):
            title_el = card.select_one("h2 a, h3 a, a.job-title")
            comp_el = card.select_one(".company, .employer")
            loc_el = card.select_one(".location")
            sal_el = card.select_one(".salary")
            date_el = card.select_one(".date, time")
            if not title_el:
                continue
            href = title_el.get("href", "")
            url = href if href.startswith("http") else f"{self.base}{href}"
            out.append({
                "title": clean_text(title_el.get_text()),
                "company": clean_text(comp_el.get_text()) if comp_el else "Hays Client",
                "location": clean_text(loc_el.get_text()) if loc_el else "",
                "salary": clean_text(sal_el.get_text()) if sal_el else "",
                "date_posted": clean_text(date_el.get_text()) if date_el else "",
                "url": url,
                "description": "",
                "employment_type": "",
                "shift_text": "",
            })
        return out
```

- [ ] **Step 3: Smoke test**

Same pattern. Delete temp file.

- [ ] **Step 4: Commit** *(if using git)*

```bash
git add scrapers/hays.py
git commit -m "feat(scrapers): Hays"
```

### Task 4.7: scrapers/randstad.py

**Files:**
- Create: `scrapers/randstad.py`

- [ ] **Step 1: Inspect**

URL: `https://www.randstad.co.uk/jobs/search/?query={role}&location=london&page={page}`. Listing: `article.job-tile` or `li.job-list-item`. Title: `h3 a`. Company: not shown (Randstad is the agency). Location: `.location`. Salary: `.salary`. Date: `.posted-date`.

- [ ] **Step 2: Write scraper**

```python
"""Randstad UK scraper."""

from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from utils.helpers import clean_text


class RandstadScraper(BaseScraper):
    name = "Randstad"
    base = "https://www.randstad.co.uk"

    def search_url(self, role, page):
        return f"{self.base}/jobs/search/?query={quote_plus(role)}&location=london&page={page}"

    def parse_listings(self, page):
        soup = BeautifulSoup(page.content(), "lxml")
        out = []
        for card in soup.select("article.job-tile, li.job-list-item, div.job-card"):
            title_el = card.select_one("h2 a, h3 a, a.job-tile__title-link")
            loc_el = card.select_one(".location, [class*='location']")
            sal_el = card.select_one(".salary, [class*='salary']")
            date_el = card.select_one(".posted-date, time, [class*='date']")
            if not title_el:
                continue
            href = title_el.get("href", "")
            url = href if href.startswith("http") else f"{self.base}{href}"
            out.append({
                "title": clean_text(title_el.get_text()),
                "company": "Randstad Client",
                "location": clean_text(loc_el.get_text()) if loc_el else "",
                "salary": clean_text(sal_el.get_text()) if sal_el else "",
                "date_posted": clean_text(date_el.get_text()) if date_el else "",
                "url": url,
                "description": "",
                "employment_type": "",
                "shift_text": "",
            })
        return out
```

- [ ] **Step 3: Smoke test + commit** *(same pattern)*

### Task 4.8: scrapers/matchtech.py

**Files:**
- Create: `scrapers/matchtech.py`

- [ ] **Step 1: Inspect**

URL: `https://www.matchtech.com/jobs?keywords={role}&location=london&page={page}`. Matchtech is engineering-focused — likely few security results. Selectors similar to other niche boards: `div.job-card` / `article.job`.

- [ ] **Step 2: Write scraper** (same structure as Randstad above, swap `name`, `base`, selectors)

```python
"""Matchtech scraper. Engineering-focused — expect few security results."""

from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from utils.helpers import clean_text


class MatchtechScraper(BaseScraper):
    name = "Matchtech"
    base = "https://www.matchtech.com"

    def search_url(self, role, page):
        return f"{self.base}/jobs?keywords={quote_plus(role)}&location=london&page={page}"

    def parse_listings(self, page):
        soup = BeautifulSoup(page.content(), "lxml")
        out = []
        for card in soup.select("article.job, div.job-card, li.job-result"):
            title_el = card.select_one("h2 a, h3 a, a.job-title")
            comp_el = card.select_one(".company, .employer")
            loc_el = card.select_one(".location")
            sal_el = card.select_one(".salary")
            date_el = card.select_one(".date, time")
            if not title_el:
                continue
            href = title_el.get("href", "")
            url = href if href.startswith("http") else f"{self.base}{href}"
            out.append({
                "title": clean_text(title_el.get_text()),
                "company": clean_text(comp_el.get_text()) if comp_el else "Matchtech Client",
                "location": clean_text(loc_el.get_text()) if loc_el else "",
                "salary": clean_text(sal_el.get_text()) if sal_el else "",
                "date_posted": clean_text(date_el.get_text()) if date_el else "",
                "url": url,
                "description": "",
                "employment_type": "",
                "shift_text": "",
            })
        return out
```

- [ ] **Step 3: Smoke test + commit**

### Task 4.9: scrapers/careerstructure.py

**Files:**
- Create: `scrapers/careerstructure.py`

- [ ] **Step 1: Inspect**

URL: `https://www.careerstructure.com/jobs/{role-slug}?location=london&page={page}` — also accepts `?keywords=`. Construction/engineering board — limited security results.

- [ ] **Step 2: Write scraper** (same template; only `name`, `base`, search URL pattern change)

```python
"""CareerStructure scraper."""

from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from utils.helpers import clean_text


class CareerStructureScraper(BaseScraper):
    name = "CareerStructure"
    base = "https://www.careerstructure.com"

    def search_url(self, role, page):
        return f"{self.base}/jobs?keywords={quote_plus(role)}&location=london&page={page}"

    def parse_listings(self, page):
        soup = BeautifulSoup(page.content(), "lxml")
        out = []
        for card in soup.select("article[data-at='job-item'], div.job, li.job-result"):
            title_el = card.select_one('a[data-at="job-item-title"], h2 a, a.job-title')
            comp_el = card.select_one('[data-at="job-item-company-name"], .company')
            loc_el = card.select_one('[data-at="job-item-location"], .location')
            sal_el = card.select_one('[data-at="job-item-salary"], .salary')
            date_el = card.select_one('[data-at="job-item-timeago"], time, .date')
            if not title_el:
                continue
            href = title_el.get("href", "")
            url = href if href.startswith("http") else f"{self.base}{href}"
            out.append({
                "title": clean_text(title_el.get_text()),
                "company": clean_text(comp_el.get_text()) if comp_el else "",
                "location": clean_text(loc_el.get_text()) if loc_el else "",
                "salary": clean_text(sal_el.get_text()) if sal_el else "",
                "date_posted": clean_text(date_el.get_text()) if date_el else "",
                "url": url,
                "description": "",
                "employment_type": "",
                "shift_text": "",
            })
        return out
```

- [ ] **Step 3: Smoke test + commit**

### Task 4.10: scrapers/ice_recruit.py

**Files:**
- Create: `scrapers/ice_recruit.py`

- [ ] **Step 1: Inspect**

URL: `https://www.icerecruit.com/jobs?q={role}&location=london&page={page}`. Engineering-focused — few results expected.

- [ ] **Step 2: Write scraper**

```python
"""ICE Recruit scraper."""

from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from utils.helpers import clean_text


class IceRecruitScraper(BaseScraper):
    name = "ICE Recruit"
    base = "https://www.icerecruit.com"

    def search_url(self, role, page):
        return f"{self.base}/jobs?q={quote_plus(role)}&location=london&page={page}"

    def parse_listings(self, page):
        soup = BeautifulSoup(page.content(), "lxml")
        out = []
        for card in soup.select("article.job, div.job-card, li.job"):
            title_el = card.select_one("h2 a, h3 a, a.job-title")
            comp_el = card.select_one(".company, .employer")
            loc_el = card.select_one(".location")
            sal_el = card.select_one(".salary")
            date_el = card.select_one(".date, time")
            if not title_el:
                continue
            href = title_el.get("href", "")
            url = href if href.startswith("http") else f"{self.base}{href}"
            out.append({
                "title": clean_text(title_el.get_text()),
                "company": clean_text(comp_el.get_text()) if comp_el else "ICE Recruit Client",
                "location": clean_text(loc_el.get_text()) if loc_el else "",
                "salary": clean_text(sal_el.get_text()) if sal_el else "",
                "date_posted": clean_text(date_el.get_text()) if date_el else "",
                "url": url,
                "description": "",
                "employment_type": "",
                "shift_text": "",
            })
        return out
```

- [ ] **Step 3: Smoke test + commit**

### Task 4.11: scrapers/morson.py

**Files:**
- Create: `scrapers/morson.py`

- [ ] **Step 1: Inspect**

URL: `https://www.morson.com/jobs?keywords={role}&location=london&page={page}`. Same template as above.

- [ ] **Step 2: Write scraper**

```python
"""Morson Group scraper."""

from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from utils.helpers import clean_text


class MorsonScraper(BaseScraper):
    name = "Morson"
    base = "https://www.morson.com"

    def search_url(self, role, page):
        return f"{self.base}/jobs?keywords={quote_plus(role)}&location=london&page={page}"

    def parse_listings(self, page):
        soup = BeautifulSoup(page.content(), "lxml")
        out = []
        for card in soup.select("article.job, div.job-card, li.job-result, div.job"):
            title_el = card.select_one("h2 a, h3 a, a.job-title")
            comp_el = card.select_one(".company, .employer")
            loc_el = card.select_one(".location")
            sal_el = card.select_one(".salary")
            date_el = card.select_one(".date, time")
            if not title_el:
                continue
            href = title_el.get("href", "")
            url = href if href.startswith("http") else f"{self.base}{href}"
            out.append({
                "title": clean_text(title_el.get_text()),
                "company": clean_text(comp_el.get_text()) if comp_el else "Morson Client",
                "location": clean_text(loc_el.get_text()) if loc_el else "",
                "salary": clean_text(sal_el.get_text()) if sal_el else "",
                "date_posted": clean_text(date_el.get_text()) if date_el else "",
                "url": url,
                "description": "",
                "employment_type": "",
                "shift_text": "",
            })
        return out
```

- [ ] **Step 3: Smoke test + commit**

### Task 4.12: scrapers/__init__.py — registry

**Files:**
- Modify: `scrapers/__init__.py`

- [ ] **Step 1: Register all scrapers**

```python
from scrapers.reed import ReedScraper
from scrapers.indeed import IndeedScraper
from scrapers.cv_library import CvLibraryScraper
from scrapers.totaljobs import TotaljobsScraper
from scrapers.linkedin import LinkedInScraper
from scrapers.hays import HaysScraper
from scrapers.randstad import RandstadScraper
from scrapers.matchtech import MatchtechScraper
from scrapers.careerstructure import CareerStructureScraper
from scrapers.ice_recruit import IceRecruitScraper
from scrapers.morson import MorsonScraper

ALL_SCRAPERS = [
    ReedScraper,
    IndeedScraper,
    CvLibraryScraper,
    TotaljobsScraper,
    LinkedInScraper,
    HaysScraper,
    RandstadScraper,
    MatchtechScraper,
    CareerStructureScraper,
    IceRecruitScraper,
    MorsonScraper,
]
```

- [ ] **Step 2: Smoke**

```bash
python -c "from scrapers import ALL_SCRAPERS; print(len(ALL_SCRAPERS), [s.name for s in ALL_SCRAPERS])"
```

Expected: `11 ['Reed', 'Indeed', 'CV-Library', 'Totaljobs', 'LinkedIn', 'Hays', 'Randstad', 'Matchtech', 'CareerStructure', 'ICE Recruit', 'Morson']`

- [ ] **Step 3: Commit** *(if using git)*

```bash
git add scrapers/__init__.py
git commit -m "feat(scrapers): registry of all 11 site scrapers"
```

---

## Phase 5: Orchestrator

### Task 5.1: main.py — pipeline, no CLI yet

**Files:**
- Create: `main.py`

- [ ] **Step 1: Write orchestrator**

```python
"""Entry point: run all scrapers across all roles, filter, dedupe, rank, write TXT."""

import argparse
import sys
import time
import traceback
from datetime import datetime

from config import OUTPUT_DIR, OUTPUT_FILENAME_FMT, PER_SITE_CAP, TARGET_ROLES
from core.dedupe import dedupe
from core.filter import (
    classify_rota, passes_exclusions, passes_location, passes_night_shift,
    passes_recency, passes_sia_explicit,
)
from core.location import commute_estimate, postcode_prefix
from core.playwright_engine import BrowserSession
from core.ranking import rank
from scrapers import ALL_SCRAPERS
from utils.helpers import normalise_date, parse_salary
from utils.logger import get_logger

log = get_logger("main")


def enrich(job):
    """Normalise scraped fields into a consistent shape."""
    smin, smax = parse_salary(job.get("salary"))
    job["salary_min"] = smin
    job["salary_max"] = smax
    job["date_posted_parsed"] = normalise_date(job.get("date_posted"))
    text_blob = " ".join(str(job.get(k, "")) for k in
                         ("title", "description", "shift_text", "employment_type"))
    job["_text"] = text_blob
    job["rota"] = classify_rota(text_blob)
    prefix = postcode_prefix(job.get("location"))
    job["commute"] = commute_estimate(prefix) if prefix else "Unknown"
    return job


def apply_filters(jobs, counters):
    kept = []
    for j in jobs:
        if not passes_recency(j["date_posted_parsed"]):
            counters["recency"] += 1
            continue
        if not passes_location(j.get("location")):
            counters["location"] += 1
            continue
        if not passes_night_shift(j["_text"]):
            counters["shift"] += 1
            continue
        if not passes_sia_explicit(j["_text"]):
            counters["sia"] += 1
            continue
        if not passes_exclusions(j["_text"]):
            counters["exclusion"] += 1
            continue
        kept.append(j)
    return kept


def write_output(jobs):
    fname = datetime.now().strftime(OUTPUT_FILENAME_FMT)
    path = OUTPUT_DIR / fname
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for j in jobs:
            dp = j["date_posted_parsed"]
            dp_str = dp.strftime("%d/%m/%Y") if dp else "Unknown"
            salary = j.get("salary") or (
                f"£{j['salary_min']:,} - £{j['salary_max']:,}"
                if j.get("salary_min") else "Not specified"
            )
            emp = j.get("employment_type") or "Permanent"
            block = (
                f" * Company: {j.get('company') or 'Unknown'}\n"
                f" * Job Title: {j.get('title') or ''}\n"
                f" * Date Posted: {dp_str}\n"
                f" * Shift Type: Night\n"
                f" * Rota: {j.get('rota', 'Unknown')}\n"
                f" * Employment Type: {emp}\n"
                f" * Salary: {salary}\n"
                f" * Location: {j.get('location') or ''}\n"
                f" * Commute Estimate: {j.get('commute', 'Unknown')}\n"
                f" * Source Website: {j.get('source') or 'Unknown'}\n"
                f" * Application URL: {j.get('url') or ''}\n\n"
            )
            f.write(block)
    return path


def run(roles, scrapers, headless=True, per_site_cap=PER_SITE_CAP):
    started = time.time()
    raw = []
    counters = {"recency": 0, "location": 0, "shift": 0, "sia": 0, "exclusion": 0}

    with BrowserSession(headless=headless) as bs:
        for role in roles:
            log.info(f"=== ROLE: {role} ===")
            for ScraperCls in scrapers:
                s = ScraperCls(bs)
                try:
                    raw.extend(s.run(role, max_results=per_site_cap))
                except Exception as e:
                    log.error(f"{s.name} failed for {role}: {e}")
                    s.errlog.error(traceback.format_exc())

        failed_navs = bs.failed_navigations

    log.info(f"Raw collected: {len(raw)}")
    enriched = [enrich(j) for j in raw]
    filtered = apply_filters(enriched, counters)
    log.info(f"After filter: {len(filtered)}")
    pre_dedupe = len(filtered)
    deduped = dedupe(filtered)
    dups_removed = pre_dedupe - len(deduped)
    log.info(f"After dedupe: {len(deduped)} (removed {dups_removed})")
    ranked = rank(deduped)

    out_path = write_output(ranked)
    elapsed = time.time() - started

    print()
    print(f"Total jobs found: {len(raw)}")
    print(f"Accepted: {len(ranked)}")
    print(f"Rejected by filter: {sum(counters.values())} "
          f"(recency={counters['recency']}, location={counters['location']}, "
          f"shift={counters['shift']}, SIA={counters['sia']}, "
          f"exclusion={counters['exclusion']})")
    print(f"Duplicates removed: {dups_removed}")
    print(f"Failed page loads: {failed_navs}")
    print(f"Execution time: {time.strftime('%H:%M:%S', time.gmtime(elapsed))}")
    print(f"Output: {out_path}")


if __name__ == "__main__":
    run(TARGET_ROLES, ALL_SCRAPERS)
```

- [ ] **Step 2: Importability smoke**

```bash
python -c "import main; print('main loads OK')"
```

Expected: `main loads OK`

- [ ] **Step 3: Commit** *(if using git)*

```bash
git add main.py
git commit -m "feat(main): orchestrator + pipeline + TXT output"
```

### Task 5.2: main.py — CLI flags

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Replace the `if __name__ == "__main__":` block**

Replace the existing block at the bottom of `main.py` with:

```python
def _filter_scrapers(names_csv):
    if not names_csv:
        return ALL_SCRAPERS
    wanted = {n.strip().lower() for n in names_csv.split(",")}
    return [s for s in ALL_SCRAPERS if s.name.lower() in wanted]


def _filter_roles(roles_csv):
    if not roles_csv:
        return TARGET_ROLES
    return [r.strip() for r in roles_csv.split(",")]


def main():
    ap = argparse.ArgumentParser(description="Night security job aggregator.")
    ap.add_argument("--visible", action="store_true",
                    help="Show browser window (enables manual CAPTCHA solve).")
    ap.add_argument("--dry-run", action="store_true",
                    help="Run filter/dedupe/rank against tests/fixture.json, no network.")
    ap.add_argument("--sites", default="",
                    help="Comma-separated scraper names (e.g. reed,indeed). Default: all.")
    ap.add_argument("--roles", default="",
                    help="Comma-separated role keywords. Default: all 8 target roles.")
    args = ap.parse_args()

    if args.dry_run:
        _dry_run()
        return

    run(
        roles=_filter_roles(args.roles),
        scrapers=_filter_scrapers(args.sites),
        headless=not args.visible,
    )


def _dry_run():
    import json
    from pathlib import Path
    fixture = Path(__file__).parent / "tests" / "fixture.json"
    if not fixture.exists():
        print(f"No fixture at {fixture}. Create one with sample raw jobs.")
        sys.exit(1)
    raw = json.loads(fixture.read_text(encoding="utf-8"))
    counters = {"recency": 0, "location": 0, "shift": 0, "sia": 0, "exclusion": 0}
    enriched = [enrich(j) for j in raw]
    filtered = apply_filters(enriched, counters)
    deduped = dedupe(filtered)
    ranked = rank(deduped)
    out_path = write_output(ranked)
    print(f"Dry-run: {len(raw)} raw → {len(ranked)} accepted → {out_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: CLI smoke**

```bash
python main.py --help
```

Expected: argparse help showing `--visible`, `--dry-run`, `--sites`, `--roles`.

- [ ] **Step 3: Commit** *(if using git)*

```bash
git add main.py
git commit -m "feat(main): CLI flags (--visible, --dry-run, --sites, --roles)"
```

### Task 5.3: tests/fixture.json for dry-run

**Files:**
- Create: `tests/fixture.json`
- Create: `tests/__init__.py` (empty)

- [ ] **Step 1: Write minimal fixture**

```bash
mkdir -p tests
```

Create `tests/__init__.py` empty. Create `tests/fixture.json`:

```json
[
  {
    "source": "Reed",
    "title": "Door Supervisor - Static Corporate Site",
    "company": "Acme Security Ltd",
    "location": "London SE1 4AB",
    "salary": "£32,000 - £36,000",
    "date_posted": "2 days ago",
    "url": "https://reed.co.uk/jobs/12345",
    "description": "Permanent night shift role. 4 on 4 off. Must hold valid SIA Licence (Door Supervisor). Static site at corporate HQ.",
    "employment_type": "Permanent",
    "shift_text": "Nights only, 4 on 4 off"
  },
  {
    "source": "Indeed",
    "title": "Event Steward",
    "company": "FestivalSec",
    "location": "Reading",
    "salary": "£12/hr",
    "date_posted": "Yesterday",
    "url": "https://indeed.com/jobs/9999",
    "description": "Festival security work, weekends only. Zero hours contract.",
    "employment_type": "Casual",
    "shift_text": "Variable"
  },
  {
    "source": "CV-Library",
    "title": "Night Concierge",
    "company": "Concierge London",
    "location": "Croydon CR0 2AA",
    "salary": "£28k",
    "date_posted": "1 week ago",
    "url": "https://cv-library.co.uk/job/55555",
    "description": "Front desk security at residential block. SIA Door Supervisor licence required. Permanent night shifts.",
    "employment_type": "Permanent",
    "shift_text": "Permanent nights"
  }
]
```

- [ ] **Step 2: Run dry-run**

```bash
python main.py --dry-run
```

Expected: `Dry-run: 3 raw → 2 accepted → output\<timestamp> - Door Supervisor Job Search.txt` (Event Steward rejected by exclusion + non-target location).

- [ ] **Step 3: Inspect output TXT**

Open the generated file. Verify two job blocks present with the exact bullet format. Verify the Croydon job comes second (SE > CR by priority).

- [ ] **Step 4: Commit** *(if using git)*

```bash
git add tests/__init__.py tests/fixture.json
git commit -m "test(fixture): minimal fixture for --dry-run validation"
```

---

## Phase 6: First real run + iteration

### Task 6.1: Smallest real run

**Files:** None modified

- [ ] **Step 1: Run a tight live scan**

Start with **one role**, **one site**, **visible mode**. Once that works, expand.

```bash
python main.py --visible --roles "Door Supervisor" --sites reed
```

- [ ] **Step 2: Inspect results**

Watch the browser. Check that:
- Cookie banner gets dismissed
- Listings extract (the run log will show `Reed role='Door Supervisor' collected=N`)
- Filter funnel makes sense (numbers add up roughly)
- TXT file is well-formed

- [ ] **Step 3: If selectors miss, fix and rerun**

Open browser DevTools on the Reed search page. Compare actual DOM against `scrapers/reed.py` selectors. Update + rerun.

### Task 6.2: Widen to all core 4

```bash
python main.py --visible --roles "Door Supervisor" --sites reed,indeed,cv-library,totaljobs
```

Iterate on per-scraper selector fixes until all 4 produce results.

### Task 6.3: Full unattended run

```bash
python main.py
```

Headless, all 8 roles × 11 sites. Expect 30–60 min. Sites that fail (LinkedIn auth wall most likely) get logged and skipped.

- [ ] **Step 1: Review final TXT**

Open `output/<timestamp> - Door Supervisor Job Search.txt`. Verify ordering, no duplicates, format matches spec exactly.

- [ ] **Step 2: Review summary numbers**

Sanity-check: rejected counts should sum to (raw - accepted - duplicates_removed) approximately.

- [ ] **Step 3: Final commit** *(if using git)*

```bash
git add -A
git commit -m "chore: first full live run validated"
```

---

## Self-review notes

**Spec coverage:** all 8 spec sections (project layout, decisions, data flow, component contracts, CLI, rota, output, summary, error handling, anti-bot, testing) map to plan tasks. Task 5.3 covers the fixture mentioned in spec section "Testing approach".

**Known plan softness:**
- Scrapers 4.1–4.11 ship with **best-guess selectors based on current public DOM patterns**. Each site routinely changes markup, so the smoke-test step in each task is where selectors get verified and corrected. Plan deliberately budgets selector iteration into Phase 6, not Phase 4.
- LinkedIn (4.5) is most likely to never return useful results without authentication. Acceptable per spec's "isolate failures" rule.
- The salary parser in Task 1.4 treats hourly rates as `(None, None)` rather than annualising — keeps ranking honest, hourly roles still surface if they pass all other filters.
- `Employment Type` in output defaults to "Permanent" when scraped value is empty — assumption justified because zero-hours/casual roles get rejected by exclusion filter before reaching the writer.
