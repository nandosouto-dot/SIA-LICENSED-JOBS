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

    def fetch_description(self, url: str) -> str:
        """Pass 2: navigate to a job's URL and pull the full description.

        Default impl: extract JSON-LD JobPosting.description if present, else
        fall back to <body> text via BeautifulSoup. Subclasses may override
        for sites with idiosyncratic detail pages.
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
        for j in extract_jsonld_jobpostings(html):
            desc = j.get("description")
            if desc:
                return clean_text(desc)
        soup = BeautifulSoup(html, "lxml")
        # Heuristic: grab the largest text block on the page.
        main = soup.select_one('main') or soup.select_one('article') or soup.body
        return clean_text(main.get_text(" ") if main else "")

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
