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
