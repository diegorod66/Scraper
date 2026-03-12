# =============================================================================
# storage.py — Escritura de resultados en archivo CSV
# =============================================================================
# Genera productos.csv con una fila por producto y columnas fijas.
# Usa codificación UTF-8 con BOM para compatibilidad directa con Excel.
# =============================================================================

import csv
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Columnas del CSV en orden fijo
CSV_COLUMNS = [
    "nombre",
    "codigo",
    "precio",
    "cantidad",
    "descripcion",
    "imagen_url",
    "imagen_local",
]


def save_csv(products: list, filepath: str) -> None:
    """
    Escribe la lista de productos en un archivo CSV.

    Parámetros:
        products (list[dict]): Lista de diccionarios con los datos de cada producto.
                               Cada dict debe contener las claves de CSV_COLUMNS.
        filepath (str)       : Ruta del archivo CSV de salida.

    Comportamiento:
        - Sobreescribe el archivo si ya existe.
        - Filas con claves adicionales son ignoradas (extrasaction='ignore').
        - Filas con claves faltantes se rellenan con cadena vacía.
        - Codificación UTF-8-sig (con BOM) para compatibilidad con Excel en Windows.
    """
    if not products:
        logger.warning("No hay productos para guardar en el CSV.")
        return

    output_path = Path(filepath)

    # Asegurar que el directorio destino existe
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(output_path, mode="w", newline="", encoding="utf-8-sig") as csvfile:
            writer = csv.DictWriter(
                csvfile,
                fieldnames=CSV_COLUMNS,
                extrasaction="ignore",
            )

            # Escribir fila de cabeceras
            writer.writeheader()

            for product in products:
                # Rellenar claves faltantes con cadena vacía para evitar KeyError
                row = {col: product.get(col, "") for col in CSV_COLUMNS}
                writer.writerow(row)

        logger.info("CSV guardado en '%s' con %d productos.", output_path, len(products))

    except OSError as e:
        logger.error("Error al escribir el archivo CSV '%s': %s", output_path, e)
        raise
