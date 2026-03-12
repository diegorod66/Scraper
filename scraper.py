# =============================================================================
# scraper.py — Navegación, paginación y orquestación del scraping
# =============================================================================
# Contiene la lógica de alto nivel:
#   - get_product_links(): recorre el listado paginado y recopila URLs
#   - scrape_product():    descarga y extrae datos de un producto individual
#   - run():               punto de entrada que conecta todos los módulos
#
# Soporta dos modos de operación controlados por config.USE_SELENIUM:
#   False → requests + BeautifulSoup  (sitios con HTML estático)
#   True  → Selenium Chrome headless  (sitios que requieren JavaScript)
# =============================================================================

import logging
import time
from urllib.parse import urljoin

from bs4 import BeautifulSoup

import config
import downloader
import parser
import storage

logger = logging.getLogger(__name__)


# =============================================================================
# Helpers compartidos
# =============================================================================

def _make_absolute(url: str, base: str) -> str:
    """Convierte una URL relativa en absoluta usando la URL base."""
    if not url:
        return ""
    return urljoin(base, url)


# =============================================================================
# Modo requests (HTML estático)
# =============================================================================

def _get_html_requests(session, url: str) -> str:
    """
    Descarga el HTML de una URL usando requests con reintentos.
    Devuelve el texto HTML o cadena vacía en caso de error.
    """
    import requests as req

    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            response = session.get(url, timeout=config.REQUEST_TIMEOUT)
            response.raise_for_status()
            # Usar apparent_encoding solo si está disponible; de lo contrario utf-8
            response.encoding = response.apparent_encoding or "utf-8"
            return response.text
        except req.exceptions.Timeout:
            logger.warning("Timeout en '%s' (intento %d/%d)", url, attempt, config.MAX_RETRIES)
        except req.exceptions.HTTPError as e:
            logger.warning("HTTP error en '%s': %s", url, e)
            break  # No reintentar errores HTTP (4xx/5xx)
        except req.exceptions.RequestException as e:
            logger.warning("Error de red en '%s' (intento %d/%d): %s", url, attempt, config.MAX_RETRIES, e)

        if attempt < config.MAX_RETRIES:
            time.sleep(config.REQUEST_DELAY * attempt)  # Back-off progresivo

    return ""


def get_product_links_requests(session, listing_url: str) -> list:
    """
    Recorre todas las páginas del listado y recopila las URLs de cada producto.

    - Sigue el enlace de "página siguiente" hasta que no haya más páginas.
    - Deduplica las URLs para evitar procesar el mismo producto dos veces.

    Retorna lista de URLs absolutas.
    """
    import requests as req

    product_urls = []
    visited_pages = set()
    current_url = listing_url

    pagination_selector = config.SELECTORS.get("pagination")
    product_link_selector = config.SELECTORS.get("product_links")

    if not product_link_selector:
        logger.error("El selector 'product_links' no está configurado en config.SELECTORS.")
        return []

    while current_url and current_url not in visited_pages:
        logger.info("Procesando página de listado: %s", current_url)
        visited_pages.add(current_url)

        # Respetar límite de páginas si está configurado
        max_pages = getattr(config, "MAX_PAGES", 0)
        if max_pages and len(visited_pages) > max_pages:
            logger.info("Límite de páginas alcanzado (%d). Deteniendo paginación.", max_pages)
            break

        html = _get_html_requests(session, current_url)
        if not html:
            logger.warning("No se pudo obtener el listado de: %s", current_url)
            break

        soup = BeautifulSoup(html, "lxml")

        # Extraer todos los enlaces a productos de esta página
        links = soup.select(product_link_selector)
        if not links:
            logger.warning(
                "No se encontraron productos con selector '%s' en: %s",
                product_link_selector,
                current_url,
            )

        for link in links:
            href = link.get("href", "").strip()
            if href:
                # Usar current_url como base para resolver paths relativos correctamente
                absolute_url = _make_absolute(href, current_url)
                if absolute_url not in product_urls:
                    product_urls.append(absolute_url)

        logger.debug("Links acumulados hasta ahora: %d", len(product_urls))

        # Encontrar el enlace a la siguiente página
        next_url = ""
        if pagination_selector:
            next_link = soup.select_one(pagination_selector)
            if next_link:
                next_href = next_link.get("href", "").strip()
                next_url = _make_absolute(next_href, current_url) if next_href else ""

        current_url = next_url if next_url != current_url else ""
        time.sleep(config.REQUEST_DELAY)

    logger.info("Total de productos encontrados en el listado: %d", len(product_urls))
    return product_urls


def scrape_product_requests(session, url: str) -> dict:
    """
    Descarga, parsea y enriquece los datos de un producto individual.

    Parámetros:
        session : Sesión requests con headers configurados.
        url     : URL absoluta de la página del producto.

    Retorna dict con todos los campos + 'imagen_local' + 'url_producto'.
    En caso de error devuelve un dict parcial con la URL para trazabilidad.
    """
    logger.info("Scrapeando producto: %s", url)

    html = _get_html_requests(session, url)
    if not html:
        logger.error("No se pudo obtener el HTML del producto: %s", url)
        return {"url_producto": url, "nombre": "", "codigo": "", "precio": "",
                "cantidad": "", "descripcion": "", "imagen_url": "", "imagen_local": ""}

    # Extraer campos del HTML
    # Pasar la URL del producto para resolver correctamente rutas de imagen relativas
    data = parser.parse_product(html, product_url=url)

    # Descargar imagen y obtener ruta local
    imagen_local = downloader.download_image(
        session=session,
        image_url=data.get("imagen_url", ""),
        product_code=data.get("codigo", ""),
        product_name=data.get("nombre", ""),
    )
    data["imagen_local"] = imagen_local
    data["url_producto"] = url

    return data


# =============================================================================
# Modo Selenium (sitios con JavaScript)
# =============================================================================

def _init_selenium_driver():
    """
    Inicializa Chrome headless con webdriver-manager.
    Requiere: pip install selenium webdriver-manager
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
    except ImportError:
        logger.error(
            "Selenium no está instalado. Ejecuta: pip install selenium webdriver-manager"
        )
        raise

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument(f"user-agent={config.HEADERS['User-Agent']}")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )
    driver.set_page_load_timeout(config.REQUEST_TIMEOUT)
    return driver


def get_product_links_selenium(driver, listing_url: str) -> list:
    """
    Versión Selenium de get_product_links.
    Navega el listado con JavaScript activado y extrae los links de productos.
    """
    from selenium.common.exceptions import TimeoutException, WebDriverException

    product_urls = []
    visited_pages = set()
    current_url = listing_url

    pagination_selector = config.SELECTORS.get("pagination")
    product_link_selector = config.SELECTORS.get("product_links")

    while current_url and current_url not in visited_pages:
        logger.info("Selenium — Página de listado: %s", current_url)
        visited_pages.add(current_url)

        try:
            driver.get(current_url)
            time.sleep(config.REQUEST_DELAY)  # Esperar renderizado JS
        except (TimeoutException, WebDriverException) as e:
            logger.warning("Selenium error al cargar listado '%s': %s", current_url, e)
            break

        soup = BeautifulSoup(driver.page_source, "lxml")
        links = soup.select(product_link_selector) if product_link_selector else []

        for link in links:
            href = link.get("href", "").strip()
            if href:
                absolute_url = _make_absolute(href, config.BASE_URL)
                if absolute_url not in product_urls:
                    product_urls.append(absolute_url)

        next_url = ""
        if pagination_selector:
            next_link = soup.select_one(pagination_selector)
            if next_link:
                next_href = next_link.get("href", "").strip()
                next_url = _make_absolute(next_href, config.BASE_URL) if next_href else ""

        current_url = next_url if next_url != current_url else ""

    logger.info("Selenium — Total productos encontrados: %d", len(product_urls))
    return product_urls


def scrape_product_selenium(driver, session, url: str) -> dict:
    """
    Versión Selenium de scrape_product.
    Renderiza la página del producto con JS y extrae los datos.
    La descarga de imagen sigue usando requests para eficiencia.
    """
    from selenium.common.exceptions import TimeoutException, WebDriverException

    logger.info("Selenium — Scrapeando producto: %s", url)

    try:
        driver.get(url)
        time.sleep(config.REQUEST_DELAY)
        html = driver.page_source
    except (TimeoutException, WebDriverException) as e:
        logger.error("Selenium error al cargar producto '%s': %s", url, e)
        return {"url_producto": url, "nombre": "", "codigo": "", "precio": "",
                "cantidad": "", "descripcion": "", "imagen_url": "", "imagen_local": ""}

    data = parser.parse_product(html, product_url=url)

    imagen_local = downloader.download_image(
        session=session,
        image_url=data.get("imagen_url", ""),
        product_code=data.get("codigo", ""),
        product_name=data.get("nombre", ""),
    )
    data["imagen_local"] = imagen_local
    data["url_producto"] = url

    return data


# =============================================================================
# Función principal de ejecución
# =============================================================================

def run(base_url: str = None) -> tuple:
    """
    Orquesta el proceso completo de scraping.

    1. Construye la URL del listado de productos.
    2. Recopila todas las URLs de productos (con paginación).
    3. Itera sobre cada URL, extrae datos y descarga imágenes.
    4. Guarda los resultados en productos.csv.

    Parámetros:
        base_url (str): Si se proporciona, sobreescribe config.BASE_URL.

    Retorna:
        (total_procesados, total_errores)
    """
    import requests as req

    if base_url:
        config.BASE_URL = base_url.rstrip("/")

    listing_url = config.BASE_URL + config.PRODUCTS_PATH
    logger.info("Iniciando scraper. URL de listado: %s", listing_url)

    products = []
    error_count = 0

    # --- Modo requests (por defecto) ---
    if not config.USE_SELENIUM:
        session = req.Session()
        session.headers.update(config.HEADERS)

        # Obtener todas las URLs de productos del listado paginado
        product_urls = get_product_links_requests(session, listing_url)

        if not product_urls:
            logger.warning("No se encontraron productos. Verifica BASE_URL y los selectores.")
            return 0, 0

        # Scrapear cada producto individualmente
        for i, url in enumerate(product_urls, start=1):
            logger.info("[%d/%d] Procesando: %s", i, len(product_urls), url)

            data = scrape_product_requests(session, url)

            # Considerar error si no se obtuvo nombre ni código
            if not data.get("nombre") and not data.get("codigo"):
                error_count += 1
            else:
                products.append(data)

            # Pausa entre requests para no saturar el servidor
            time.sleep(config.REQUEST_DELAY)

        session.close()

    # --- Modo Selenium ---
    else:
        import requests as req_img

        driver = _init_selenium_driver()
        img_session = req_img.Session()
        img_session.headers.update(config.HEADERS)

        try:
            product_urls = get_product_links_selenium(driver, listing_url)

            if not product_urls:
                logger.warning("Selenium: No se encontraron productos.")
                return 0, 0

            for i, url in enumerate(product_urls, start=1):
                logger.info("[%d/%d] Selenium procesando: %s", i, len(product_urls), url)

                data = scrape_product_selenium(driver, img_session, url)

                if not data.get("nombre") and not data.get("codigo"):
                    error_count += 1
                else:
                    products.append(data)

        finally:
            driver.quit()
            img_session.close()

    # Guardar todos los resultados en CSV
    storage.save_csv(products, config.OUTPUT_CSV)

    return len(products), error_count
