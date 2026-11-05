#!/bin/bash
# Build dist/MacBooth.app (and dist/MacBooth.zip) with PyInstaller.
# Usage: packaging/build_mac.sh [python]   (default: ~/pibooth-venv/bin/python)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${1:-$HOME/pibooth-venv/bin/python}"
BUILD="$ROOT/packaging/build"

"$PYTHON" -m pip install -q "pyinstaller==6.22.3"

# Application icon from the theme
mkdir -p "$BUILD/MacBooth.iconset"
ICON="$ROOT/pibooth/themes/droidknights/assets/app-icon.png"
for size in 16 32 128 256 512; do
    sips -z $size $size "$ICON" --out "$BUILD/MacBooth.iconset/icon_${size}x${size}.png" >/dev/null
    sips -z $((size * 2)) $((size * 2)) "$ICON" --out "$BUILD/MacBooth.iconset/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$BUILD/MacBooth.iconset" -o "$BUILD/MacBooth.icns"

# Configuration of this Mac, copied on the first launch on another Mac:
# home paths made portable, without the counters and the backups
CONFIG="${PIBOOTH_CONFIG:-$HOME/.config/pibooth}"
rm -rf "$BUILD/config"
mkdir -p "$BUILD/config"
for file in "$CONFIG"/pibooth.cfg "$CONFIG"/translations.cfg "$CONFIG"/*.json; do
    [ -f "$file" ] || continue
    [ "$(basename "$file")" = "counters.json" ] && continue
    sed "s#$HOME/#~/#g" "$file" > "$BUILD/config/$(basename "$file")"
done

"$PYTHON" -m PyInstaller --noconfirm --clean \
    --workpath "$BUILD/pyinstaller" --distpath "$ROOT/dist" \
    "$ROOT/packaging/MacBooth.spec"

rm -f "$ROOT/dist/MacBooth.zip"
ditto -c -k --keepParent "$ROOT/dist/MacBooth.app" "$ROOT/dist/MacBooth.zip"
echo "Built $ROOT/dist/MacBooth.app"
