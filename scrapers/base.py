"""Abstract scraper. Subclasses implement search_url + parse_listings."""

from abc import ABC, abstractmethod

from bs4 import BeautifulSoup

from config import PER_SITE_CAP
from core.parser import extract_jsonld_jobpostings
from utils.helpers import clean_text
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

    # Selectors tried in order on the per-job page, narrowest first.
    # Avoid scraping the whole page so footer/nav text doesn't pollute the
    # SIA / night-shift / exclusion keyword checks.
    _DESC_SELECTORS = (
        '[itemprop="description"]',
        '[data-qa*="description" i]',
        '[data-testid*="description" i]',
        '[class*="job-description" i]',
        '[class*="description" i]',
        '[id*="description" i]',
        'section.description',
        'div.description',
        'main',
        'article',
    )

    # Hard cap on description text length to keep filter checks honest.
    # Real job descriptions rarely exceed ~6k chars; anything bigger is page chrome.
    _DESC_MAX_CHARS = 8000

    def fetch_description(self, url: str) -> str:
        """Pass 2: navigate to a job's URL and pull the full description.

        Order of preference: JSON-LD JobPosting.description → narrow content
        selectors → <main>/<article> → <body>. Output is capped at
        ``_DESC_MAX_CHARS`` so footer/nav noise can't trigger false-positive
        keyword matches downstream.
        """
        if not url:
            return ""
        try:
            self.engine.goto(url)
            self.engine.dismiss_cookies()
            if self.engine.detect_captcha():
                self.engine.wait_for_human(self.name)
            html = self.engine.page.content()
        except Exception as e:
            self.errlog.warning(f"fetch_description {url}: {e}")
            return ""
        # Prefer structured data (JSON-LD JobPosting).
        for j in extract_jsonld_jobpostings(html):
            desc = j.get("description")
            if desc:
                return clean_text(desc)[: self._DESC_MAX_CHARS]
        # DOM fallback — narrowest selector first.
        soup = BeautifulSoup(html, "lxml")
        for sel in self._DESC_SELECTORS:
            el = soup.select_one(sel)
            if el:
                text = clean_text(el.get_text(" "))
                if text:
                    return text[: self._DESC_MAX_CHARS]
        # Last resort: body text (rare).
        body_text = clean_text(soup.body.get_text(" ") if soup.body else "")
        return body_text[: self._DESC_MAX_CHARS]

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
