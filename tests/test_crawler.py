import builtins

import pytest

from crawler import (
    Crawler,
    CrawlerUnavailable,
    InvalidHandle,
    SeleniumPageSource,
    extract_media_links,
    profile_url,
)

PAGE = """
<html><body>
  <img src="https://pbs.twimg.com/profile_images/1/avatar.jpg">
  <img src="https://pbs.twimg.com/media/AAA?format=jpg&name=small">
  <img alt="no src">
  <img src="https://evil.example/?u=https://pbs.twimg.com/media/BBB">
  <img src="https://pbs.twimg.com/media/CCC.png">
  <img src="https://pbs.twimg.com/media/AAA?format=jpg&name=small">
</body></html>
"""


def test_only_media_images_are_extracted_once_in_page_order():
    assert extract_media_links(PAGE) == [
        "https://pbs.twimg.com/media/AAA?format=jpg&name=small",
        "https://pbs.twimg.com/media/CCC.png",
    ]


def test_profile_url_uses_the_handle():
    assert profile_url("NASA_jpl") == "https://twitter.com/NASA_jpl"


@pytest.mark.parametrize(
    "keyword", ["", "a" * 16, "../i/flow", "nasa?x=1", "@evil.example", "nasa/status/1", "日本"]
)
def test_keywords_outside_the_handle_alphabet_are_refused(keyword):
    with pytest.raises(InvalidHandle):
        profile_url(keyword)


def test_crawler_reads_the_rendered_profile_page():
    requested = []

    def page_source(url):
        requested.append(url)
        return PAGE

    links = Crawler(page_source=page_source).get_image_links("nasa")
    assert requested == ["https://twitter.com/nasa"]
    assert len(links) == 2


def test_missing_selenium_is_reported(monkeypatch):
    real_import = builtins.__import__

    def without_selenium(name, *args, **kwargs):
        if name.startswith("selenium"):
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_selenium)
    with pytest.raises(CrawlerUnavailable, match="requirements-crawler"):
        SeleniumPageSource()("https://twitter.com/nasa")
