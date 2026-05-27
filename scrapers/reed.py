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
        salary = ""
        bs = j.get("baseSalary")
        if isinstance(bs, dict):
            val = bs.get("value")
            if isinstance(val, dict):
                lo, hi = val.get("minValue"), val.get("maxValue")
                if lo and hi:
                    salary = f"{lo} - {hi}"
                elif lo:
                    salary = str(lo)
            elif val:
                salary = str(val)
        return {
            "title": j.get("title"),
            "company": org.get("name") if isinstance(org, dict) else str(org),
            "location": addr.get("addressLocality") if isinstance(addr, dict) else "",
            "salary": salary,
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
            comp = card.select_one('a[data-element="recruiter"]')
            loc = card.select_one('li[data-qa="job-metadata-location"]')
            sal = card.select_one('li[data-qa="job-metadata-salary"]')
            posted_by = card.select_one('div[data-qa="job-posted-by"]')
            # "Posted by" text format: "22 April by Gold Group Ltd" or "Yesterday by X"
            date_posted = ""
            if posted_by:
                pb_text = clean_text(posted_by.get_text(" "))
                if " by " in pb_text:
                    date_posted = pb_text.split(" by ", 1)[0].strip()
                else:
                    date_posted = pb_text
            # Employment type: 3rd li in metadata (no data-qa) — "Permanent, full-time" etc.
            emp_type = ""
            metadata_lis = card.select('ul[data-qa="job-metadata"] > li')
            for li in metadata_lis:
                if not li.get("data-qa"):
                    emp_type = clean_text(li.get_text())
                    break
            if not a:
                continue
            href = a.get("href", "")
            url = href if href.startswith("http") else f"{self.base}{href}"
            out.append({
                "title": clean_text(a.get_text()),
                "company": clean_text(comp.get_text()) if comp else "",
                "location": clean_text(loc.get_text()) if loc else "",
                "salary": clean_text(sal.get_text()) if sal else "",
                "date_posted": date_posted,
                "url": url,
                "description": "",
                "employment_type": emp_type,
                "shift_text": "",
            })
        return out
