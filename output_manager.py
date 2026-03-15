# =============================================================================
# output_manager.py — Gestión de carpeta de salida y log de sesión
# =============================================================================
# Responsabilidades:
#   1. Crear la carpeta de salida con formato {sitio}_{YYYY-MM-DD} a partir
#      de la URL que se está scrapeando.
#   2. Agregar un FileHandler al logger raíz que escribe en scraper.log
#      dentro de esa carpeta, registrando todos los eventos de la sesión.
#
# Uso típico en main.py:
#   output_dir   = output_manager.create_output_dir(listing_url)
#   file_handler = output_manager.setup_file_logging(output_dir)
#   # ... ejecutar scraper ...
#   output_manager.teardown_file_logging(file_handler)
# =============================================================================

import logging
import re
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_site_name(url: str) -> str:
    """
    Extrae el nombre del sitio de una URL como string seguro para carpetas.

    Elimina 'www.' y reemplaza caracteres no permitidos por guiones bajos.

    Ejemplos:
        "https://www.mayoristaomega.com.ar/lista-de-productos"
            → "mayoristaomega.com.ar"
        "https://books.toscrape.com/catalogue"
            → "books.toscrape.com"
    """
    parsed = urlparse(url)
    netloc = parsed.netloc or url

    # Quitar prefijo www.
    netloc = re.sub(r"^www\.", "", netloc, flags=re.IGNORECASE)

    # Reemplazar caracteres no seguros para el sistema de archivos
    safe = re.sub(r"[^\w.\-]", "_", netloc).strip("_")
    return safe or "sitio"


# ---------------------------------------------------------------------------
# Carpeta de salida
# ---------------------------------------------------------------------------

def create_output_dir(listing_url: str) -> Path:
    """
    Crea y retorna la carpeta de salida para una sesión de scraping.

    Formato del nombre: {nombre_sitio}_{YYYY-MM-DD}
    Ejemplo: mayoristaomega.com.ar_2026-03-15/

    Si la carpeta ya existe (re-ejecución del mismo día) la reutiliza;
    nunca sobreescribe ni borra contenido previo.

    Parámetros:
        listing_url (str): URL del listado que se va a scrapear.

    Retorna:
        Path de la carpeta creada (o ya existente).
    """
    site_name = get_site_name(listing_url)
    today = date.today().strftime("%Y-%m-%d")
    folder_name = f"{site_name}_{today}"

    output_dir = Path(folder_name)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Carpeta de salida: %s", output_dir.resolve())
    return output_dir


# ---------------------------------------------------------------------------
# Logging a archivo
# ---------------------------------------------------------------------------

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_file_logging(output_dir: Path) -> logging.FileHandler:
    """
    Agrega un FileHandler al logger raíz que escribe en {output_dir}/scraper.log.

    Registra un encabezado con la fecha/hora exacta de inicio de sesión.
    El handler se añade al logger raíz para capturar todos los módulos.

    Parámetros:
        output_dir (Path): Carpeta de salida donde se creará scraper.log.

    Retorna:
        El FileHandler creado (guardarlo para pasarlo a teardown_file_logging).
    """
    log_path = output_dir / "scraper.log"
    handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    # Encabezado de sesión — facilita identificar cada ejecución en el log
    separator = "=" * 70
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    handler.stream.write(f"\n{separator}\n")
    handler.stream.write(f"  INICIO DE SESIÓN: {now}\n")
    handler.stream.write(f"{separator}\n")
    handler.stream.flush()

    logger.info("Log de sesión iniciado: %s", log_path)
    return handler


def teardown_file_logging(handler: logging.FileHandler) -> None:
    """
    Escribe el pie de sesión, remueve el FileHandler del logger raíz y lo cierra.

    Siempre llamar esto en un bloque finally para garantizar el cierre limpio
    del archivo de log, incluso si el scraping falla.

    Parámetros:
        handler (logging.FileHandler): Handler retornado por setup_file_logging.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    separator = "=" * 70
    try:
        handler.stream.write(f"{separator}\n")
        handler.stream.write(f"  FIN DE SESIÓN: {now}\n")
        handler.stream.write(f"{separator}\n\n")
        handler.stream.flush()
    except Exception:
        pass

    logging.getLogger().removeHandler(handler)
    handler.close()
