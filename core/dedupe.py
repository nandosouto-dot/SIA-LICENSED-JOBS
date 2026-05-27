"""Fuzzy deduplication across raw scraped jobs."""

from urllib.parse import urlparse, urlunparse
from rapidfuzz import fuzz


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
            # Fuzzy match only when BOTH sides have non-empty title and company.
            # rapidfuzz.WRatio('', '') returns 100, which would falsely dedupe
            # two jobs with blank fields. Defensive guard.
            kept_title = (kept.get("title") or "").strip()
            kept_company = (kept.get("company") or "").strip()
            if not (title and company and kept_title and kept_company):
                continue
            if (
                fuzz.WRatio(title, kept_title) >= 90
                and fuzz.WRatio(company, kept_company) >= 95
            ):
                is_dup = True
                break
        if not is_dup:
            out.append(job)
    return out


if __name__ == "__main__":
    assert canonical_url("https://reed.co.uk/jobs/123?utm=x") == "https://reed.co.uk/jobs/123"
    assert canonical_url("https://reed.co.uk/jobs/123/") == "https://reed.co.uk/jobs/123"
    assert canonical_url("https://reed.co.uk/jobs/123#section") == "https://reed.co.uk/jobs/123"
    assert canonical_url("") == ""
    assert canonical_url(None) == ""

    jobs = [
        {"title": "Door Supervisor", "company": "Acme Security", "url": "https://reed.co.uk/jobs/1?utm=x"},
        {"title": "Door Supervisor", "company": "Acme Security", "url": "https://reed.co.uk/jobs/1"},
        {"title": "Door Supervisor Nights", "company": "Acme Security Ltd", "url": "https://other.com/2"},
        {"title": "Night Concierge", "company": "Different Co", "url": "https://other.com/3"},
    ]
    out = dedupe(jobs)
    assert len(out) == 2, [j["url"] for j in out]

    # Fix D: two jobs with blank title+company must NOT collapse into one
    blanks = [
        {"title": "", "company": "", "url": "https://a.com/1"},
        {"title": "", "company": "", "url": "https://b.com/2"},
    ]
    assert len(dedupe(blanks)) == 2, "blank-field jobs falsely deduped"
    print("dedupe OK")
