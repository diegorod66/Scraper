#!/usr/bin/env bash
# =============================================================================
# deploy_v1.1.0.sh — Sube los cambios de v1.1.0 a GitHub
# =============================================================================
# Uso:
#   1. Copiá todos los archivos al directorio de tu repo local
#   2. Ejecutá este script desde la raíz del repo:
#        bash deploy_v1.1.0.sh
# =============================================================================

set -e  # Salir inmediatamente si algún comando falla

VERSION="1.1.0"
BRANCH="main"
TAG="v${VERSION}"
COMMIT_MSG="feat: v${VERSION} — carpeta dinámica, log de sesión y deduplicación MD5"
TAG_MSG="v${VERSION}: carpeta de salida dinámica, scraper.log por sesión y deduplicación de imágenes por MD5"

echo ""
echo "============================================================"
echo "  Deploy Scraper de Productos ${TAG}"
echo "============================================================"
echo ""

# --- Verificar que estamos en un repo git ---
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Error: no estás dentro de un repositorio git."
    exit 1
fi

# --- Verificar rama activa ---
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "$BRANCH" ]; then
    echo "⚠️  Estás en la rama '$CURRENT_BRANCH', no en '$BRANCH'."
    read -p "   ¿Continuar de todas formas? [s/n]: " confirm
    if [[ "$confirm" != "s" && "$confirm" != "S" ]]; then
        echo "   Abortado."
        exit 0
    fi
fi

# --- Verificar que el tag no existe ya ---
if git tag | grep -q "^${TAG}$"; then
    echo "❌ El tag '${TAG}' ya existe. Abortando para no sobreescribir."
    echo "   Si querés forzar el reemplazo: git tag -d ${TAG} && git push origin :refs/tags/${TAG}"
    exit 1
fi

# --- Mostrar archivos a commitear ---
echo "📄 Archivos a incluir en el commit:"
git status --short
echo ""

# --- Stagear archivos modificados ---
git add output_manager.py
git add downloader.py
git add main.py
git add README.md
git add CHANGELOG.md
git add VERSION

# Verificar que hay algo para commitear
if git diff --cached --quiet; then
    echo "ℹ️  No hay cambios staged para commitear."
    echo "   Asegurate de haber copiado los archivos nuevos al repo."
    exit 1
fi

# --- Commit ---
echo "📝 Commiteando con mensaje:"
echo "   '${COMMIT_MSG}'"
echo ""
git commit -m "${COMMIT_MSG}"

# --- Tag de versión ---
echo "🏷️  Creando tag ${TAG}..."
git tag -a "${TAG}" -m "${TAG_MSG}"

# --- Push ---
echo ""
echo "🚀 Subiendo a GitHub (rama ${BRANCH} + tag ${TAG})..."
git push origin "${BRANCH}"
git push origin "${TAG}"

echo ""
echo "============================================================"
echo "  ✅ v${VERSION} publicada exitosamente en GitHub"
echo "============================================================"
echo ""
echo "  Próximo paso — crear el Release en GitHub:"
echo "  1. Ir a: https://github.com/diegorod66/Scraper/releases/new"
echo "  2. Seleccionar el tag: ${TAG}"
echo "  3. Pegar el contenido de RELEASE_NOTES.md como descripción"
echo "  4. Publicar"
echo ""
