"""Date / salary / text helpers."""

import random
import re
import time
from datetime import date, datetime, timedelta
from html import unescape

from bs4 import BeautifulSoup


def normalise_date(raw):
    if not raw:
        return None
    text = str(raw).strip().lower()
    today = date.today()
    if not text:
        return None
    if "just now" in text or "today" in text or "minute" in text or "hour" in text:
        return today
    if "yesterday" in text:
        return today - timedelta(days=1)
    m = re.search(r"(\d+)\s*(day|week|month|year)s?\s*ago", text)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        days = {"day": 1, "week": 7, "month": 30, "year": 365}[unit]
        return today - timedelta(days=n * days)
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.match(r"(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})", text)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        try:
            return date(y, mo, d)
        except ValueError:
            return None
    return None


def parse_salary(raw):
    if not raw:
        return (None, None)
    text = str(raw).lower().replace(",", "").replace("£", "").strip()
    if not text or "competitive" in text or "negotiable" in text:
        return (None, None)
    matches = re.findall(r"(\d+(?:\.\d+)?)(k?)", text)
    nums = []
    for n, k in matches:
        v = float(n) * (1000 if k == "k" else 1)
        if v >= 1000:
            nums.append(int(v))
    if not nums:
        return (None, None)
    if len(nums) == 1:
        return (nums[0], nums[0])
    return (min(nums), max(nums))


def clean_text(raw):
    if not raw:
        return ""
    text = unescape(str(raw))
    if "<" in text and ">" in text:
        text = BeautifulSoup(text, "lxml").get_text(" ")
    return " ".join(text.split())


def random_delay(min_ms, max_ms):
    """Sleep for a random duration in [min_ms, max_ms] milliseconds."""
    time.sleep(random.uniform(min_ms / 1000, max_ms / 1000))


if __name__ == "__main__":
    today = date.today()

    # normalise_date
    assert normalise_date("Posted today") == today
    assert normalise_date("Yesterday") == today - timedelta(days=1)
    assert normalise_date("2 days ago") == today - timedelta(days=2)
    assert normalise_date("Posted 3 hours ago") == today
    assert normalise_date("Posted just now") == today
    assert normalise_date("1 week ago") == today - timedelta(days=7)
    assert normalise_date("12/05/2026") == date(2026, 5, 12)
    assert normalise_date("12-05-2026") == date(2026, 5, 12)
    assert normalise_date("2026-05-12") == date(2026, 5, 12)
    assert normalise_date("2026-05-12T08:30:00Z") == date(2026, 5, 12)
    assert normalise_date("") is None
    assert normalise_date(None) is None
    assert normalise_date("blah") is None
    print("normalise_date OK")

    # parse_salary
    assert parse_salary("£28,000 - £32,000 per annum") == (28000, 32000)
    assert parse_salary("£14.50 per hour") == (None, None)
    assert parse_salary("28000 to 32000") == (28000, 32000)
    assert parse_salary("£30k") == (30000, 30000)
    assert parse_salary("£30k - £35k") == (30000, 35000)
    assert parse_salary("Competitive") == (None, None)
    assert parse_salary("") == (None, None)
    assert parse_salary(None) == (None, None)
    print("parse_salary OK")

    # clean_text
    assert clean_text("  Hello\n\n  world  ") == "Hello world"
    assert clean_text("<p>Foo &amp; bar</p>") == "Foo & bar"
    assert clean_text("") == ""
    assert clean_text(None) == ""
    print("clean_text OK")
