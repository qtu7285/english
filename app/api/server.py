"""
Local Web Server for English Tutor & Vault Explorer
Built using Python Standard Library (ThreadingHTTPServer, urllib).
"""

import os
import sys
import json
import argparse
import mimetypes
import subprocess
from http import HTTPStatus
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path

# Add current dir to import path
sys.path.insert(0, os.path.dirname(__file__))

from vault import VaultManager, DEFAULT_VAULT_ROOT
from gemini import GeminiClient

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

# Default pedagogical tutor system prompt (aligned with AGENTS.md)
DEFAULT_SYSTEM_PROMPT = """You are an English tutor. Explain in Vietnamese, briefly, naturally, and clearly.
Use ASCII bracketed status labels: [OK], [~], [X], [NEXT], [RETRY], [SAVE], [CONFIRM], [EN], and [VI]. Do not use emojis.

Rules:
1. Explaining a word/phrase (e.g. '.urge', 'inspire'):
   - Provide meaning in Vietnamese
   - Part of speech
   - Common usage/collocations
   - A short natural English example with Vietnamese meaning
   - End with: [NEXT] Nhập số câu để luyện (ví dụ 5), hoặc .từ_mới để chuyển từ.

2. Explaining a sentence:
   - Natural Vietnamese meaning
   - Important grammar/structure
   - Correction if needed

3. Interactive Practice Round (CRITICAL - ONE QUESTION AT A TIME):
   When the learner enters a positive integer N (such as '3' or '5') after studying a word:
   - You MUST initiate an interactive practice round of N questions.
   - VERY IMPORTANT: Present ONLY ONE question at a time! NEVER output all questions at once.
   - For the initial turn, present ONLY "Câu 1/N":
     * Include difficulty label: [D1] (cơ bản), [D2] (trung bình), or [D3] (khó).
     * Provide a sentence with blank(s) `___` and a clear Vietnamese translation hint.
     * Provide 4 options (A, B, C, D) testing the target word and its collocations, or ask to fill in the blank.
     * Stop and wait for the learner to answer Câu 1/N.

4. Grading and Advancing Questions (ONE BY ONE):
   When the learner answers a question (e.g. typing "A", "urged", or the word):
   - Grade the answer immediately:
     * If correct: output [OK] with a brief explanation of why it fits and common collocation.
     * If incorrect: output [X], explain the mistake, and give the correct sentence.
   - If there are remaining questions in the round (e.g. Question K < N):
     * Immediately present the next single question: "Câu (K+1)/N [D2]" in the same response and wait for the answer.
     * Do NOT present more than 1 question at a time.
   - If it was the last question (Câu N/N):
     * Announce round completion: [OK] Hoàn thành N/N câu!
     * End with: [NEXT] Nhập số câu để luyện tiếp (ví dụ 5), hoặc .từ_mới để chuyển từ.

5. Commands:
   - '.s': Confirm learning progress is saved.
   - '.g': Git sync status.
   - '.help': Show available commands.

You have access to tools to read, search, list, and write files in the user's learning vault and vocabulary data. Use them when requested."""

class AppServerHandler(BaseHTTPRequestHandler):
    vault: VaultManager = VaultManager()

    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def _read_json_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length)
        return json.loads(body.decode("utf-8"))

    def _send_json(self, data, status=200):
        self._set_headers(status, "application/json; charset=utf-8")
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _send_error(self, message, status=400):
        self._send_json({"error": message}, status=status)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # API Endpoints
        if path == "/api/status":
            self._send_json({
                "status": "ok",
                "vault_root": str(self.vault.root_path),
                "web_dir": str(WEB_DIR)
            })
            return

        if path == "/api/vault/list":
            subpath = query.get("subpath", [""])[0]
            files = self.vault.list_files(subpath=subpath)
            self._send_json({"files": files, "vault_root": str(self.vault.root_path)})
            return

        if path == "/api/vault/read":
            file_path = query.get("path", [""])[0]
            if not file_path:
                self._send_error("Parameter 'path' is required.")
                return
            result = self.vault.read_file(file_path)
            if "error" in result:
                self._send_error(result["error"], 404)
            else:
                self._send_json(result)
            return

        if path == "/api/vault/search":
            q = query.get("q", [""])[0]
            if not q:
                self._send_error("Parameter 'q' is required.")
                return
            results = self.vault.search_vault(q)
            self._send_json({"matches": results, "query": q})
            return

        # Serve static web files
        self._serve_static(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/chat":
            try:
                body = self._read_json_body()
                message = body.get("message", "").strip()
                history = body.get("history", [])
                api_key = body.get("apiKey")
                oauth_token = body.get("oauthToken")
                model = str(body.get("model", "gemini-3.6-flash")).strip()
                if not model or model == "gemini-2.5-flash":
                    model = "gemini-3.6-flash"
                system_prompt = body.get("systemInstruction", DEFAULT_SYSTEM_PROMPT)
                enable_tools = body.get("enableVaultTools", True)

                if not message:
                    self._send_error("Message cannot be empty.")
                    return

                if not api_key and not oauth_token:
                    # Return friendly offline mock reply if no auth yet
                    self._send_json({
                        "text": "[~] Bạn chưa cấu hình Google API Key hoặc OAuth Token.\n\nVui lòng nhấn biểu tượng Cài đặt (⚙) ở góc trên để nhập API Key (lấy miễn phí tại https://aistudio.google.com/) hoặc đăng nhập OAuth.\n\nTrong lúc chờ cấu hình, bạn vẫn có thể dùng tab 'Vault Explorer' để đọc/ghi file từ vựng trực tiếp!",
                        "tool_logs": []
                    })
                    return

                # Build conversation contents with strictly alternating turns
                contents = []
                last_role = None
                for turn in history:
                    text_content = turn.get("text", "").strip()
                    if not text_content:
                        continue
                    role = "user" if turn.get("role") == "user" else "model"
                    if role == last_role:
                        contents[-1]["parts"].append({"text": text_content})
                    else:
                        contents.append({
                            "role": role,
                            "parts": [{"text": text_content}]
                        })
                        last_role = role

                # Add current user message
                if contents and contents[-1]["role"] == "user":
                    contents[-1]["parts"].append({"text": message})
                else:
                    contents.append({
                        "role": "user",
                        "parts": [{"text": message}]
                    })

                client = GeminiClient(api_key=api_key, oauth_token=oauth_token)
                result = client.chat_with_vault(
                    vault=self.vault,
                    contents=contents,
                    model=model,
                    system_instruction=system_prompt,
                    enable_vault_tools=enable_tools
                )
                self._send_json(result)

            except Exception as e:
                self._send_error(str(e), 500)
            return

        if path == "/api/vault/write":
            try:
                body = self._read_json_body()
                file_path = body.get("path", "")
                content = body.get("content", "")
                append = body.get("append", False)
                if not file_path:
                    self._send_error("Parameter 'path' is required.")
                    return
                result = self.vault.write_file(file_path, content, append=append)
                if "error" in result:
                    self._send_error(result["error"], 500)
                else:
                    self._send_json(result)
            except Exception as e:
                self._send_error(str(e), 500)
            return

        if path == "/api/oauth/exchange":
            try:
                # Exchange auth code for tokens via Google OAuth token endpoint
                import urllib.request, urllib.parse
                body = self._read_json_body()
                code = body.get("code")
                client_id = body.get("clientId")
                client_secret = body.get("clientSecret")
                redirect_uri = body.get("redirectUri")

                if not all([code, client_id, client_secret, redirect_uri]):
                    self._send_error("Missing required OAuth parameters.")
                    return

                token_url = "https://oauth2.googleapis.com/token"
                post_data = urllib.parse.urlencode({
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code"
                }).encode("utf-8")

                req = urllib.request.Request(token_url, data=post_data, method="POST")
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    self._send_json(data)
            except Exception as e:
                self._send_error(f"OAuth exchange failed: {str(e)}", 400)
            return

        self._send_error("Not Found", 404)

    def _serve_static(self, req_path):
        if req_path in ("", "/"):
            req_path = "/index.html"

        safe_path = req_path.lstrip("/\\")
        file_path = (WEB_DIR / safe_path).resolve()

        try:
            file_path.relative_to(WEB_DIR)
        except ValueError:
            self._send_error("Forbidden", 403)
            return

        if not file_path.exists() or not file_path.is_file():
            self._send_error(f"File not found: {req_path}", 404)
            return

        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = "application/octet-stream"

        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self._set_headers(200, mime_type)
            self.wfile.write(content)
        except Exception as e:
            self._send_error(str(e), 500)

def get_tailscale_info():
    ts_ip = None
    try:
        res = subprocess.check_output(["ifconfig"], stderr=subprocess.DEVNULL).decode()
        import re
        matches = re.findall(r"inet (100\.\d{1,3}\.\d{1,3}\.\d{1,3})", res)
        if matches:
            ts_ip = matches[0]
    except Exception:
        pass
    return ts_ip

def run(port=5000, host="0.0.0.0", vault_path=None, auto_open=False):
    if vault_path:
        AppServerHandler.vault.set_root(vault_path)

    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, AppServerHandler)

    ts_ip = get_tailscale_info()

    print(f"\n=======================================================")
    print(f"  English Tutor Web App đang chạy")
    print(f"=======================================================")
    print(f"[OK] Cục bộ (trên máy này):     http://localhost:{port}")
    print(f"[OK] Qua Tailscale (tên máy):   http://zf3:{port}")
    if ts_ip:
        print(f"[OK] Qua Tailscale (địa chỉ IP): http://{ts_ip}:{port}")
    print(f"[*] Thư mục Vault: {AppServerHandler.vault.root_path}")
    print(f"[*] Bấm Ctrl+C để dừng server.\n")

    if auto_open:
        try:
            subprocess.Popen(["termux-open-url", f"http://localhost:{port}"])
            print("[OK] Đã mở trình duyệt Termux.")
        except Exception:
            pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[OK] Đã dừng server.")
        httpd.server_close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="English Tutor Web & Vault App")
    parser.add_argument("--port", type=int, default=5000, help="Port to run on (default 5000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address (default 0.0.0.0 for LAN & Tailscale)")
    parser.add_argument("--vault", type=str, default=None, help="Custom vault root directory")
    parser.add_argument("--open", action="store_true", help="Automatically open in browser (termux-open-url)")

    args = parser.parse_args()
    run(port=args.port, host=args.host, vault_path=args.vault, auto_open=args.open)
