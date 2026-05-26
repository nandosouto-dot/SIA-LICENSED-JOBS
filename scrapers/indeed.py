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
