import datetime
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
import os
import glob
from typing import Any

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

# When the task is to fetch all the products, you're gonna have to navigate a bit with Webdriver and then save the results somehow
def store_page_html(page_html: str, folder: str = 'scraped_pages') -> str:
    os.makedirs(folder, exist_ok=True)
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')
    filepath = f'{folder}/snapshot_{timestamp}.html'
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(page_html)

def get_latest_snapshot(folder: str = 'scraped_pages') -> str:
    files = glob.glob(os.path.join(folder, '*.html'))
    if not files:
        raise FileNotFoundError(f'No HTML files found in {folder}')

    latest_file = max(files, key=os.path.getmtime)
    return latest_file

def parse_html_file(path: str) -> BeautifulSoup:
    with open(path, encoding='utf-8') as f:
        return BeautifulSoup(f.read(), 'html.parser')

# Very hacky and non-maintainable solution
# Performance: probably bad; you have to search for "Produkte gefunden" every time
# Maintainability: This string is unlikely to be anywhere else on the site. The site's template is unlikely to change
def scrape_num_products(soup: BeautifulSoup) -> str:
    produkte_gefunden_string = soup.find(string='Produkte gefunden')
    num_products_parent = produkte_gefunden_string.parent
    num_products_parent_content = num_products_parent.get_text()
    extracted_integer = num_products_parent_content[0:2]

    # This needs to be stored somewhere in GitHub Actions cron
    return extracted_integer

if __name__ == '__main__':
    fetch_new_page = False

    if fetch_new_page:
        driver = create_driver()
        try:
            html = fetch_page_html(driver, url)
            filepath = store_page_html(html)
            print(f'Saved HTML to {filepath}')

            # Use By.XPATH
            # When scraping products: use webdriver to load in next page
        finally:
            driver.quit()
    else:
        filepath = get_latest_snapshot()
        print(f'Reading latest saved HTML: {filepath}')

        soup = parse_html_file(filepath)

        # test = soup.find_all('p')
        # for tag in test[8]:
        #     print(f'Name: {tag.name}, Content: {tag.get_text()}')

        num_products = scrape_num_products(soup)
        print(f'Number of products: {num_products}')

        # driver.get('file://C:/Users/abdul/PycharmProjects/CannabisWebScraper/scraped_pages/snapshot_2025-12-01_21-22.html')
        # print(driver.find_elements(By.CLASS_NAME, 'MuiTypography-root.MuiTypography-body1.mui-9mqwrs'))


    # soup = parse_html_file('filepath')
    # print(soup.title)