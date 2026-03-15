# Scraper de Productos v1.1.0

## ¿Qué hay de nuevo?

Esta versión agrega cuatro funcionalidades de calidad de vida que hacen al scraper más organizado, trazable y eficiente en el uso de ancho de banda.

---

## ✨ Novedades

### 📁 Carpeta de salida dinámica

Cada ejecución crea automáticamente una carpeta con el nombre del sitio y la fecha:

```
mayoristaomega.com.ar_2026-03-15/
    ├── productos.csv
    ├── imagenes_productos/
    └── scraper.log
```

No más archivos sueltos en la raíz del proyecto. Re-ejecutar el mismo día reutiliza la carpeta sin borrar nada.

---

### 📋 Log de sesión en archivo

Cada carpeta incluye un `scraper.log` con:
- Timestamp exacto de inicio y fin de cada ejecución
- Todos los eventos del scraper: productos encontrados, errores HTTP, imágenes omitidas, etc.
- Historial acumulativo si se ejecuta más de una vez el mismo día

---

### 🔍 Deduplicación de imágenes por MD5

Las imágenes se verifican en **dos niveles** antes de descargarse:

1. **Por nombre de archivo** — si el archivo ya existe en disco, skip inmediato (sin red)
2. **Por hash MD5** — si el mismo contenido ya fue descargado con otro nombre, se descarta y se registra en el log

Esto evita descargar duplicados aunque el sitio sirva la misma imagen con URLs distintas.

---

### 🗂️ Nuevo módulo `output_manager.py`

Módulo dedicado a la gestión de salidas, con API limpia:

```python
output_dir   = output_manager.create_output_dir(listing_url)
file_handler = output_manager.setup_file_logging(output_dir)
# ... scraping ...
output_manager.teardown_file_logging(file_handler)
```

---

## 📦 Archivos modificados

| Archivo | Tipo | Descripción |
|---|---|---|
| `output_manager.py` | ✅ Nuevo | Carpeta dinámica y logging a archivo |
| `downloader.py` | 🔧 Modificado | Deduplicación por nombre + MD5 |
| `main.py` | 🔧 Modificado | Integración del nuevo flujo por URL |
| `README.md` | 🔧 Modificado | Documentación actualizada |
| `CHANGELOG.md` | 🔧 Modificado | Historial de cambios |
| `VERSION` | 🔧 Modificado | `1.0.0` → `1.1.0` |

---

## ⚡ Instalación / Actualización

No hay dependencias nuevas. Si ya tenés el entorno configurado, simplemente actualizá los archivos:

```bash
git pull origin main
```

---

## 🔄 Compatibilidad

- ✅ 100% compatible con la configuración existente en `config.py`
- ✅ Sin cambios en `parser.py`, `scraper.py`, `storage.py`, `html_cache.py`, `url_manager.py`
- ✅ Todos los argumentos CLI (`--url`, `--no-cache`, `--log`, `--urls-file`) funcionan igual
