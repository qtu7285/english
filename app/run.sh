#!/usr/bin/env bash
# Script khởi chạy English Tutor Web App trên Termux
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BIN_PATH="$HOME/.local/bin/english-server"

PORT=5000
USE_TLS=0
GEN_CERT=0
TLS_HOSTS="${ENGLISH_TLS_HOSTS:-zf3}"

# Nhận tham số theo thứ tự tự do: số cổng, tls, gen-cert
for arg in "$@"; do
    case "$arg" in
        tls|--tls)
            USE_TLS=1
            ;;
        gen-cert|--gen-cert)
            GEN_CERT=1
            ;;
        ''|*[!0-9]*)
            echo "[X] Tham số không hợp lệ: $arg (dùng: bash app/run.sh [PORT] [tls|gen-cert])" >&2
            exit 1
            ;;
        *)
            PORT="$arg"
            ;;
    esac
done

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

if [ "$GEN_CERT" -eq 1 ]; then
    echo "[*] Tạo chứng chỉ HTTPS cục bộ..."
    "$BIN_PATH" --gen-cert --tls-hosts "$TLS_HOSTS" --port "$PORT"
    exit 0
fi

echo "[*] Chạy động cơ Golang siêu nhẹ..."
if [ "$USE_TLS" -eq 1 ]; then
    "$BIN_PATH" --vault "$REPO_DIR" --port "$PORT" --tls --tls-hosts "$TLS_HOSTS" --open
else
    "$BIN_PATH" --vault "$REPO_DIR" --port "$PORT" --open
fi
