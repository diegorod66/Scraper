# =============================================================================
# config.py — Configuración centralizada del scraper
# =============================================================================
# INSTRUCCIONES DE USO:
#   1. Cambia BASE_URL por la URL raíz del sitio objetivo.
#   2. Ajusta PRODUCTS_PATH a la ruta de la sección de productos.
#   3. Modifica los valores en SELECTORS según la estructura HTML del sitio.
#      Puedes inspeccionar los selectores con las DevTools del navegador (F12).
# =============================================================================

# --- URL del sitio objetivo ---
# Sitio de prueba: books.toscrape.com (diseñado para practicar scraping)
BASE_URL = "https://books.toscrape.com"

# Ruta relativa a la sección de listado de productos
# books.toscrape.com usa /catalogue/page-1.html como listado principal
PRODUCTS_PATH = "/catalogue/page-1.html"

# --- Selectores CSS adaptables ---
# Configurados para books.toscrape.com
# Modificar estos valores al cambiar de sitio objetivo.
SELECTORS = {
    # Enlace de cada producto en el listado (dentro de article.product_pod)
    "product_links": "article.product_pod h3 a",

    # Enlace a la siguiente página de paginación
    "pagination": "li.next a",

    # Nombre del producto en su página individual
    "name": "article.product_page h1",

    # Código UPC del producto (primera celda de la tabla de detalles)
    "code": "table.table tr:first-child td",

    # Precio del producto
    "price": "p.price_color",

    # Disponibilidad / stock (contiene texto como "In stock (22 available)")
    "stock": "p.instock.availability",

    # Párrafo de descripción (está después del div#product_description)
    "description": "div#product_description ~ p",

    # Imagen principal del producto (dentro de div.item.active en el carrusel)
    "image": "div.item img",
}

# --- Archivos de salida ---
OUTPUT_CSV = "productos.csv"
IMAGES_DIR = "imagenes_productos"

# --- Comportamiento del scraper ---
# Pausa en segundos entre cada request (respetar el servidor)
REQUEST_DELAY = 1.5

# Timeout en segundos para cada request HTTP
REQUEST_TIMEOUT = 15

# Número máximo de reintentos por producto ante errores transitorios
MAX_RETRIES = 3

# Número máximo de páginas de listado a recorrer (0 = sin límite, recorre todo el sitio)
MAX_PAGES = 2

# --- Modo JavaScript (Selenium) ---
# Cambiar a True si el sitio carga productos con JavaScript (SPA, React, etc.)
USE_SELENIUM = False

# --- Headers HTTP realistas ---
# Simular un navegador real para evitar bloqueos básicos
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    # Omitir brotli (br): requests no lo descomprime nativamente.
    # requests gestiona gzip/deflate automáticamente sin este header.
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
}
