# Scraper de Productos

Scraper web modular en Python que recorre un sitio de productos, extrae datos clave, descarga imágenes y genera un archivo CSV.

## Características

- Navegación automática con paginación
- Extracción de: nombre, código, precio, stock, descripción e imagen
- Descarga de imágenes organizadas en `imagenes_productos/`
- Salida en `productos.csv` compatible con Excel (UTF-8 BOM)
- Manejo robusto de errores (timeouts, campos vacíos, HTTP errors)
- Modo JavaScript opcional con Selenium + Chrome headless

## Requisitos

- Python 3.9 o superior

## Instalación

```bash
pip install requests beautifulsoup4 lxml
```

Si el sitio requiere JavaScript (`USE_SELENIUM = True` en `config.py`):

```bash
pip install selenium webdriver-manager
```

## Uso

```bash
# Usa BASE_URL definida en config.py
python main.py

# Sobreescribe la URL desde la línea de comandos
python main.py --url https://www.tienda.com

# Con log detallado
python main.py --url https://www.tienda.com --log DEBUG
```

## Configuración

Edita **`config.py`** antes de ejecutar:

| Variable | Descripción |
|---|---|
| `BASE_URL` | URL raíz del sitio objetivo |
| `PRODUCTS_PATH` | Ruta relativa al listado de productos |
| `SELECTORS` | Selectores CSS para cada campo (ver tabla abajo) |
| `REQUEST_DELAY` | Pausa en segundos entre requests (default: `1.5`) |
| `MAX_PAGES` | Límite de páginas de listado a recorrer (`0` = sin límite) |
| `USE_SELENIUM` | `True` para sitios que requieren JavaScript |

### Selectores CSS a adaptar

Inspecciona el sitio objetivo con las DevTools del navegador (F12) y ajusta:

```python
SELECTORS = {
    "product_links": "a.product-item-link",  # Enlace a cada producto en el listado
    "pagination":    "li.next a",             # Enlace a la página siguiente
    "name":          "h1.product-name",       # Nombre del producto
    "code":          "span.product-sku",      # Código / SKU
    "price":         "p.price_color",         # Precio
    "stock":         "p.instock.availability",# Stock disponible
    "description":   "div#description ~ p",  # Descripción
    "image":         "div.item img",          # Imagen principal
}
```

## Archivos generados

```
imagenes_productos/
    {codigo}_{nombre}.jpg   ← una imagen por producto
productos.csv               ← datos de todos los productos
```

### Columnas del CSV

| Columna | Descripción |
|---|---|
| `nombre` | Nombre del producto |
| `codigo` | Código / SKU |
| `precio` | Precio (solo valor numérico) |
| `cantidad` | Stock disponible |
| `descripcion` | Descripción del producto |
| `imagen_url` | URL original de la imagen |
| `imagen_local` | Ruta local del archivo descargado |

## Estructura del proyecto

```
Scraper/
├── config.py       ← URL, selectores y parámetros
├── main.py         ← Punto de entrada (CLI + logging)
├── scraper.py      ← Navegación, paginación y orquestación
├── parser.py       ← Extracción de campos con BeautifulSoup
├── downloader.py   ← Descarga y caché de imágenes
└── storage.py      ← Escritura del CSV
```

## Sitio de prueba

El proyecto viene preconfigurado para [books.toscrape.com](https://books.toscrape.com), un sitio diseñado para practicar scraping.

```bash
python main.py
# Scrapes 2 páginas (40 libros) con imágenes y CSV incluidos
```
