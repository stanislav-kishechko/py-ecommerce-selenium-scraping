import csv
from dataclasses import dataclass, fields
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions


BASE_URL = "https://webscraper.io/"
HOME_URL = urljoin(BASE_URL, "test-sites/e-commerce/more/")


@dataclass
class Product:
    title: str
    description: str
    price: float
    rating: int
    num_of_reviews: int


class Scraper:
    """Manages the WebDriver lifecycle and shared browser utilities."""

    def __init__(self) -> None:
        self._driver = self._create_driver()

    def _create_driver(self) -> webdriver.Chrome:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
        return webdriver.Chrome(options=options)

    def get(self, url: str) -> None:
        self._driver.get(url)

    def accept_cookies(self) -> None:
        """Click the accept cookies button if it appears."""
        try:
            wait = WebDriverWait(self._driver, 3)
            accept_button = wait.until(
                expected_conditions.element_to_be_clickable(
                    (By.ID, "cookieBannerBtn")
                )
            )
            accept_button.click()
        except Exception:
            pass

    def quit(self) -> None:
        self._driver.quit()

    def __enter__(self) -> "Scraper":
        return self

    def __exit__(self, *args) -> None:
        self.quit()

    @property
    def driver(self) -> webdriver.Chrome:
        return self._driver


class PageScraper:
    """Handles loading all products from a single page and parsing them."""

    def __init__(self, driver: webdriver.Chrome) -> None:
        self._driver = driver

    def load_all_products(self) -> list[Product]:
        """Click 'more' until exhausted, then parse the full product list."""
        self._click_until_all_loaded()
        return self._parse_products()

    def _click_until_all_loaded(self) -> None:
        wait = WebDriverWait(self._driver, 5)
        while True:
            try:
                more_button = wait.until(
                    expected_conditions.element_to_be_clickable(
                        (By.CLASS_NAME, "btn-primary")
                    )
                )
                self._driver.execute_script(
                    "arguments[0].click();", more_button
                )
            except Exception:
                break

    def _parse_products(self) -> list[Product]:
        products = []
        for card in self._driver.find_elements(By.CLASS_NAME, "thumbnail"):
            products.append(self._parse_card(card))

        return products

    def _parse_card(self, card: webdriver) -> Product:
        title = card.find_element(
            By.CLASS_NAME, "title"
        ).get_attribute("title").strip()

        description = card.find_element(
            By.CLASS_NAME, "description"
        ).text.strip()

        price_text = card.find_element(By.CLASS_NAME, "price").text.strip()
        price = float(price_text.replace("$", ""))

        rating = len(card.find_elements(By.CLASS_NAME, "ws-icon-star"))

        num_of_reviews = int(
            card.find_element(
                By.CSS_SELECTOR, "span[itemprop='reviewCount']"
            ).text.strip()
        )

        return Product(
            title=title,
            description=description,
            price=price,
            rating=rating,
            num_of_reviews=num_of_reviews,
        )


class ProductRepository:
    """Persists products to CSV files."""

    def save(self, file_name: str, products: list[Product]) -> None:
        with open(file_name, "w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow([f.name for f in fields(Product)])
            for product in products:
                writer.writerow(
                    [
                        product.title,
                        product.description,
                        product.price,
                        product.rating,
                        product.num_of_reviews,
                    ]
                )


class EcommerceCrawler:
    """Orchestrates scraping across all e-commerce pages."""

    PAGES: dict[str, str] = {
        "home.csv": HOME_URL,
        "computers.csv": urljoin(HOME_URL, "computers"),
        "laptops.csv": urljoin(HOME_URL, "computers/laptops"),
        "tablets.csv": urljoin(HOME_URL, "computers/tablets"),
        "phones.csv": urljoin(HOME_URL, "phones"),
        "touch.csv": urljoin(HOME_URL, "phones/touch"),
    }

    def __init__(self) -> None:
        self._repository = ProductRepository()

    def run(self) -> None:
        with Scraper() as scraper:
            for file_name, page_url in self.PAGES.items():
                self._scrape_page(scraper, page_url, file_name)

    def _scrape_page(
        self, scraper: Scraper, page_url: str, file_name: str
    ) -> None:
        scraper.get(page_url)
        scraper.accept_cookies()

        page_scraper = PageScraper(scraper.driver)
        products = page_scraper.load_all_products()
        self._repository.save(file_name, products)


def get_all_products() -> None:
    EcommerceCrawler().run()


if __name__ == "__main__":
    get_all_products()
