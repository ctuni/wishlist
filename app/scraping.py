import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


class ScrapedProduct:
    def __init__(self, title=None, image_url=None, price=None, currency=None, source=None):
        self.title = title
        self.image_url = image_url
        self.price = price
        self.currency = currency
        self.source = source


PRICE_REGEX = re.compile(r"(\d+[.,]\d{2})")


def _guess_price(text: str):
    if not text:
        return None, None
    match = PRICE_REGEX.search(text)
    if not match:
        return None, None
    val = match.group(1).replace(",", ".")
    try:
        value = float(val)
    except ValueError:
        return None, None

    currency = None
    if "€" in text:
        currency = "EUR"
    elif "$" in text:
        currency = "USD"

    return value, currency


def scrape_generic(url: str) -> ScrapedProduct:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/123.0 Safari/537.36"
        )
    }

    domain = urlparse(url).netloc

    try:
        resp = httpx.get(url, headers=headers, timeout=20, follow_redirects=True)
    except httpx.RequestError as e:
        # No s'ha pogut connectar (time out, DNS, etc.) → entrada mínima
        print(f"[scraper] Error de connexió amb {url}: {e}")
        return ScrapedProduct(title=url, image_url=None, price=None, currency=None, source=domain)

    # Si la web ens retorna 4xx/5xx, no petem: fem servir fallback
    if resp.status_code >= 400:
        print(f"[scraper] HTTP {resp.status_code} per {url}, creant entrada mínima sense scraping.")
        return ScrapedProduct(title=url, image_url=None, price=None, currency=None, source=domain)

    soup = BeautifulSoup(resp.text, "html.parser")

    # TITLE
    title = None
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()

    # IMAGE
    image_url = None
    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        image_url = og_image["content"]
    if not image_url:
        first_img = soup.find("img")
        if first_img and first_img.get("src"):
            image_url = first_img["src"]

    # PRICE
    price = None
    currency = None

    candidates = []
    for selector in [
        "[class*=price]",
        "[id*=price]",
        "[class*=Price]",
        "[id*=Price]",
    ]:
        candidates.extend(soup.select(selector))

    text_joined = " ".join(c.get_text(" ", strip=True) for c in candidates)
    price, currency = _guess_price(text_joined)

    if price is None:
        price, currency = _guess_price(soup.get_text(" ", strip=True))

    return ScrapedProduct(
        title=title or url,
        image_url=image_url,
        price=price,
        currency=currency,
        source=domain,
    )


def scrape_product(url: str) -> ScrapedProduct:
    # Punt d’entrada únic per si més endavant afegim scrapers específics
    return scrape_generic(url)
