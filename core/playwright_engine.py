"""Playwright wrapper: stealth, persistent profile, retries, CAPTCHA detection."""

import os
import random
import sys

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from config import (
    ACTION_DELAY_MAX_MS, ACTION_DELAY_MIN_MS, BROWSER_PROFILE_DIR,
    NAV_DELAY_MAX_MS, NAV_DELAY_MIN_MS, USER_AGENT,
)
from utils.helpers import random_delay
from utils.logger import get_logger

log = get_logger("engine")

CAPTCHA_SELECTORS = [
    'iframe[src*="recaptcha"]',
    'iframe[title*="cloudflare" i]',
    '#challenge-form',
    '[id^="datadome"]',
    'iframe[src*="hcaptcha"]',
    'div.cf-browser-verification',
]

COOKIE_BUTTON_SELECTORS = [
    'button:has-text("Accept all")',
    'button:has-text("Accept All")',
    'button:has-text("I accept")',
    'button:has-text("Agree")',
    'button#onetrust-accept-btn-handler',
    'button[aria-label*="accept" i]',
    'button[data-testid*="accept" i]',
]


class NavigationError(Exception):
    pass


class CaptchaBlocked(Exception):
    pass


class BrowserSession:
    def __init__(self, headless=True, proxy=None):
        self.headless = headless
        self.proxy = proxy or os.environ.get("JOB_SEARCH_PROXY")
        self._pw = None
        self._context = None
        self.page = None
        self.failed_navigations = 0

    def __enter__(self):
        self._pw = sync_playwright().start()
        viewport_w = 1366 + random.randint(-30, 30)
        viewport_h = 768 + random.randint(-20, 20)
        launch_kwargs = {
            "headless": self.headless,
            "user_agent": USER_AGENT,
            "viewport": {"width": viewport_w, "height": viewport_h},
            "locale": "en-GB",
            "timezone_id": "Europe/London",
            "extra_http_headers": {"Accept-Language": "en-GB,en;q=0.9"},
        }
        if self.proxy:
            launch_kwargs["proxy"] = {"server": self.proxy}
        self._context = self._pw.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_PROFILE_DIR),
            **launch_kwargs,
        )
        self.page = self._context.new_page()
        try:
            from playwright_stealth import Stealth
            Stealth().apply_stealth_sync(self.page)
        except Exception as e:
            log.warning(f"playwright-stealth not applied: {e}")
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if self._context:
                self._context.close()
        finally:
            if self._pw:
                self._pw.stop()

    def goto(self, url, retries=3, wait_until="domcontentloaded"):
        last_err = None
        for attempt in range(1, retries + 1):
            try:
                self.page.goto(url, wait_until=wait_until, timeout=30000)
                random_delay(NAV_DELAY_MIN_MS, NAV_DELAY_MAX_MS)
                return
            except PWTimeout as e:
                last_err = e
                log.warning(f"goto attempt {attempt}/{retries} timed out: {url}")
                random_delay(2000 * attempt, 4000 * attempt)
            except Exception as e:
                last_err = e
                log.warning(f"goto attempt {attempt}/{retries} error: {e}")
                random_delay(2000 * attempt, 4000 * attempt)
        self.failed_navigations += 1
        raise NavigationError(f"Could not load {url}: {last_err}")

    def dismiss_cookies(self):
        for sel in COOKIE_BUTTON_SELECTORS:
            try:
                btn = self.page.locator(sel).first
                if btn.count() and btn.is_visible(timeout=1000):
                    btn.click(timeout=2000)
                    random_delay(ACTION_DELAY_MIN_MS, ACTION_DELAY_MAX_MS)
                    return True
            except Exception:
                continue
        return False

    def lazy_scroll(self, passes=3):
        for _ in range(passes):
            self.page.mouse.wheel(0, 1500)
            random_delay(ACTION_DELAY_MIN_MS, ACTION_DELAY_MAX_MS)

    def detect_captcha(self):
        for sel in CAPTCHA_SELECTORS:
            try:
                if self.page.locator(sel).count():
                    return True
            except Exception:
                continue
        return False

    def wait_for_human(self, site_name):
        if self.headless:
            raise CaptchaBlocked(f"CAPTCHA on {site_name} in headless mode")
        print(f"\n[CAPTCHA] Detected on {site_name}. Solve in browser then press Enter…", file=sys.stderr)
        input()
