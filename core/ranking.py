"""Composite ranking score for filtered jobs."""

from config import POSTCODE_PRIORITY, ROLE_BOOST_KEYWORDS
from core.location import postcode_prefix


def score(job):
    s = 0.0
    prefix = postcode_prefix(job.get("location"))
    if prefix in POSTCODE_PRIORITY:
        s += (len(POSTCODE_PRIORITY) - POSTCODE_PRIORITY.index(prefix)) * 1000

    smin = job.get("salary_min") or 0
    smax = job.get("salary_max") or smin
    s += (smin + smax) / 2 / 100

    text = ((job.get("title") or "") + " " + (job.get("description") or "")).lower()
    for kw in ROLE_BOOST_KEYWORDS:
        if kw in text:
            s += 50

    return s


def rank(jobs):
    return sorted(jobs, key=score, reverse=True)


if __name__ == "__main__":
    j1 = {"location": "London SE1", "salary_min": 35000, "title": "Static Security"}
    j2 = {"location": "Bromley BR1", "salary_min": 30000, "title": "Door Supervisor"}
    j3 = {"location": "Manchester M1", "salary_min": 40000, "title": "Concierge Security"}
    assert score(j1) > score(j2)
    assert score(j1) > score(j3)
    ranked = rank([j2, j3, j1])
    assert ranked[0] == j1
    print("ranking OK")
