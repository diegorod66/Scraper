# Changelog

Todos los cambios notables de este proyecto están documentados aquí.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/).
Versionado semántico: [SemVer](https://semver.org/lang/es/).

---

## [1.1.0] - 2026-03-15

### Agregado
- `output_manager.py`: nuevo módulo con dos responsabilidades:
  - `create_output_dir(url)`: crea la carpeta de salida `{sitio}_{YYYY-MM-DD}/`
    extrayendo el nombre del sitio de la URL scrapeada.
  - `setup_file_logging(output_dir)` / `teardown_file_logging(handler)`:
    agrega un `FileHandler` al logger raíz que escribe `scraper.log` dentro
    de la carpeta de salida, registrando fecha/hora de inicio y fin de sesión.

### Modificado
- `downloader.py`: deduplicación de imágenes en dos niveles:
  - **Nivel 1 (nombre)**: si el archivo de destino ya existe en disco, se omite
    sin calcular MD5 (comportamiento de caché preexistente, sin cambios).
  - **Nivel 2 (MD5)**: se descarga el contenido a un buffer en memoria, se
    calcula su MD5 y se compara contra el índice de sesión. Si el hash ya existe
    (misma imagen con distinto nombre de archivo), se descarta el buffer y se
    registra en el log el archivo original con ese contenido.
  - Nueva función pública `init_dedup_index(images_dir)`: construye el índice
    MD5 `{md5_hex → Path}` a partir de las imágenes existentes. Debe llamarse
    una vez por sesión antes de empezar a descargar.
- `main.py`:
  - Integra `output_manager.create_output_dir()` por cada URL procesada.
  - Integra `output_manager.setup_file_logging()` / `teardown_file_logging()`.
  - Llama a `downloader.init_dedup_index()` con la carpeta de imágenes de sesión.
  - Actualiza `config.OUTPUT_CSV` y `config.IMAGES_DIR` en tiempo de ejecución
    para que todos los módulos escriban dentro de la carpeta de salida correcta.
  - Elimina `_csv_path_for_url()` (reemplazado por `output_manager`).
  - Agrega resumen visual de la estructura de archivos generada al finalizar.

### Estructura de salida por ejecución
```
{nombre_sitio}_{YYYY-MM-DD}/
    ├── productos.csv          ← datos scrapeados
    ├── imagenes_productos/    ← imágenes descargadas
    └── scraper.log            ← log completo de la sesión
```

---

## [1.0.0] - 2026-03-15

### Agregado
- `scraper.py`: scraper modular con soporte requests y Selenium
- `parser.py`: extracción de datos por selectores CSS configurables
- `downloader.py`: descarga de imágenes con reintentos y pausa configurable
- `storage.py`: exportación a CSV con encoding UTF-8-sig (compatible Excel)
- `config.py`: configuración centralizada (URL, selectores, delays, modo)
- `main.py`: punto de entrada con argumentos CLI (`--url`, `--log`)
- `url_manager.py`: carga de URLs desde `urls.txt` y menú interactivo de selección
- `html_cache.py`: descarga previa de HTML a disco (FASE 1) antes del parseo
- `urls.txt`: archivo de URLs de ejemplo (una por línea)
- `.gitignore`: exclusión de caché, imágenes, CSVs y artefactos de Python

### Características principales
- Modo `LISTING_MODE`: extrae datos directamente del listado sin visitar páginas individuales
- Paginación `infinite_scroll`: soporte para sitios con carga AJAX por scroll (`?page=N`)
- Flujo en dos fases: descarga HTML → parseo desde caché local
- Flag `--no-cache`: modo directo sin caché (comportamiento original)
- Soporte multi-URL con CSV separado por sitio (`productos_<slug>.csv`)
- Selección de URLs con rangos, individuales y combinaciones (`1,3-5,all`)

---

<!-- Plantilla para próximas versiones:

## [X.Y.Z] - AAAA-MM-DD

### Agregado
- Nueva funcionalidad

### Modificado
- Cambio en funcionalidad existente

### Corregido
- Bug fix

### Eliminado
- Funcionalidad removida

-->
