# =============================================================================
# main.py — Punto de entrada del scraper
# =============================================================================
# Uso básico (comportamiento original, sin cambios):
#   python main.py                          # Usa BASE_URL definida en config.py
#   python main.py --url https://sitio.com  # Sobreescribe BASE_URL desde CLI
#   python main.py --url https://sitio.com --log DEBUG
#
# Flujo con archivo de URLs y caché de HTML:
#   python main.py                          # Si existe urls.txt, muestra el menú
#   python main.py --urls-file mis_urls.txt # Usa un archivo de URLs personalizado
#   python main.py --no-cache               # Saltea la fase de caché (flujo directo)
#
# Estructura de salida generada automáticamente por ejecución:
#   {nombre_sitio}_{YYYY-MM-DD}/
#       productos.csv          ← datos de todos los productos scrapeados
#       imagenes_productos/    ← imágenes descargadas
#       scraper.log            ← log completo de la sesión
#
# Instalación de dependencias:
#   pip install requests beautifulsoup4 lxml
#   pip install selenium webdriver-manager  # Solo si USE_SELENIUM = True en config.py
# =============================================================================

import argparse
import logging
import sys
import time
from pathlib import Path

import requests

import config
import downloader    # necesario para init_dedup_index
import html_cache
import output_manager  # NUEVO
import scraper
import storage
import url_manager


def setup_logging(level: str) -> None:
    """
    Configura el sistema de logging con formato legible en consola.
    Niveles disponibles: DEBUG, INFO, WARNING, ERROR, CRITICAL
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )


def parse_args() -> argparse.Namespace:
    """
    Define y parsea los argumentos de línea de comandos.
    """
    parser_args = argparse.ArgumentParser(
        description="Scraper web de productos — extrae datos y descarga imágenes.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Ejemplos:\n"
            "  python main.py\n"
            "  python main.py --url https://www.tienda.com\n"
            "  python main.py --urls-file mis_urls.txt\n"
            "  python main.py --no-cache --log DEBUG\n"
        ),
    )

    parser_args.add_argument(
        "--url",
        type=str,
        default=None,
        metavar="URL",
        help=(
            "URL del listado a scrapear. "
            "Si no se proporciona, se usa BASE_URL + PRODUCTS_PATH de config.py "
            "o las URLs del archivo urls.txt si existe."
        ),
    )

    parser_args.add_argument(
        "--urls-file",
        type=str,
        default=None,
        metavar="ARCHIVO",
        help=(
            f"Ruta al archivo de texto con las URLs (una por línea). "
            f"Por defecto: '{config.URLS_FILE}' (definido en config.py)."
        ),
    )

    parser_args.add_argument(
        "--no-cache",
        action="store_true",
        default=False,
        help=(
            "Deshabilita la descarga previa de HTML. "
            "El scraper hace los requests directamente sin guardar en disco. "
            "Comportamiento idéntico al flujo original."
        ),
    )

    parser_args.add_argument(
        "--log",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        metavar="NIVEL",
        help="Nivel de detalle del log (DEBUG, INFO, WARNING, ERROR). Por defecto: INFO",
    )

    return parser_args.parse_args()


# =============================================================================
# Flujo con caché de HTML (FASE 1 + FASE 2)
# =============================================================================

def _run_with_cache(listing_url: str, csv_path: str) -> tuple:
    """
    Ejecuta el scraping en dos fases para una URL dada:

    FASE 1 — Descarga y guarda todos los HTML del listado en disco.
    FASE 2 — Parsea los productos a partir de los archivos guardados.

    Parámetros:
        listing_url (str): URL completa del listado de productos.
        csv_path    (str): Ruta del archivo CSV de salida.

    Retorna:
        (total_ok, total_errores)
    """
    logger = logging.getLogger(__name__)

    session = requests.Session()
    session.headers.update(config.HEADERS)

    try:
        # --- FASE 1: Descargar todo el HTML a disco ---
        logger.info("FASE 1 — Descargando HTML de: %s", listing_url)
        cached_pages = html_cache.download_listing_pages(
            session=session,
            listing_url=listing_url,
            cache_dir=config.HTML_CACHE_DIR,
        )

        if not cached_pages:
            logger.warning("FASE 1 fallida: no se pudo descargar HTML de: %s", listing_url)
            return 0, 0

        logger.info("FASE 1 completada: %d página(s) guardadas.", len(cached_pages))

        # --- FASE 2: Parsear desde los archivos HTML guardados ---
        logger.info("FASE 2 — Parseando desde caché local...")
        products, error_count = scraper.scrape_from_cached_pages(session, cached_pages)

        if not products:
            logger.warning("FASE 2: sin productos extraídos de: %s", listing_url)
            return 0, error_count

        # Guardar CSV
        storage.save_csv(products, csv_path)
        return len(products), error_count

    finally:
        session.close()


# =============================================================================
# Resolución de URLs a scrapear
# =============================================================================

def _resolve_urls(args) -> list:
    """
    Determina la lista de URLs a scrapear según los argumentos recibidos.

    Prioridad:
        1. --url <URL>      → usa esa URL directamente, sin menú
        2. --urls-file / urls.txt existe → carga el archivo y muestra el menú
        3. Fallback         → usa config.BASE_URL + config.PRODUCTS_PATH

    Retorna:
        Lista de URLs (strings) a procesar.
    """
    logger = logging.getLogger(__name__)

    # 1. URL individual por CLI → sin menú
    if args.url:
        logger.info("URL proporcionada por CLI: %s", args.url)
        return [args.url]

    # 2. Archivo de URLs
    urls_file = args.urls_file or config.URLS_FILE
    if Path(urls_file).exists():
        try:
            all_urls = url_manager.load_urls(urls_file)
        except FileNotFoundError as e:
            logger.warning("No se pudo leer el archivo de URLs: %s", e)
            all_urls = []

        if all_urls:
            if len(all_urls) == 1:
                logger.info("Una sola URL en '%s': %s", urls_file, all_urls[0])
                return all_urls

            selected = url_manager.interactive_menu(all_urls)
            if selected:
                return selected
            logger.info("Selección cancelada por el usuario.")
            sys.exit(0)

    # 3. Fallback a configuración
    fallback = config.BASE_URL + config.PRODUCTS_PATH
    logger.info("urls.txt no encontrado. Usando URL de config: %s", fallback)
    return [fallback]


# =============================================================================
# Configuración de rutas de salida por URL  (MODIFICADO)
# =============================================================================

def _configure_output_paths(output_dir: Path) -> tuple[str, str]:
    """
    Actualiza config.OUTPUT_CSV y config.IMAGES_DIR para apuntar dentro de
    output_dir y retorna ambas rutas como strings.

    Al actualizar el módulo config en tiempo de ejecución, todos los módulos
    (scraper, downloader, storage) usan automáticamente las rutas correctas
    sin necesidad de pasarlas explícitamente por cada función.

    Parámetros:
        output_dir (Path): Carpeta de salida de la sesión actual.

    Retorna:
        (csv_path, images_dir)
    """
    csv_path = str(output_dir / "productos.csv")
    images_dir = str(output_dir / "imagenes_productos")

    config.OUTPUT_CSV = csv_path
    config.IMAGES_DIR = images_dir

    return csv_path, images_dir


# =============================================================================
# Punto de entrada principal
# =============================================================================

def main() -> None:
    args = parse_args()
    setup_logging(args.log)

    logger = logging.getLogger(__name__)

    # --- Resolver URLs ---
    urls_to_scrape = _resolve_urls(args)

    # --- Mostrar configuración activa ---
    logger.info("=" * 60)
    logger.info("Scraper de productos iniciado")
    logger.info("URLs a procesar  : %d", len(urls_to_scrape))
    logger.info("Modo requests    : %s", "Selenium (JS)" if config.USE_SELENIUM else "requests (HTML estático)")
    logger.info("Caché de HTML    : %s", "DESHABILITADO (--no-cache)" if args.no_cache else config.HTML_CACHE_DIR)
    logger.info("Pausa requests   : %.1f seg", config.REQUEST_DELAY)
    logger.info("=" * 60)

    start_time = time.time()
    grand_total_ok = 0
    grand_total_errors = 0

    for i, listing_url in enumerate(urls_to_scrape, start=1):

        logger.info("")
        logger.info("── URL %d/%d ──────────────────────────────────────────", i, len(urls_to_scrape))
        logger.info("Listado : %s", listing_url)

        # ----------------------------------------------------------------
        # NUEVO — Crear carpeta de salida dinámica para esta URL
        # ----------------------------------------------------------------
        output_dir = output_manager.create_output_dir(listing_url)

        # ----------------------------------------------------------------
        # NUEVO — Activar logging a archivo dentro de la carpeta de salida
        # ----------------------------------------------------------------
        file_handler = output_manager.setup_file_logging(output_dir)

        # ----------------------------------------------------------------
        # NUEVO — Apuntar config a las rutas dentro de output_dir
        # ----------------------------------------------------------------
        csv_path, images_dir = _configure_output_paths(output_dir)

        logger.info("CSV     : %s", csv_path)
        logger.info("Imágenes: %s", images_dir)
        logger.info("")

        # ----------------------------------------------------------------
        # NUEVO — Inicializar índice MD5 con imágenes ya existentes
        # ----------------------------------------------------------------
        downloader.init_dedup_index(images_dir)

        try:
            if args.no_cache:
                total_ok, total_errors = scraper.run(
                    listing_url_override=listing_url,
                    output_csv=csv_path,
                )
            else:
                total_ok, total_errors = _run_with_cache(listing_url, csv_path)

        except KeyboardInterrupt:
            logger.warning("Scraping interrumpido por el usuario (Ctrl+C).")
            output_manager.teardown_file_logging(file_handler)
            sys.exit(0)
        except Exception as e:
            logger.critical(
                "Error fatal procesando '%s': %s", listing_url, e, exc_info=True
            )
            total_ok, total_errors = 0, 1

        grand_total_ok += total_ok
        grand_total_errors += total_errors

        logger.info(
            "Resultado URL %d: %d productos, %d errores — CSV: %s",
            i, total_ok, total_errors, csv_path,
        )

        # ----------------------------------------------------------------
        # NUEVO — Cerrar el log de archivo antes de pasar a la próxima URL
        # ----------------------------------------------------------------
        output_manager.teardown_file_logging(file_handler)

    # --- Resumen final ---
    elapsed = time.time() - start_time
    logger.info("")
    logger.info("=" * 60)
    logger.info("Scraping completado en %.1f segundos", elapsed)
    logger.info("URLs procesadas     : %d", len(urls_to_scrape))
    logger.info("Productos guardados : %d", grand_total_ok)
    logger.info("Errores totales     : %d", grand_total_errors)
    logger.info("Estructura de salida:")
    for url in urls_to_scrape:
        site = output_manager.get_site_name(url)
        from datetime import date
        folder = f"{site}_{date.today().strftime('%Y-%m-%d')}/"
        logger.info("  %s", folder)
        logger.info("    ├── productos.csv")
        logger.info("    ├── imagenes_productos/")
        logger.info("    └── scraper.log")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
