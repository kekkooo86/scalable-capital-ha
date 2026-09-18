#!/usr/bin/env bash
set -e

export HOME=/data
export XDG_CONFIG_HOME=/data/.config
CFG_DIR="$XDG_CONFIG_HOME/scalable-cli"
mkdir -p "$CFG_DIR"
chmod 700 "$CFG_DIR"

if [ ! -f "$CFG_DIR/config.toml" ]; then
    printf '[auth]\nsession_backend = "file"\nsigning_key_backend = "file"\n' > "$CFG_DIR/config.toml"
    chmod 600 "$CFG_DIR/config.toml"
fi

exec python3 -u /app/server.py
