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
