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
