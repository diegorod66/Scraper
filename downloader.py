# =============================================================================
# downloader.py — Descarga de imágenes de productos
# =============================================================================
# Descarga la imagen de cada producto y la guarda localmente.
# Usa el código y nombre del producto para generar nombres de archivo únicos.
# Si la imagen ya existe localmente, la omite (caché simple).
# =============================================================================

import logging
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

import config

logger = logging.getLogger(__name__)


def _sanitize_filename(text: str, max_length: int = 50) -> str:
    """
    Convierte texto arbitrario en un nombre de archivo seguro.
    Elimina caracteres especiales, espacios y limita la longitud.
    """
    # Reemplazar caracteres no alfanuméricos por guiones bajos
    sanitized = re.sub(r"[^\w\-]", "_", text, flags=re.UNICODE)
    # Colapsar múltiples guiones bajos consecutivos
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    return sanitized[:max_length]


def _get_extension(image_url: str) -> str:
    """
    Determina la extensión del archivo de imagen a partir de la URL.
    Devuelve '.jpg' como extensión por defecto si no puede determinarse.
    """
    path = urlparse(image_url).path
    ext = os.path.splitext(path)[1].lower()
    # Aceptar sólo extensiones de imagen conocidas
    valid_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp"}
    return ext if ext in valid_extensions else ".jpg"


def download_image(
    session: requests.Session,
    image_url: str,
    product_code: str,
    product_name: str,
) -> str:
    """
    Descarga la imagen de un producto y la guarda en IMAGES_DIR.

    Parámetros:
        session      : Sesión requests activa con headers configurados.
        image_url    : URL absoluta de la imagen a descargar.
        product_code : Código/SKU del producto (usado en el nombre del archivo).
        product_name : Nombre del producto (usado en el nombre del archivo).

    Retorna:
        Ruta local relativa del archivo guardado, o cadena vacía si falla.
    """
    # Validar que se proporcionó una URL
    if not image_url:
        logger.debug("Sin URL de imagen para el producto '%s'.", product_name)
        return ""

    # Crear directorio de imágenes si no existe
    images_dir = Path(config.IMAGES_DIR)
    images_dir.mkdir(parents=True, exist_ok=True)

    # Construir nombre de archivo a partir de código y nombre del producto
    code_part = _sanitize_filename(product_code) if product_code else "sin_codigo"
    name_part = _sanitize_filename(product_name) if product_name else "sin_nombre"
    extension = _get_extension(image_url)
    filename = f"{code_part}_{name_part}{extension}"
    local_path = images_dir / filename

    # Omitir descarga si el archivo ya existe (caché simple)
    if local_path.exists():
        logger.debug("Imagen ya existe localmente: %s", local_path)
        return str(local_path)

    # Descargar la imagen en modo streaming para no cargar todo en memoria
    try:
        response = session.get(
            image_url,
            stream=True,
            timeout=config.REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        with open(local_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        logger.info("Imagen guardada: %s", local_path)
        time.sleep(getattr(config, "IMAGE_DOWNLOAD_DELAY", 0.5))
        return str(local_path)

    except requests.exceptions.Timeout:
        logger.warning("Timeout al descargar imagen de '%s': %s", product_name, image_url)
    except requests.exceptions.HTTPError as e:
        logger.warning("HTTP error al descargar imagen de '%s': %s", product_name, e)
    except requests.exceptions.RequestException as e:
        logger.warning("Error de red al descargar imagen de '%s': %s", product_name, e)
    except OSError as e:
        logger.warning("Error al escribir imagen '%s': %s", local_path, e)

    # Si el archivo quedó incompleto, eliminarlo
    if local_path.exists():
        try:
            local_path.unlink()
        except OSError:
            pass

    return ""
