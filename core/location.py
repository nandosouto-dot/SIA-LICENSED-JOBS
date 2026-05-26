"""Postcode-prefix matching + commute hint."""

import re

from config import COMMUTE_ESTIMATES, MAX_COMMUTE_MIN, POSTCODE_PRIORITY

_PREFIX_RE = re.compile(r"\b([A-Z]{1,2})\d", re.IGNORECASE)


def postcode_prefix(location_text):
    if not location_text:
        return None
    m = _PREFIX_RE.search(str(location_text))
    return m.group(1).upper() if m else None


def in_target_area(prefix):
    if not prefix:
        return False
    return prefix in POSTCODE_PRIORITY


def commute_estimate(prefix):
    return COMMUTE_ESTIMATES.get(prefix, "Unknown")


def commute_minutes_upper(prefix):
    """Upper bound of the commute estimate in minutes, or 999 if unknown."""
    est = COMMUTE_ESTIMATES.get(prefix)
    if not est:
        return 999
    nums = [int(n) for n in re.findall(r"\d+", est)]
    return max(nums) if nums else 999


if __name__ == "__main__":
    assert postcode_prefix("London SE1 4AB") == "SE"
    assert postcode_prefix("Croydon CR0") == "CR"
    assert postcode_prefix("Bromley, BR1 2XY") == "BR"
    assert postcode_prefix("Manchester M1 4BT") == "M"
    assert postcode_prefix("No postcode here") is None
    assert postcode_prefix("") is None
    assert postcode_prefix(None) is None

    assert in_target_area("SE") is True
    assert in_target_area("SW") is True
    assert in_target_area("M") is False
    assert in_target_area(None) is False

    assert commute_estimate("SE") == "20-40 min"
    assert commute_estimate("ZZ") == "Unknown"

    assert commute_minutes_upper("SE") == 40
    assert commute_minutes_upper("ZZ") == 999
    print("location OK")
