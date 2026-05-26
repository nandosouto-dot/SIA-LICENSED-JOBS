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
