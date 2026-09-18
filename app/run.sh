#!/usr/bin/env bash
# Script khởi chạy English Tutor Web App trên Termux
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BIN_PATH="$HOME/.local/bin/english-server"

PORT="${1:-5000}"

echo "=================================================="
echo "  Khởi chạy English Tutor Web App"
echo "=================================================="

# Biên dịch lại khi chưa có binary hoặc bất kỳ file .go nào mới hơn binary
needs_build=0
if [ ! -x "$BIN_PATH" ]; then
    needs_build=1
else
    for src in "$SCRIPT_DIR"/api/*.go; do
        if [ "$src" -nt "$BIN_PATH" ]; then
            needs_build=1
            break
        fi
    done
fi

if [ "$needs_build" -eq 1 ]; then
    if ! command -v go >/dev/null 2>&1; then
        echo "[X] Chưa cài Go. Cài bằng: pkg install golang" >&2
        exit 1
    fi
    echo "[*] Tự động biên dịch Golang engine..."
    mkdir -p "$(dirname "$BIN_PATH")"
    go build -o "$BIN_PATH" "$SCRIPT_DIR"/api/*.go
    chmod +x "$BIN_PATH"
fi

echo "[*] Chạy động cơ Golang siêu nhẹ..."
"$BIN_PATH" --vault "$REPO_DIR" --port "$PORT" --open
