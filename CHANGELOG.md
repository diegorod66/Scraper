# Changelog

Todos los cambios notables de este proyecto están documentados aquí.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/).
Versionado semántico: [SemVer](https://semver.org/lang/es/).

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
