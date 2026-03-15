# =============================================================================
# url_manager.py — Carga de URLs desde archivo y menú interactivo de selección
# =============================================================================
# Módulo NUEVO. Provee dos funciones públicas:
#   load_urls(filepath)      → carga y valida las URLs del archivo
#   interactive_menu(urls)   → muestra el menú y retorna las URLs elegidas
# =============================================================================

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


def load_urls(filepath: str) -> list:
    """
    Lee las URLs del archivo indicado (una por línea).

    Ignora líneas vacías y comentarios que comiencen con '#'.
    Valida que cada línea tenga formato de URL (http:// o https://).

    Parámetros:
        filepath (str): Ruta al archivo de texto con las URLs.

    Retorna:
        Lista de strings con las URLs válidas encontradas.

    Lanza:
        FileNotFoundError si el archivo no existe.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(
            f"Archivo de URLs no encontrado: '{filepath}'\n"
            f"Crea el archivo con una URL por línea."
        )

    urls = []
    with open(path, encoding="utf-8") as f:
        for line_num, raw_line in enumerate(f, start=1):
            line = raw_line.strip()

            # Ignorar líneas vacías y comentarios
            if not line or line.startswith("#"):
                continue

            # Validación básica de formato URL
            if not re.match(r"^https?://", line, re.IGNORECASE):
                logger.warning(
                    "Línea %d ignorada (no parece una URL válida): '%s'",
                    line_num,
                    line,
                )
                continue

            urls.append(line)

    if not urls:
        logger.warning("El archivo '%s' no contiene URLs válidas.", filepath)

    logger.info("%d URL(s) cargadas desde '%s'.", len(urls), filepath)
    return urls


def _parse_selection(raw: str, total: int) -> list:
    """
    Interpreta la entrada del usuario y devuelve los índices (0-based) seleccionados.

    Formatos aceptados (basados en números 1-based mostrados en el menú):
        all / *          → todos
        1                → solo el elemento 1
        1,3,5            → elementos 1, 3 y 5
        2-5              → rango del 2 al 5 inclusive
        1,3-5,7          → combinación de individuales y rangos

    Parámetros:
        raw   (str): Entrada cruda del usuario.
        total (int): Total de URLs disponibles.

    Retorna:
        Lista de índices 0-based, sin duplicados, en orden.

    Lanza:
        ValueError si el formato es inválido o los números están fuera de rango.
    """
    raw = raw.strip().lower()

    if raw in ("all", "*", "todos", "todas"):
        return list(range(total))

    indices = set()
    # Separar por comas
    parts = [p.strip() for p in raw.split(",") if p.strip()]

    for part in parts:
        # Rango: "2-5"
        range_match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", part)
        if range_match:
            start, end = int(range_match.group(1)), int(range_match.group(2))
            if start > end:
                start, end = end, start
            if start < 1 or end > total:
                raise ValueError(
                    f"Rango '{part}' fuera de rango (1-{total})."
                )
            for i in range(start, end + 1):
                indices.add(i - 1)
            continue

        # Número individual: "3"
        if re.fullmatch(r"\d+", part):
            num = int(part)
            if num < 1 or num > total:
                raise ValueError(
                    f"Número '{num}' fuera de rango (1-{total})."
                )
            indices.add(num - 1)
            continue

        raise ValueError(f"Formato no reconocido: '{part}'")

    return sorted(indices)


def interactive_menu(urls: list) -> list:
    """
    Muestra en consola el listado numerado de URLs y solicita al usuario
    que seleccione cuáles scrapear.

    Formatos de entrada aceptados:
        all / *        → todas las URLs
        1              → solo la primera
        1,3            → primera y tercera
        2-4            → del 2 al 4 inclusive
        1,3-5,7        → combinación

    Parámetros:
        urls (list): Lista de URLs cargadas desde el archivo.

    Retorna:
        Sublista de URLs seleccionadas (en el orden original).
    """
    if not urls:
        logger.error("No hay URLs disponibles para mostrar en el menú.")
        return []

    # --- Encabezado del menú ---
    print()
    print("=" * 60)
    print("  URLS DISPONIBLES PARA SCRAPEAR")
    print("=" * 60)
    for i, url in enumerate(urls, start=1):
        print(f"  {i:>3}. {url}")
    print("-" * 60)
    print("  Opciones de selección:")
    print("    all       → todas las URLs")
    print("    1         → solo la URL 1")
    print("    1,3       → URLs 1 y 3")
    print("    2-5       → URLs del 2 al 5")
    print("    1,3-5,7   → combinación")
    print("=" * 60)

    # --- Loop de entrada hasta que sea válida ---
    while True:
        try:
            raw = input("  Selección: ").strip()
            if not raw:
                print("  Por favor ingresá una selección.")
                continue

            indices = _parse_selection(raw, len(urls))

            if not indices:
                print("  La selección resultó vacía. Intentá de nuevo.")
                continue

            selected = [urls[i] for i in indices]

            # Confirmación
            print()
            print(f"  {len(selected)} URL(s) seleccionada(s):")
            for url in selected:
                print(f"    • {url}")
            print()
            confirm = input("  Confirmar? [s/n]: ").strip().lower()
            if confirm in ("s", "si", "sí", "y", "yes", ""):
                return selected
            print()

        except ValueError as e:
            print(f"  Error de selección: {e}  — Intentá de nuevo.")
        except (KeyboardInterrupt, EOFError):
            print("\n  Operación cancelada.")
            return []
