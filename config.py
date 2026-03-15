# =============================================================================
# config.py — Configuración centralizada del scraper
# =============================================================================
# INSTRUCCIONES DE USO:
#   1. Cambia BASE_URL por la URL raíz del sitio objetivo.
#   2. Ajusta PRODUCTS_PATH a la ruta de la sección de productos.
#   3. Si LISTING_MODE = True, todos los datos se extraen del listado directamente
#      (sin visitar páginas individuales de producto). Ideal para sitios que
#      muestran nombre, código, precio y stock en el listado.
#   4. Si LISTING_MODE = False, se usa SELECTORS para parsear cada página individual.
# =============================================================================

# --- URL del sitio objetivo ---
BASE_URL = "https://www.mayoristaomega.com.ar"

# Ruta relativa a la sección de listado de productos
PRODUCTS_PATH = "/lista-de-productos"

# =============================================================================
# LISTING_MODE = True → extrae todos los datos directamente del listado
#                       sin visitar páginas individuales de cada producto.
#                       Usar cuando el listado ya contiene nombre, código,
#                       precio, stock e imagen de cada producto.
# LISTING_MODE = False → sigue cada enlace al detalle del producto y parsea
#                        esa página con los selectores de SELECTORS.
# =============================================================================
LISTING_MODE = True

# --- Selectores para LISTING_MODE = True ---
# Configurados para mayoristaomega.com.ar (/lista-de-productos)
LISTING_SELECTORS = {
    "product_container": "div.product.text-center",
    "name": "h3.product-title",
    "code": "span.item-codigo span",
    "price": "span.item-precio",
    "stock": "div.cantidadstock i",
    "image": "img.product-image",
    "link": "figure.product-media a",
}

# =============================================================================
# Paginación del listado
# =============================================================================
# "infinite_scroll" → el sitio carga más productos via AJAX al hacer scroll.
#   Envía GET a PRODUCTS_PATH?page=N con el header X-Requested-With: XMLHttpRequest.
#   La respuesta es HTML parcial (solo los divs de producto, sin página completa).
#   El scraper itera page=1, 2, 3... hasta recibir una respuesta sin productos.
#
# "css_link" → paginación clásica via enlace HTML (usa LISTING_SELECTORS["pagination"]).
#
# "" (vacío) → sin paginación, una sola página.
# =============================================================================
LISTING_PAGINATION = "infinite_scroll"

# --- Selectores para LISTING_MODE = False (páginas individuales de producto) ---
# Configurados para scrapingcourse.com/ecommerce (WooCommerce) como referencia
SELECTORS = {
    "product_links": "li.product a.woocommerce-loop-product__link",
    "pagination": "a.next.page-numbers",
    "name": "h1.product_title",
    "code": "span.sku",
    "price": "p.price span.woocommerce-Price-amount",
    "stock": "p.stock",
    "description": "div.woocommerce-product-details__short-description",
    "image": "div.woocommerce-product-gallery__image img",
}

# --- Archivos de salida ---
OUTPUT_CSV = "productos.csv"
IMAGES_DIR = "imagenes_productos"

# =============================================================================
# NUEVO — Configuración para lectura de URLs y caché de HTML
# =============================================================================
# Archivo con las URLs a scrapear (una por línea).
# Puede ser una ruta relativa al directorio del scraper o absoluta.
URLS_FILE = "urls.txt"

# Directorio donde se guardan los HTML descargados antes del parseo.
# Se crea automáticamente si no existe.
# Estructura: html_cache/<slug-de-url>/page_0001.html, page_0002.html ...
HTML_CACHE_DIR = "html_cache"
# =============================================================================

# --- Comportamiento del scraper ---
# Pausa entre requests de páginas del listado (segundos)
REQUEST_DELAY = 2.0
# Pausa entre descargas de imágenes individuales (segundos)
IMAGE_DOWNLOAD_DELAY = 0.5
REQUEST_TIMEOUT = 15
MAX_RETRIES = 3
MAX_PAGES = 0

# --- Modo JavaScript (Selenium) ---
USE_SELENIUM = False

# --- Headers HTTP realistas ---
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
}
