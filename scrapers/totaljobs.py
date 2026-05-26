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
