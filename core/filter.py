"""Filter pipeline for raw scraped jobs."""

import re
from datetime import date, timedelta

from config import (
    DAY_KEYWORDS, EXCLUSION_KEYWORDS, LONDON_AREA_KEYWORDS, MAX_COMMUTE_MIN,
    NIGHT_KEYWORDS, POSTCODE_PRIORITY, RECENCY_DAYS,
    ROTA_4_ON_4_OFF_PATTERNS, SIA_KEYWORDS, TITLE_SECURITY_PATTERN,
)
from core.location import commute_minutes_upper, in_target_area, postcode_prefix

_TITLE_SECURITY_RE = re.compile(TITLE_SECURITY_PATTERN, re.IGNORECASE)


def _lower(t):
    return (t or "").lower()


def passes_recency(date_posted, max_age_days=RECENCY_DAYS):
    if not date_posted:
        return False
    delta = (date.today() - date_posted).days
    return 0 <= delta <= max_age_days


def passes_title_security(title):
    """Cheap title-only check: must mention security/door/concierge/guard/etc."""
    if not title:
        return False
    return bool(_TITLE_SECURITY_RE.search(title))


def passes_location(location_text):
    if not location_text:
        return False
    # First try postcode-based matching (most precise).
    prefix = postcode_prefix(location_text)
    if prefix:
        if in_target_area(prefix):
            return True
        if commute_minutes_upper(prefix) <= MAX_COMMUTE_MIN:
            return True
    # Fallback: many scraped listings show city/area names with no postcode
    # (e.g. "Sidcup, Kent"). Accept if any London-area keyword appears.
    t = location_text.lower()
    return any(kw in t for kw in LONDON_AREA_KEYWORDS)


def passes_night_shift(text):
    t = _lower(text)
    if not t:
        return False
    has_night = any(k in t for k in NIGHT_KEYWORDS) or "night" in t
    has_day_only = any(k in t for k in DAY_KEYWORDS)
    return has_night and not has_day_only


def passes_sia_explicit(text):
    t = _lower(text)
    return any(k in t for k in SIA_KEYWORDS)


def passes_exclusions(text):
    """Returns True if job PASSES (no exclusion words present)."""
    t = _lower(text)
    return not any(k in t for k in EXCLUSION_KEYWORDS)


def classify_rota(text):
    t = _lower(text)
    for pat in ROTA_4_ON_4_OFF_PATTERNS:
        if re.search(pat, t):
            return "4-on-4-off"
    if re.search(r"\d\s*on\s*\d\s*off", t):
        return "Other"
    return "Unknown"


if __name__ == "__main__":
    today = date.today()

    assert passes_recency(today) is True
    assert passes_recency(today - timedelta(days=3)) is True
    assert passes_recency(today - timedelta(days=10)) is False
    assert passes_recency(None) is False

    assert passes_location("London SE1 4AB") is True
    assert passes_location("Croydon CR0") is True
    assert passes_location("Manchester M1") is False
    assert passes_location("") is False

    # Title pre-filter — keep security/door/concierge/guard, drop everything else
    assert passes_title_security("Security Officer") is True
    assert passes_title_security("Door Supervisor") is True
    assert passes_title_security("Night Concierge") is True
    assert passes_title_security("Static Security Guard") is True
    assert passes_title_security("Gatehouse Security") is True
    assert passes_title_security("SIA Temp Receptionist") is True
    assert passes_title_security("Lifeguard - Flexible") is False  # guard inside lifeguard
    assert passes_title_security("Housekeeping Supervisor") is False
    assert passes_title_security("Cafe Supervisor Monday - Friday") is False
    assert passes_title_security("Van Driver") is False
    assert passes_title_security("") is False
    assert passes_title_security(None) is False

    assert passes_night_shift("Permanent nights, 4 on 4 off") is True
    assert passes_night_shift("Day shift only, 9-5") is False
    assert passes_night_shift("Mon-Fri office hours") is False
    assert passes_night_shift("") is False
    assert passes_night_shift("rotating day/night") is True  # exclusion catches later

    assert passes_sia_explicit("Must hold valid SIA Licence") is True
    assert passes_sia_explicit("Door Supervisor licence required") is True
    assert passes_sia_explicit("Highfield Level 2 Door Supervisor preferred") is True
    assert passes_sia_explicit("Security experience preferred") is False

    assert passes_exclusions("Zero hours contract") is False
    assert passes_exclusions("Event security, festival work") is False
    assert passes_exclusions("Self-employed door supervisor") is False
    assert passes_exclusions("Permanent night role at static site") is True

    assert classify_rota("4 on 4 off shifts") == "4-on-4-off"
    assert classify_rota("Four on four off pattern") == "4-on-4-off"
    assert classify_rota("3 on 3 off rota") == "Other"
    assert classify_rota("no shift info") == "Unknown"

    print("filter OK")
