import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from time import sleep
from constants import TWITTER_BASE_URL

class Crawler:

    def __init__(self):
        options = Options()
        options.add_argument("window-size=1200,1100")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36")
        self.driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)

    def get_image_links(self, keyword):
        scraping_url = f"{TWITTER_BASE_URL}{keyword}"

        sleep(3)
        self.driver.get(scraping_url)
        sleep(10)

        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        image_links = []

        for images in soup.findAll("img"):
            if (link := images.get("src")) is not  None and "https://pbs.twimg.com/media" in link:
                image_links.append(link)

        return image_links
