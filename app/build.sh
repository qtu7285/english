#!/usr/bin/env bash
# Script biên dịch Go server cho Termux
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"

echo "[*] Đang biên dịch Golang engine..."
go build -o "$BIN_DIR/english-server" "$SCRIPT_DIR/api/main.go" "$SCRIPT_DIR/api/vault.go" "$SCRIPT_DIR/api/gemini.go"
chmod +x "$BIN_DIR/english-server"
echo "[OK] Đã biên dịch thành công: $BIN_DIR/english-server"
