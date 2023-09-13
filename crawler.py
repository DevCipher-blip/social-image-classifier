"""Collect media image links from a public Twitter profile page.

Profile pages are rendered by JavaScript, so the page source comes from a headless
Chrome driven by Selenium. Selenium is an optional dependency (requirements-crawler.txt);
without it /keyword answers 503 and /file keeps working.
"""

import re
from contextlib import suppress

from bs4 import BeautifulSoup

from constants import TWITTER_BASE_URL

MEDIA_PREFIX = "https://pbs.twimg.com/media/"
HANDLE = re.compile(r"[A-Za-z0-9_]{1,15}")


class InvalidHandle(ValueError):
    pass


class CrawlerUnavailable(RuntimeError):
    pass


def profile_url(keyword: str) -> str:
    # The keyword becomes a URL path, so only Twitter's handle alphabet is allowed.
    if not HANDLE.fullmatch(keyword):
        raise InvalidHandle("keyword must be 1-15 letters, digits or underscores")
    return f"{TWITTER_BASE_URL}{keyword}"


def extract_media_links(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = (img.get("src") or "" for img in soup.find_all("img"))
    return list(dict.fromkeys(link for link in links if link.startswith(MEDIA_PREFIX)))


class SeleniumPageSource:
    def __init__(self, page_load_timeout: float = 20, render_wait: float = 10):
        self.page_load_timeout = page_load_timeout
        self.render_wait = render_wait

    def __call__(self, url: str) -> str:
        try:
            from selenium import webdriver
            from selenium.common.exceptions import TimeoutException
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support import expected_conditions
            from selenium.webdriver.support.ui import WebDriverWait
        except ImportError as error:
            raise CrawlerUnavailable(
                "The crawler needs Selenium: pip install -r requirements-crawler.txt"
            ) from error

        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1200,1100")
        driver = webdriver.Chrome(options=options)
        try:
            driver.set_page_load_timeout(self.page_load_timeout)
            driver.get(url)
            media = (By.CSS_SELECTOR, f'img[src^="{MEDIA_PREFIX}"]')
            # No media rendered in time: return whatever the page has.
            with suppress(TimeoutException):
                WebDriverWait(driver, self.render_wait).until(
                    expected_conditions.presence_of_element_located(media)
                )
            return driver.page_source
        finally:
            driver.quit()


class Crawler:
    def __init__(self, page_source=None):
        self.page_source = page_source or SeleniumPageSource()

    def get_image_links(self, keyword: str) -> list[str]:
        return extract_media_links(self.page_source(profile_url(keyword)))
