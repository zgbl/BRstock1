#!/bin/bash
set -e

# 1. Handle AppData persistence
# OpenD saves session/device info in AppData.dat. We link it to our persistent data folder.
if [ ! -f /opend/data/AppData.dat ] && [ -f /opend/AppData.dat ]; then
    cp /opend/AppData.dat /opend/data/AppData.dat
fi
if [ -f /opend/data/AppData.dat ]; then
    ln -sf /opend/data/AppData.dat /opend/AppData.dat
fi

# 2. Configure OpenD.xml (only if account info is provided)
if [ -n "$MOOMOO_ACCOUNT" ] && [ -n "$MOOMOO_PWD" ]; then
    echo "⚙️  Configuring OpenD with environment variables..."
    TMP_FILE=$(mktemp)
    sed "s|<login_account>.*</login_account>|<login_account>${MOOMOO_ACCOUNT}</login_account>|g" /opend/OpenD.xml > "$TMP_FILE"
    sed -i "s|<login_pwd>.*</login_pwd>|<login_pwd>${MOOMOO_PWD}</login_pwd>|g" "$TMP_FILE"
    cat "$TMP_FILE" > /opend/OpenD.xml
    rm "$TMP_FILE"
    echo "✅ OpenD.xml updated."
else
    echo "⚠️  Warning: MOOMOO_ACCOUNT or MOOMOO_PWD not set. Using existing OpenD.xml"
fi

echo "🚀 Starting OpenD..."
exec "$@"
