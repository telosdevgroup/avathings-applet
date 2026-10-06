#!/usr/bin/env bash
set -e

APPLET_UUID="avathings@telosdevgroup"

CURRENT_APPLETS=$(gsettings get org.cinnamon enabled-applets)

if echo "$CURRENT_APPLETS" | grep -q "$APPLET_UUID"; then
    echo "Applet '$APPLET_UUID' is already enabled."
    exit 0
fi

# Find next applet ID
NEXT_ID=$(echo "$CURRENT_APPLETS" | grep -oP ':\K[0-9]+(?=\x27)' | sort -n | tail -1)
NEXT_ID=$((NEXT_ID + 1))

# Append applet to panel1 right section
ENTRY="panel1:right:0:$APPLET_UUID:$NEXT_ID"
NEW_APPLETS=$(echo "$CURRENT_APPLETS" | sed "s/]$/, '$ENTRY']/")

echo "Enabling $ENTRY..."
gsettings set org.cinnamon enabled-applets "$NEW_APPLETS"
echo "Done! The Avathings applet should now appear on your panel."
