"""Central configuration. All tunables live here."""

from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / "output"
LOG_DIR = PROJECT_ROOT / "logs"
BROWSER_PROFILE_DIR = PROJECT_ROOT / "browser_profile"

for d in (OUTPUT_DIR, LOG_DIR, BROWSER_PROFILE_DIR):
    d.mkdir(parents=True, exist_ok=True)

# Target roles (search keywords)
TARGET_ROLES = [
    "Door Supervisor",
    "Security Officer Night Shift",
    "Static Security Guard",
    "Night Concierge",
    "Corporate Security Officer",
    "Gatehouse Security",
    "Front Desk Security",
    "Concierge Security",
]

# Postcode priority — lower index = higher priority
POSTCODE_PRIORITY = ["SE", "SW", "SM", "CR", "BR"]

# Static commute estimate by postcode prefix (rough London inner→outer)
COMMUTE_ESTIMATES = {
    "SE": "20-40 min",
    "SW": "25-45 min",
    "SM": "35-55 min",
    "CR": "30-50 min",
    "BR": "35-55 min",
    "E":  "40-60 min",
    "EC": "30-50 min",
    "N":  "45-60 min",
    "NW": "40-60 min",
    "W":  "35-55 min",
    "WC": "30-50 min",
    "DA": "40-60 min",
    "KT": "45-60 min",
    "TW": "45-60 min",
}

# Filter thresholds
RECENCY_DAYS = 7
PER_SITE_CAP = 50
MAX_COMMUTE_MIN = 60

# London-area place names that map to acceptable postcodes (lowercase, substring match).
# Used as a fallback in passes_location when a job listing has no postcode in its
# location string (common with Reed, Indeed, etc. — they show "Sidcup, Kent" not "DA14").
LONDON_AREA_KEYWORDS = {
    # Generic
    "london",
    # SE (south-east London)
    "bermondsey", "camberwell", "catford", "charlton", "crystal palace",
    "deptford", "dulwich", "eltham", "greenwich", "lewisham", "new cross",
    "peckham", "rotherhithe", "sydenham", "walworth", "woolwich",
    "blackheath", "kennington", "elephant and castle",
    # SW (south-west London)
    "balham", "battersea", "brixton", "chelsea", "clapham", "fulham",
    "lambeth", "putney", "streatham", "tooting", "vauxhall", "wandsworth",
    "wimbledon", "earlsfield", "stockwell",
    # SM (Sutton)
    "sutton", "carshalton", "cheam", "hackbridge", "wallington",
    # CR (Croydon)
    "croydon", "addington", "coulsdon", "norbury", "purley",
    "south norwood", "thornton heath", "selsdon", "kenley",
    # BR (Bromley)
    "bromley", "beckenham", "biggin hill", "chislehurst", "hayes",
    "keston", "orpington", "petts wood", "west wickham",
    # DA (Dartford / Bexley — commute range)
    "sidcup", "bexley", "bexleyheath", "dartford", "welling", "crayford",
    "erith", "belvedere",
    # KT (Kingston — commute range)
    "kingston upon thames", "kingston", "surbiton", "new malden",
    "tolworth", "chessington",
    # TW (Twickenham — commute range)
    "twickenham", "richmond", "teddington", "hampton",
}

# Boost keywords for ranking (case-insensitive substring match)
ROLE_BOOST_KEYWORDS = [
    "static", "corporate", "concierge", "gatehouse",
    "reception", "front desk",
]

# Exclusion keywords (case-insensitive substring match in description)
EXCLUSION_KEYWORDS = [
    "rotating day/night", "rotating days/nights", "rotating shifts",
    "flexible shifts", "event security", "festival security",
    "temporary seasonal", "seasonal work", "zero hours", "zero-hours",
    "self-employed", "self employed", "cash in hand", "cash-in-hand",
    "no longer accepting applications", "this job has expired",
]

# Night shift positive markers
NIGHT_KEYWORDS = [
    "night shift", "nights only", "night-only", "overnight",
    "permanent nights", "night work", "10pm", "11pm", "12am",
    "22:00", "23:00", "00:00",
]

# Day/rotating markers that DISQUALIFY (must absence of these implied night)
DAY_KEYWORDS = [
    "day shift", "days only", "9am-5pm", "9-5", "monday to friday",
    "mon-fri", "office hours",
]

# SIA explicit markers (at least one required)
SIA_KEYWORDS = [
    "sia licence", "sia license", "sia door supervisor",
    "door supervisor licence", "door supervisor license",
    "highfield level 2 door supervisor", "level 2 door supervisor",
    "sia ds", "ds licence", "ds license",
]

# Rota classification patterns (regex-style raw, case-insensitive)
ROTA_4_ON_4_OFF_PATTERNS = [
    r"4\s*on\s*4\s*off", r"4-on-4-off", r"four\s+on\s+four\s+off",
]

# User agent for Playwright
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Delays (milliseconds)
ACTION_DELAY_MIN_MS = 800
ACTION_DELAY_MAX_MS = 2400
NAV_DELAY_MIN_MS = 1500
NAV_DELAY_MAX_MS = 4000

# Output filename pattern
OUTPUT_FILENAME_FMT = "%Y%m%d %H%M%S - Door Supervisor Job Search.txt"
