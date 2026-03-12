# =============================================================================
# parser.py — Extracción de datos de la página individual de cada producto
# =============================================================================
# Usa los selectores definidos en config.SELECTORS para localizar cada campo.
# Si un campo no se encuentra, devuelve cadena vacía sin lanzar excepción.
# =============================================================================

import logging
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import config

logger = logging.getLogger(__name__)


def _get_text(soup: BeautifulSoup, selector: str) -> str:
    """
    Extrae y limpia el texto del primer elemento que coincida con el selector.
    Devuelve cadena vacía si el selector no encuentra nada.
    """
    if not selector:
        return ""
    element = soup.select_one(selector)
    if element is None:
        return ""
    return " ".join(element.get_text(separator=" ").split())


def _get_image_url(soup: BeautifulSoup, selector: str, base_url: str) -> str:
    """
    Extrae la URL de la imagen principal.
    Intenta los atributos 'src', 'data-src' y 'data-lazy-src' en ese orden.
    Si la URL es relativa la convierte a absoluta usando base_url.
    """
    if not selector:
        return ""
    img = soup.select_one(selector)
    if img is None:
        return ""

    url = (
        img.get("src")
        or img.get("data-src")
        or img.get("data-lazy-src")
        or ""
    )

    url = url.strip()

    # Usar urljoin para resolver correctamente cualquier tipo de URL relativa
    # (rutas con ../, /, o absolutas) respecto a la URL de la página del producto
    if url and not url.startswith("http"):
        url = urljoin(base_url, url)

    return url


def _clean_price(raw: str) -> str:
    """
    Limpia el precio eliminando símbolos de moneda y espacios extra.
    Devuelve únicamente el valor numérico con separadores.
    Ejemplo: "  $ 1.299,99 " -> "1.299,99"
    """
    if not raw:
        return ""
    # Eliminar símbolo de moneda y espacios
    cleaned = re.sub(r"[^\d.,]", "", raw).strip()
    return cleaned


def _clean_stock(raw: str) -> str:
    """
    Extrae el valor numérico del stock si viene con texto descriptivo.
    Ejemplo: "En stock: 15 unidades" -> "15"
    """
    if not raw:
        return ""
    numbers = re.findall(r"\d+", raw)
    return numbers[0] if numbers else raw.strip()


def parse_product(html: str, product_url: str = "") -> dict:
    """
    Parsea el HTML de la página individual de un producto y extrae todos los campos.

    Parámetros:
        html        (str): Contenido HTML de la página del producto.
        product_url (str): URL de la página del producto, usada para resolver
                           rutas de imagen relativas (ej. ../../media/...).

    Retorna:
        dict con claves: nombre, codigo, precio, cantidad, descripcion, imagen_url
    """
    soup = BeautifulSoup(html, "lxml")
    selectors = config.SELECTORS
    # Usar la URL del producto como base para resolver paths relativos de imagen
    base_url = product_url or config.BASE_URL

    # --- Nombre del producto ---
    nombre = _get_text(soup, selectors.get("name"))

    # --- Código / SKU del producto ---
    codigo = _get_text(soup, selectors.get("code"))

    # --- Precio ---
    precio_raw = _get_text(soup, selectors.get("price"))
    precio = _clean_price(precio_raw)

    # --- Cantidad en stock ---
    stock_raw = _get_text(soup, selectors.get("stock"))
    cantidad = _clean_stock(stock_raw)

    # --- Descripción ---
    descripcion = _get_text(soup, selectors.get("description"))

    # --- URL de la imagen principal ---
    imagen_url = _get_image_url(soup, selectors.get("image"), base_url)

    # Advertir si algún campo crítico está vacío
    if not nombre:
        logger.warning("Campo 'nombre' no encontrado con selector: %s", selectors.get("name"))
    if not codigo:
        logger.warning("Campo 'codigo' no encontrado con selector: %s", selectors.get("code"))

    return {
        "nombre": nombre,
        "codigo": codigo,
        "precio": precio,
        "cantidad": cantidad,
        "descripcion": descripcion,
        "imagen_url": imagen_url,
    }
