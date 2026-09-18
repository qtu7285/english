#!/usr/bin/env bash
# Script khởi chạy English Tutor Web App trên Termux
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BIN_PATH="$HOME/.local/bin/english-server"
PY_SERVER="$SCRIPT_DIR/api/server.py"

PORT="${1:-5000}"

echo "=================================================="
echo "  Khởi chạy English Tutor Web App"
echo "=================================================="

# Tự động biên dịch nếu chưa có binary hoặc code mới hơn
if [ ! -f "$BIN_PATH" ] || [ "$SCRIPT_DIR/api/main.go" -nt "$BIN_PATH" ]; then
    mkdir -p "$HOME/.local/bin"
    if command -v go >/dev/null 2>&1; then
        echo "[*] Tự động biên dịch Golang engine..."
        go build -o "$BIN_PATH" "$SCRIPT_DIR/api/main.go" "$SCRIPT_DIR/api/vault.go" "$SCRIPT_DIR/api/gemini.go"
        chmod +x "$BIN_PATH"
    fi
fi

if [ -f "$BIN_PATH" ] && [ -x "$BIN_PATH" ]; then
    echo "[*] Chạy động cơ Golang siêu nhẹ..."
    "$BIN_PATH" --vault "$REPO_DIR" --port "$PORT" --open
else
    echo "[*] Fallback: Chạy động cơ Python..."
    python3 "$PY_SERVER" --vault "$REPO_DIR" --port "$PORT" --open
fi
