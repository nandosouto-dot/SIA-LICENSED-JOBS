"""Entry point: run all scrapers across all roles, filter, dedupe, rank, write TXT."""

import argparse
import sys
import time
import traceback
from datetime import datetime

from config import OUTPUT_DIR, OUTPUT_FILENAME_FMT, PER_SITE_CAP, TARGET_ROLES
from core.dedupe import dedupe
from core.filter import (
    classify_rota, passes_exclusions, passes_location, passes_night_shift,
    passes_recency, passes_sia_explicit, passes_title_security,
)
from core.location import commute_estimate, postcode_prefix
from core.playwright_engine import BrowserSession
from core.ranking import rank
from scrapers import ALL_SCRAPERS
from utils.helpers import normalise_date, parse_salary
from utils.logger import get_logger

log = get_logger("main")


def enrich(job):
    """Normalise scraped fields into a consistent shape."""
    smin, smax = parse_salary(job.get("salary"))
    job["salary_min"] = smin
    job["salary_max"] = smax
    job["date_posted_parsed"] = normalise_date(job.get("date_posted"))
    text_blob = " ".join(str(job.get(k, "")) for k in
                         ("title", "description", "shift_text", "employment_type"))
    job["_text"] = text_blob
    job["rota"] = classify_rota(text_blob)
    prefix = postcode_prefix(job.get("location"))
    job["commute"] = commute_estimate(prefix) if prefix else "Unknown"
    return job


def apply_cheap_filters(jobs, counters):
    """Filter on fields available from search results (no per-job page fetch needed).

    Order matters: cheapest rejections first to minimise wasted work.
    """
    kept = []
    for j in jobs:
        if not passes_title_security(j.get("title")):
            counters["title"] += 1
            continue
        if not passes_recency(j["date_posted_parsed"]):
            counters["recency"] += 1
            continue
        if not passes_location(j.get("location")):
            counters["location"] += 1
            continue
        kept.append(j)
    return kept


def apply_expensive_filters(jobs, counters):
    """Filter on fields requiring the full job description (post Pass 2 fetch)."""
    kept = []
    for j in jobs:
        # Rebuild text blob now that description is populated.
        j["_text"] = " ".join(str(j.get(k, "")) for k in
                              ("title", "description", "shift_text", "employment_type"))
        j["rota"] = classify_rota(j["_text"])
        if not passes_night_shift(j["_text"]):
            counters["shift"] += 1
            continue
        if not passes_sia_explicit(j["_text"]):
            counters["sia"] += 1
            continue
        if not passes_exclusions(j["_text"]):
            counters["exclusion"] += 1
            continue
        kept.append(j)
    return kept


def write_output(jobs):
    fname = datetime.now().strftime(OUTPUT_FILENAME_FMT)
    path = OUTPUT_DIR / fname
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for j in jobs:
            dp = j["date_posted_parsed"]
            dp_str = dp.strftime("%d/%m/%Y") if dp else "Unknown"
            if j.get("salary_min"):
                salary = f"£{j['salary_min']:,} - £{j['salary_max']:,}"
            elif j.get("salary"):
                salary = j["salary"]
            else:
                salary = "Not specified"
            emp = j.get("employment_type") or "Permanent"
            block = (
                f" * Company: {j.get('company') or 'Unknown'}\n"
                f" * Job Title: {j.get('title') or ''}\n"
                f" * Date Posted: {dp_str}\n"
                f" * Shift Type: Night\n"
                f" * Rota: {j.get('rota', 'Unknown')}\n"
                f" * Employment Type: {emp}\n"
                f" * Salary: {salary}\n"
                f" * Location: {j.get('location') or ''}\n"
                f" * Commute Estimate: {j.get('commute', 'Unknown')}\n"
                f" * Source Website: {j.get('source') or 'Unknown'}\n"
                f" * Application URL: {j.get('url') or ''}\n\n"
            )
            f.write(block)
    return path


def run(roles, scrapers, headless=True, per_site_cap=PER_SITE_CAP):
    started = time.time()
    raw_by_source = {}  # source name -> list of (job, scraper_instance)
    counters = {"title": 0, "recency": 0, "location": 0, "shift": 0, "sia": 0, "exclusion": 0}

    with BrowserSession(headless=headless) as bs:
        # Pass 1: search results → cheap fields only
        for role in roles:
            log.info(f"=== ROLE: {role} ===")
            for ScraperCls in scrapers:
                s = ScraperCls(bs)
                try:
                    listings = s.run(role, max_results=per_site_cap)
                    raw_by_source.setdefault(s.name, []).extend([(j, s) for j in listings])
                except Exception as e:
                    log.error(f"{s.name} failed for {role}: {e}")
                    s.errlog.error(traceback.format_exc())

        # Flatten for filtering, keeping the originating scraper for Pass 2
        flat = [(j, s) for items in raw_by_source.values() for (j, s) in items]
        raw_count = len(flat)
        log.info(f"Raw collected: {raw_count}")

        cheap_survivors = []
        for j, s in flat:
            enrich(j)  # mutates in place
            if apply_cheap_filters([j], counters):
                cheap_survivors.append((j, s))
        log.info(f"After cheap filter (recency+location): {len(cheap_survivors)}")

        # Pass 2: fetch description for each survivor
        for j, s in cheap_survivors:
            if not j.get("description"):
                log.info(f"[Pass 2] fetching {s.name}: {j.get('title')!r}")
                j["description"] = s.fetch_description(j.get("url"))

        # Now apply expensive filters
        expensive_input = [j for (j, _s) in cheap_survivors]
        filtered = apply_expensive_filters(expensive_input, counters)
        log.info(f"After expensive filter (shift+SIA+exclusion): {len(filtered)}")

        failed_navs = bs.failed_navigations

    pre_dedupe = len(filtered)
    deduped = dedupe(filtered)
    dups_removed = pre_dedupe - len(deduped)
    log.info(f"After dedupe: {len(deduped)} (removed {dups_removed})")
    ranked = rank(deduped)

    out_path = write_output(ranked)
    elapsed = time.time() - started

    print()
    print(f"Total jobs found: {raw_count}")
    print(f"Accepted: {len(ranked)}")
    print(f"Rejected by filter: {sum(counters.values())} "
          f"(title={counters['title']}, recency={counters['recency']}, "
          f"location={counters['location']}, shift={counters['shift']}, "
          f"SIA={counters['sia']}, exclusion={counters['exclusion']})")
    print(f"Duplicates removed: {dups_removed}")
    print(f"Failed page loads: {failed_navs}")
    print(f"Execution time: {time.strftime('%H:%M:%S', time.gmtime(elapsed))}")
    print(f"Output: {out_path}")


def _filter_scrapers(names_csv):
    if not names_csv:
        return ALL_SCRAPERS
    wanted = {n.strip().lower() for n in names_csv.split(",")}
    return [s for s in ALL_SCRAPERS if s.name.lower() in wanted]


def _filter_roles(roles_csv):
    if not roles_csv:
        return TARGET_ROLES
    return [r.strip() for r in roles_csv.split(",")]


def _dry_run():
    import json
    from pathlib import Path
    fixture = Path(__file__).parent / "tests" / "fixture.json"
    if not fixture.exists():
        print(f"No fixture at {fixture}. Create one with sample raw jobs.")
        sys.exit(1)
    raw = json.loads(fixture.read_text(encoding="utf-8"))
    counters = {"title": 0, "recency": 0, "location": 0, "shift": 0, "sia": 0, "exclusion": 0}
    enriched = [enrich(j) for j in raw]
    # Fixture data has descriptions pre-filled, so we can run both passes back-to-back.
    cheap = apply_cheap_filters(enriched, counters)
    filtered = apply_expensive_filters(cheap, counters)
    deduped = dedupe(filtered)
    ranked = rank(deduped)
    out_path = write_output(ranked)
    print(f"Dry-run: {len(raw)} raw -> {len(ranked)} accepted -> {out_path}")


def main():
    ap = argparse.ArgumentParser(description="Night security job aggregator.")
    ap.add_argument("--visible", action="store_true",
                    help="Show browser window (enables manual CAPTCHA solve).")
    ap.add_argument("--dry-run", action="store_true",
                    help="Run filter/dedupe/rank against tests/fixture.json, no network.")
    ap.add_argument("--sites", default="",
                    help="Comma-separated scraper names (e.g. reed,indeed). Default: all.")
    ap.add_argument("--roles", default="",
                    help="Comma-separated role keywords. Default: all 8 target roles.")
    args = ap.parse_args()

    if args.dry_run:
        _dry_run()
        return

    run(
        roles=_filter_roles(args.roles),
        scrapers=_filter_scrapers(args.sites),
        headless=not args.visible,
    )


if __name__ == "__main__":
    main()
