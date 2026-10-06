#!/usr/bin/env bash
set -e

APPLET_UUID="avathings@telosdevgroup"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
SOURCE_DIR="$REPO_DIR/applet/$APPLET_UUID"
TARGET_DIR="$HOME/.local/share/cinnamon/applets/$APPLET_UUID"

echo "==> Installing $APPLET_UUID..."

mkdir -p "$HOME/.local/share/cinnamon/applets"

if [ -L "$TARGET_DIR" ] || [ -d "$TARGET_DIR" ]; then
    echo "Removing previous applet installation at $TARGET_DIR..."
    rm -rf "$TARGET_DIR"
fi

ln -s "$SOURCE_DIR" "$TARGET_DIR"
echo "Successfully symlinked $SOURCE_DIR -> $TARGET_DIR"

echo ""
echo "To enable the applet in Cinnamon:"
echo "1. Right click on your panel -> Applets"
echo "2. Find 'Avathings' under the Installed tab and click '+' (Add)"
echo "   (or run: ./scripts/enable-applet.sh)"
