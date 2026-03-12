# =============================================================================
# main.py — Punto de entrada del scraper
# =============================================================================
# Uso:
#   python main.py                          # Usa BASE_URL definida en config.py
#   python main.py --url https://sitio.com  # Sobreescribe BASE_URL desde CLI
#   python main.py --url https://sitio.com --log DEBUG  # Nivel de log detallado
#
# Instalación de dependencias:
#   pip install requests beautifulsoup4 lxml
#   pip install selenium webdriver-manager  # Solo si USE_SELENIUM = True en config.py
# =============================================================================

import argparse
import logging
import sys
import time

import config
import scraper


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
            "  python main.py --url https://www.tienda.com --log DEBUG\n"
        ),
    )

    parser_args.add_argument(
        "--url",
        type=str,
        default=None,
        metavar="URL",
        help=(
            "URL base del sitio a scrapear. "
            "Si no se proporciona, se usa BASE_URL definida en config.py."
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


def main() -> None:
    args = parse_args()
    setup_logging(args.log)

    logger = logging.getLogger(__name__)

    # Mostrar configuración activa al inicio
    effective_url = args.url or config.BASE_URL
    logger.info("=" * 60)
    logger.info("Scraper de productos iniciado")
    logger.info("URL objetivo  : %s", effective_url)
    logger.info("Sección       : %s", config.PRODUCTS_PATH)
    logger.info("Modo          : %s", "Selenium (JS)" if config.USE_SELENIUM else "requests (HTML estático)")
    logger.info("CSV salida    : %s", config.OUTPUT_CSV)
    logger.info("Carpeta imag. : %s", config.IMAGES_DIR)
    logger.info("Pausa requests: %.1f seg", config.REQUEST_DELAY)
    logger.info("=" * 60)

    start_time = time.time()

    try:
        total_ok, total_errors = scraper.run(base_url=args.url)
    except KeyboardInterrupt:
        logger.warning("Scraping interrumpido por el usuario (Ctrl+C).")
        sys.exit(0)
    except Exception as e:
        logger.critical("Error fatal no recuperable: %s", e, exc_info=True)
        sys.exit(1)

    elapsed = time.time() - start_time

    # Resumen final
    logger.info("=" * 60)
    logger.info("Scraping completado en %.1f segundos", elapsed)
    logger.info("Productos guardados : %d", total_ok)
    logger.info("Errores             : %d", total_errors)
    logger.info("Archivo CSV         : %s", config.OUTPUT_CSV)
    logger.info("Imágenes en         : %s/", config.IMAGES_DIR)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
