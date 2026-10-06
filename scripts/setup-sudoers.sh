#!/usr/bin/env bash
set -e

SUDOERS_FILE="/etc/sudoers.d/99-avathings"
CURRENT_USER="${SUDO_USER:-$USER}"

echo "Configuring passwordless sudo for changestate and avabatt for user '$CURRENT_USER'..."

cat <<EOF | sudo tee "$SUDOERS_FILE" > /dev/null
# Allow $CURRENT_USER to execute avathings hardware governor commands without password prompt
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/local/bin/changestate, /usr/local/bin/avabatt, /usr/bin/systemctl start changestate-auto, /usr/bin/systemctl stop changestate-auto, /usr/bin/systemctl restart changestate-auto
EOF

sudo chmod 0440 "$SUDOERS_FILE"
echo "Passwordless sudo rule configured in $SUDOERS_FILE"
