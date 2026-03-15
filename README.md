# Scraper de Productos

Scraper web modular en Python que recorre un sitio de productos, extrae datos clave, descarga imágenes y genera un archivo CSV.

## Características

- Navegación automática con paginación (clásica e infinite scroll)
- Extracción de: nombre, código, precio, stock, descripción e imagen
- **Carpeta de salida dinámica** por ejecución: `{sitio}_{YYYY-MM-DD}/`
- **Log de sesión** en `scraper.log` con timestamp de inicio y fin
- **Deduplicación de imágenes** por nombre de archivo y hash MD5
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

# Sin caché de HTML (flujo directo)
python main.py --no-cache

# Con archivo de URLs personalizado
python main.py --urls-file mis_urls.txt
```

## Estructura de salida

Cada ejecución genera automáticamente una carpeta con la fecha del día:

```
{nombre_sitio}_{YYYY-MM-DD}/
    ├── productos.csv          ← datos de todos los productos scrapeados
    ├── imagenes_productos/    ← imágenes descargadas (deduplicadas)
    └── scraper.log            ← log completo de la sesión
```

**Ejemplo:**
```
mayoristaomega.com.ar_2026-03-15/
    ├── productos.csv
    ├── imagenes_productos/
    │   ├── ABC123_Producto_Ejemplo.jpg
    │   └── ...
    └── scraper.log
```

Re-ejecutar el mismo día reutiliza la carpeta existente sin borrar contenido previo.

## Deduplicación de imágenes

Las imágenes se verifican en dos niveles antes de descargarse:

1. **Por nombre de archivo** — si el archivo ya existe en disco, se omite sin tráfico de red.
2. **Por hash MD5** — si el contenido ya fue descargado (aunque con distinto nombre), se omite y se registra en el log el archivo original con ese contenido.

Ambos eventos quedan registrados en `scraper.log`.

## Configuración

Edita **`config.py`** antes de ejecutar:

| Variable | Descripción |
|---|---|
| `BASE_URL` | URL raíz del sitio objetivo |
| `PRODUCTS_PATH` | Ruta relativa al listado de productos |
| `SELECTORS` | Selectores CSS para cada campo (ver tabla abajo) |
| `REQUEST_DELAY` | Pausa en segundos entre requests (default: `2.0`) |
| `MAX_PAGES` | Límite de páginas de listado a recorrer (`0` = sin límite) |
| `USE_SELENIUM` | `True` para sitios que requieren JavaScript |
| `LISTING_MODE` | `True` para extraer datos directo del listado |
| `LISTING_PAGINATION` | `"infinite_scroll"`, `"css_link"` o `""` |

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

## Columnas del CSV

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
├── config.py           ← URL, selectores y parámetros
├── main.py             ← Punto de entrada (CLI + logging)
├── output_manager.py   ← Carpeta dinámica y log de sesión
├── scraper.py          ← Navegación, paginación y orquestación
├── parser.py           ← Extracción de campos con BeautifulSoup
├── downloader.py       ← Descarga de imágenes con deduplicación MD5
├── storage.py          ← Escritura del CSV
├── html_cache.py       ← Caché de HTML en disco (FASE 1)
├── url_manager.py      ← Carga de URLs y menú interactivo
└── urls.txt            ← URLs a scrapear (una por línea)
```

## Sitio de prueba

El proyecto viene preconfigurado para [books.toscrape.com](https://books.toscrape.com), un sitio diseñado para practicar scraping.

```bash
python main.py
```

Genera automáticamente:
```
books.toscrape.com_2026-03-15/
    ├── productos.csv
    ├── imagenes_productos/
    └── scraper.log
```
