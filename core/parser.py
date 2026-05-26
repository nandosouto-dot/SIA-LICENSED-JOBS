"""HTML / JSON-LD extraction helpers."""

import json
from bs4 import BeautifulSoup


def extract_jsonld_jobpostings(html):
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    out = []
    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or "")
        except Exception:
            continue
        for entry in (data if isinstance(data, list) else [data]):
            if isinstance(entry, dict) and entry.get("@type") == "JobPosting":
                out.append(entry)
    return out


if __name__ == "__main__":
    html = '''
    <html><head>
    <script type="application/ld+json">
    {"@type":"JobPosting","title":"Door Supervisor","hiringOrganization":{"name":"Acme Sec"},"jobLocation":{"address":{"addressLocality":"London SE1"}},"datePosted":"2026-05-20"}
    </script>
    <script type="application/ld+json">[
      {"@type":"JobPosting","title":"Night Concierge","hiringOrganization":"BigCorp"},
      {"@type":"Other","title":"ignore me"}
    ]</script>
    </head></html>
    '''
    out = extract_jsonld_jobpostings(html)
    titles = sorted(j.get("title") for j in out)
    assert titles == ["Door Supervisor", "Night Concierge"], titles
    print("parser OK")
