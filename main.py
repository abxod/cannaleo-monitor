import datetime
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
import os
# import requests (requests might still be needed for API calls to download images/files/json)

url = 'https://www.cannabisdarmstadt.de'

def create_driver() -> webdriver.Edge:
    options = Options()
    options.add_argument('--headless') # runs the browser in the background
    driver = webdriver.Edge(options=options)
    return driver

def fetch_page_html(driver: webdriver.Edge, url: str) -> str:
    driver.get(url)
    time.sleep(3) # wait for dynamic content to load
    return driver.page_source

def store_page_html(page_html: str, folder: str = 'stored_html') -> str:
    os.makedirs(folder, exist_ok=True)
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')
    filepath = f'{folder}/snapshot_{timestamp}.html'
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(page_html)

def parse_html_file(path: str) -> BeautifulSoup:
    with open(path, encoding='utf-8') as f:
        return BeautifulSoup(f.read(), 'html.parser')

if __name__ == '__main__':
    fetch_new_page = False

    if fetch_new_page:
        driver = create_driver()
        try:
            html = fetch_page_html(driver, url)
            filepath = store_page_html(html)
            print(f"Saved HTML to {filepath}")
        finally:
            try:
                driver.quit()
            except NameError:
                pass

    soup = parse_html_file('stored_html/snapshot_2025-12-01_21-22.html')