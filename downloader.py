# =============================================================================
# downloader.py — Descarga de imágenes de productos con deduplicación MD5
# =============================================================================
# Descarga la imagen de cada producto y la guarda localmente.
# Usa el código y nombre del producto para generar nombres de archivo únicos.
#
# Deduplicación en dos niveles (en orden de evaluación):
#   1. Por nombre de archivo: si local_path ya existe, se omite sin calcular MD5.
#   2. Por hash MD5: si el contenido descargado es idéntico al de una imagen ya
#      guardada (aunque tenga distinto nombre de archivo), se omite y se registra
#      en el log cuál fue el archivo original con ese contenido.
#
# El índice MD5 es un dict de sesión {md5_hex → Path} construido una vez al
# inicializar el módulo con init_dedup_index() y actualizado con cada imagen
# nueva que se guarda exitosamente.
# =============================================================================

import hashlib
import logging
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Índice de deduplicación por MD5 (estado de sesión)
# ---------------------------------------------------------------------------
# Estructura: { md5_hex (str) → ruta_local (Path) }
# Se construye al llamar init_dedup_index() y se actualiza en download_image().
_md5_index: dict[str, Path] = {}


def init_dedup_index(images_dir) -> None:
    """
    Construye el índice MD5 a partir de las imágenes ya existentes en images_dir.

    Debe llamarse UNA VEZ antes de comenzar a descargar imágenes de una sesión,
    típicamente desde main.py después de crear la carpeta de salida.

    Si images_dir no existe o está vacía, el índice queda vacío (sin error).

    Parámetros:
        images_dir: str o Path con la ruta a la carpeta de imágenes.
    """
    global _md5_index
    _md5_index = {}

    target = Path(images_dir)
    if not target.exists():
        logger.debug("[DEDUP] Carpeta de imágenes aún no existe; índice MD5 vacío.")
        return

    count = 0
    for f in target.iterdir():
        if f.is_file():
            try:
                md5 = _compute_md5(f)
                _md5_index[md5] = f
                count += 1
            except OSError as e:
                logger.warning("[DEDUP] No se pudo leer '%s' para indexar: %s", f, e)

    logger.info("[DEDUP] Índice MD5 construido: %d imagen(es) existente(s).", count)


def _compute_md5(filepath: Path) -> str:
    """Calcula el hash MD5 de un archivo en disco."""
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _download_to_buffer(response: requests.Response) -> tuple[str, list[bytes]]:
    """
    Lee el body de la respuesta en chunks, calcula el MD5 al mismo tiempo
    y retorna (md5_hex, lista_de_chunks).

    Mantiene los chunks en memoria en vez de escribirlos a disco de inmediato,
    para poder verificar el MD5 antes de decidir si guardar.
    El impacto de memoria es mínimo para imágenes (típicamente < 5 MB).
    """
    h = hashlib.md5()
    chunks: list[bytes] = []
    for chunk in response.iter_content(chunk_size=8192):
        if chunk:
            h.update(chunk)
            chunks.append(chunk)
    return h.hexdigest(), chunks


# ---------------------------------------------------------------------------
# Helpers de nombre de archivo
# ---------------------------------------------------------------------------

def _sanitize_filename(text: str, max_length: int = 50) -> str:
    """
    Convierte texto arbitrario en un nombre de archivo seguro.
    Elimina caracteres especiales, espacios y limita la longitud.
    """
    sanitized = re.sub(r"[^\w\-]", "_", text, flags=re.UNICODE)
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    return sanitized[:max_length]


def _get_extension(image_url: str) -> str:
    """
    Determina la extensión del archivo de imagen a partir de la URL.
    Devuelve '.jpg' como extensión por defecto si no puede determinarse.
    """
    path = urlparse(image_url).path
    ext = os.path.splitext(path)[1].lower()
    valid_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp"}
    return ext if ext in valid_extensions else ".jpg"


# ---------------------------------------------------------------------------
# Función pública principal
# ---------------------------------------------------------------------------

def download_image(
    session: requests.Session,
    image_url: str,
    product_code: str,
    product_name: str,
) -> str:
    """
    Descarga la imagen de un producto con deduplicación en dos niveles.

    Nivel 1 — por nombre de archivo:
        Si local_path ya existe en disco, se omite la descarga completamente
        (comportamiento de caché original).

    Nivel 2 — por hash MD5:
        Se descarga el contenido a un buffer en memoria y se calcula su MD5.
        Si el MD5 ya está en el índice de sesión, significa que ese contenido
        ya fue guardado con otro nombre; se descarta el buffer y se registra
        en el log el archivo original que tiene ese mismo contenido.
        Si el MD5 es nuevo, se escribe el buffer a disco y se actualiza el índice.

    Parámetros:
        session      : Sesión requests activa con headers configurados.
        image_url    : URL absoluta de la imagen a descargar.
        product_code : Código/SKU del producto (usado en el nombre del archivo).
        product_name : Nombre del producto (usado en el nombre del archivo).

    Retorna:
        Ruta local relativa del archivo guardado, o cadena vacía si se omite/falla.
    """
    if not image_url:
        logger.debug("Sin URL de imagen para el producto '%s'.", product_name)
        return ""

    # Crear directorio de imágenes si no existe
    images_dir = Path(config.IMAGES_DIR)
    images_dir.mkdir(parents=True, exist_ok=True)

    # Construir nombre de archivo destino
    code_part = _sanitize_filename(product_code) if product_code else "sin_codigo"
    name_part = _sanitize_filename(product_name) if product_name else "sin_nombre"
    extension = _get_extension(image_url)
    filename = f"{code_part}_{name_part}{extension}"
    local_path = images_dir / filename

    # ----------------------------------------------------------------
    # Nivel 1 — deduplicación por nombre de archivo
    # ----------------------------------------------------------------
    if local_path.exists():
        logger.debug(
            "[DEDUP] Imagen omitida (ya existe por nombre): %s", local_path
        )
        return str(local_path)

    # ----------------------------------------------------------------
    # Descargar a buffer + calcular MD5
    # ----------------------------------------------------------------
    try:
        response = session.get(
            image_url,
            stream=True,
            timeout=config.REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        md5_hex, chunks = _download_to_buffer(response)

    except requests.exceptions.Timeout:
        logger.warning(
            "[IMG] Timeout al descargar imagen de '%s': %s", product_name, image_url
        )
        return ""
    except requests.exceptions.HTTPError as e:
        logger.warning(
            "[IMG] HTTP error al descargar imagen de '%s': %s", product_name, e
        )
        return ""
    except requests.exceptions.RequestException as e:
        logger.warning(
            "[IMG] Error de red al descargar imagen de '%s': %s", product_name, e
        )
        return ""

    # ----------------------------------------------------------------
    # Nivel 2 — deduplicación por MD5
    # ----------------------------------------------------------------
    if md5_hex in _md5_index:
        existing = _md5_index[md5_hex]
        logger.info(
            "[DEDUP] Imagen omitida (contenido duplicado MD5=%s). "
            "Ya guardada como: %s — producto: '%s'",
            md5_hex[:8],
            existing,
            product_name,
        )
        return str(existing)

    # ----------------------------------------------------------------
    # Guardar en disco
    # ----------------------------------------------------------------
    try:
        with open(local_path, "wb") as f:
            for chunk in chunks:
                f.write(chunk)

        # Registrar en el índice de sesión
        _md5_index[md5_hex] = local_path

        logger.info("[IMG] Imagen guardada: %s (MD5: %s)", local_path, md5_hex[:8])
        time.sleep(getattr(config, "IMAGE_DOWNLOAD_DELAY", 0.5))
        return str(local_path)

    except OSError as e:
        logger.warning("[IMG] Error al escribir imagen '%s': %s", local_path, e)
        # Eliminar archivo incompleto si quedó
        if local_path.exists():
            try:
                local_path.unlink()
            except OSError:
                pass
        return ""
