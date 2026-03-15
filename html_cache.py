# =============================================================================
# html_cache.py — Descarga y almacenamiento local de HTML antes del scraping
# =============================================================================
# Módulo NUEVO. Separa el proceso en dos fases:
#
#   FASE 1 — Descarga: download_listing_pages()
#       Descarga todos los "trozos" HTML de una URL (primera carga + páginas
#       AJAX de infinite scroll) y los guarda en disco bajo html_cache/<slug>/.
#       No realiza ningún parseo.
#
#   FASE 2 — Lectura: load_html()
#       Lee un archivo HTML cacheado y devuelve su contenido como string.
#
# Funciones auxiliares:
#   url_to_slug(url) → nombre de directorio seguro derivado de la URL
#   list_cached_pages(cache_dir, slug) → lista de archivos .html cacheados
# =============================================================================

import logging
import re
import time
from pathlib import Path
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

import requests

import config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def url_to_slug(url: str) -> str:
    """
    Convierte una URL en un nombre de directorio seguro para el sistema de archivos.

    Ejemplo:
        "https://www.mayoristaomega.com.ar/lista-de-productos"
        → "mayoristaomega.com.ar__lista-de-productos"

    Parámetros:
        url (str): URL completa.

    Retorna:
        String con caracteres seguros (letras, dígitos, guiones y puntos).
    """
    parsed = urlparse(url)
    raw = f"{parsed.netloc}{parsed.path}"
    # Reemplazar secuencias de caracteres no seguros por '__'
    slug = re.sub(r"[^\w.\-]+", "__", raw).strip("_")
    return slug or "sitio"


def _build_page_filename(page_num: int) -> str:
    """Retorna el nombre de archivo para la página N del listado."""
    return f"page_{page_num:04d}.html"


def list_cached_pages(cache_dir: str, slug: str) -> list:
    """
    Devuelve la lista ordenada de archivos HTML cacheados para un slug dado.

    Parámetros:
        cache_dir (str): Directorio raíz de caché (config.HTML_CACHE_DIR).
        slug      (str): Identificador del sitio/URL (ver url_to_slug).

    Retorna:
        Lista de objetos Path ordenados por nombre (page_0001.html, page_0002.html...).
        Lista vacía si no existe el directorio o no hay archivos.
    """
    target_dir = Path(cache_dir) / slug
    if not target_dir.exists():
        return []
    return sorted(target_dir.glob("page_*.html"))


def load_html(filepath) -> str:
    """
    Lee el contenido de un archivo HTML cacheado.

    Parámetros:
        filepath: str o Path al archivo HTML.

    Retorna:
        Contenido del archivo como string (UTF-8).
        Cadena vacía si el archivo no existe o falla la lectura.
    """
    path = Path(filepath)
    if not path.exists():
        logger.warning("Archivo HTML cacheado no encontrado: %s", path)
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        logger.error("Error al leer HTML cacheado '%s': %s", path, e)
        return ""


# ---------------------------------------------------------------------------
# Descarga de páginas a caché (FASE 1)
# ---------------------------------------------------------------------------

def _save_html(html: str, dest_path: Path) -> None:
    """Escribe el HTML en disco de forma segura."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_text(html, encoding="utf-8")
    logger.debug("HTML guardado: %s (%d bytes)", dest_path, len(html))


def download_listing_pages(
    session: requests.Session,
    listing_url: str,
    cache_dir: str = None,
) -> list:
    """
    FASE 1 — Descarga todos los fragmentos HTML del listado y los guarda en disco.

    Comportamiento según config.LISTING_PAGINATION:

    "infinite_scroll":
        • Descarga listing_url sin header XHR → page_0001.html (HTML completo)
        • Descarga listing_url?page=2 con X-Requested-With: XMLHttpRequest → page_0002.html
        • Continúa hasta recibir una respuesta sin contenido de productos o vacía.

    "css_link" / "" (sin paginación):
        • Solo descarga listing_url → page_0001.html

    Parámetros:
        session     : requests.Session activa con headers base configurados.
        listing_url : URL completa del listado (ej. https://sitio.com/productos).
        cache_dir   : Directorio raíz de caché. Por defecto usa config.HTML_CACHE_DIR.

    Retorna:
        Lista de dicts con:
            {
                "filepath": Path   — ruta al archivo HTML guardado,
                "base_url": str    — URL de la que proviene el HTML
            }
        Lista vacía si la descarga inicial falla.
    """
    cache_root = Path(cache_dir or config.HTML_CACHE_DIR)
    slug = url_to_slug(listing_url)
    dest_dir = cache_root / slug
    pagination_mode = getattr(config, "LISTING_PAGINATION", "")
    xhr_headers = {"X-Requested-With": "XMLHttpRequest"}

    cached = []

    # -----------------------------------------------------------------------
    # Página inicial (siempre, sin header XHR → HTML completo de la página)
    # -----------------------------------------------------------------------
    logger.info("[HTML-CACHE] Descargando página inicial: %s", listing_url)
    html = _fetch(session, listing_url, extra_headers={})
    if not html:
        logger.error("[HTML-CACHE] No se pudo descargar la página inicial: %s", listing_url)
        return []

    page_path = dest_dir / _build_page_filename(1)
    _save_html(html, page_path)
    cached.append({"filepath": page_path, "base_url": listing_url})
    logger.info("[HTML-CACHE] Página 1 guardada → %s", page_path)

    # -----------------------------------------------------------------------
    # Páginas adicionales (solo en modo infinite_scroll)
    # -----------------------------------------------------------------------
    if pagination_mode == "infinite_scroll":
        page = 2
        consecutive_empty = 0

        while True:
            page_url = f"{listing_url}?page={page}"
            logger.info("[HTML-CACHE] Descargando página AJAX %d: %s", page, page_url)

            html_fragment = _fetch(session, page_url, extra_headers=xhr_headers)

            if not html_fragment or not html_fragment.strip():
                consecutive_empty += 1
                logger.info(
                    "[HTML-CACHE] Respuesta vacía en página %d (consecutivos: %d).",
                    page, consecutive_empty,
                )
                if consecutive_empty >= 2:
                    logger.info("[HTML-CACHE] Fin de paginación detectado.")
                    break
                page += 1
                time.sleep(config.REQUEST_DELAY)
                continue

            # Verificar que la respuesta tenga productos antes de guardar
            from bs4 import BeautifulSoup
            container_sel = config.LISTING_SELECTORS.get("product_container", "")
            if container_sel:
                soup = BeautifulSoup(html_fragment, "lxml")
                if not soup.select(container_sel):
                    consecutive_empty += 1
                    logger.info(
                        "[HTML-CACHE] Sin productos en página %d (consecutivos: %d).",
                        page, consecutive_empty,
                    )
                    if consecutive_empty >= 2:
                        logger.info("[HTML-CACHE] Fin de paginación detectado.")
                        break
                    page += 1
                    time.sleep(config.REQUEST_DELAY)
                    continue

            consecutive_empty = 0
            page_path = dest_dir / _build_page_filename(page)
            _save_html(html_fragment, page_path)
            cached.append({"filepath": page_path, "base_url": listing_url})
            logger.info("[HTML-CACHE] Página %d guardada → %s", page, page_path)

            page += 1
            time.sleep(config.REQUEST_DELAY)

    logger.info(
        "[HTML-CACHE] Descarga completa: %d página(s) guardadas en '%s'.",
        len(cached), dest_dir,
    )
    return cached


def _fetch(session: requests.Session, url: str, extra_headers: dict) -> str:
    """
    Realiza un GET con reintentos y devuelve el HTML como string.
    Retorna cadena vacía en caso de error persistente.
    """
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            response = session.get(
                url,
                timeout=config.REQUEST_TIMEOUT,
                headers=extra_headers,
            )
            response.raise_for_status()
            response.encoding = response.apparent_encoding or "utf-8"
            return response.text
        except requests.exceptions.Timeout:
            logger.warning("Timeout en '%s' (intento %d/%d)", url, attempt, config.MAX_RETRIES)
        except requests.exceptions.RequestException as e:
            logger.warning("Error en '%s' (intento %d/%d): %s", url, attempt, config.MAX_RETRIES, e)

        if attempt < config.MAX_RETRIES:
            time.sleep(config.REQUEST_DELAY * attempt)

    return ""
