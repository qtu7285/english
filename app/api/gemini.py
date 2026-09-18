"""
Gemini API Client with Function Calling for Local Vault
Uses standard library urllib (no external dependencies required).
"""

import json
import urllib.request
import urllib.error
import urllib.parse
from typing import Dict, Any, List, Optional
try:
    from .vault import VaultManager
except ImportError:
    from vault import VaultManager

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

VAULT_TOOL_DECLARATIONS = [
    {
        "name": "list_vault_files",
        "description": "List files and directories in the local workspace or learning vault (such as WORDS/, notes, etc.).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "subpath": {
                    "type": "STRING",
                    "description": "Optional subdirectory relative to vault root, e.g. 'WORDS' or '' for root."
                }
            }
        }
    },
    {
        "name": "read_vault_file",
        "description": "Read the contents of a specific file in the vault (e.g. 'WORDS/urg.csv', 'AGENTS.md', markdown notes).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "path": {
                    "type": "STRING",
                    "description": "Relative path to the file inside the vault, e.g. 'WORDS/urge.csv'."
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_vault_file",
        "description": "Write or append content to a file in the vault (e.g. saving new vocabulary, notes, or quiz questions).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "path": {
                    "type": "STRING",
                    "description": "Relative path to the file to create or update."
                },
                "content": {
                    "type": "STRING",
                    "description": "Text content to write into the file."
                },
                "append": {
                    "type": "BOOLEAN",
                    "description": "True to append to existing content, False to overwrite."
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "search_vault",
        "description": "Search for keywords across files (markdown, CSV, text) in the vault.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Search term, word, or collocation to find in files."
                }
            },
            "required": ["query"]
        }
    }
]

def execute_vault_tool(vault: VaultManager, func_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if func_name == "list_vault_files":
        subpath = args.get("subpath", "")
        files = vault.list_files(subpath=subpath)
        return {"files": files[:50], "total": len(files)}

    elif func_name == "read_vault_file":
        path = args.get("path", "")
        return vault.read_file(path)

    elif func_name == "write_vault_file":
        path = args.get("path", "")
        content = args.get("content", "")
        append = args.get("append", False)
        return vault.write_file(path, content, append=append)

    elif func_name == "search_vault":
        query = args.get("query", "")
        matches = vault.search_vault(query)
        return {"matches": matches, "count": len(matches)}

    return {"error": f"Unknown tool: {func_name}"}

class GeminiClient:
    def __init__(self, api_key: Optional[str] = None, oauth_token: Optional[str] = None):
        self.api_key = api_key
        self.oauth_token = oauth_token

    def _make_request(self, model: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{GEMINI_API_BASE}/models/{model}:generateContent"
        headers = {
            "Content-Type": "application/json"
        }

        if self.oauth_token:
            headers["Authorization"] = f"Bearer {self.oauth_token}"
        elif self.api_key:
            url += f"?key={urllib.parse.quote(self.api_key)}"
        else:
            raise ValueError("No API Key or OAuth Access Token provided.")

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        import time
        max_retries = 3
        backoff_sec = 2.0

        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, timeout=45) as resp:
                    raw = resp.read().decode("utf-8")
                    return json.loads(raw)
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                try:
                    parsed_err = json.loads(err_body)
                    msg = parsed_err.get("error", {}).get("message", err_body)
                except Exception:
                    msg = err_body

                # Retry on 503 (high demand) or 429 (rate limit) or 500
                if e.code in (503, 429, 500) and attempt < max_retries - 1:
                    time.sleep(backoff_sec * (attempt + 1))
                    continue

                raise RuntimeError(f"Gemini API Error ({e.code}): {msg}")
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(backoff_sec)
                    continue
                raise RuntimeError(f"Network error calling Gemini: {str(e)}")

    def chat_with_vault(
        self,
        vault: VaultManager,
        contents: List[Dict[str, Any]],
        model: str = "gemini-3.6-flash",
        system_instruction: Optional[str] = None,
        enable_vault_tools: bool = True,
        max_tool_hops: int = 5
    ) -> Dict[str, Any]:
        """
        Executes a multi-turn chat with tool calling support on the local vault.
        """
        working_contents = list(contents)
        tool_logs = []

        payload: Dict[str, Any] = {
            "contents": working_contents,
            "generationConfig": {
                "temperature": 0.7,
                "topP": 0.95
            }
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        if enable_vault_tools:
            payload["tools"] = [{"functionDeclarations": VAULT_TOOL_DECLARATIONS}]

        for _ in range(max_tool_hops):
            response = self._make_request(model, payload)
            candidates = response.get("candidates", [])
            if not candidates:
                return {
                    "text": "Không nhận được phản hồi từ AI.",
                    "tool_logs": tool_logs
                }

            first_candidate = candidates[0]
            content = first_candidate.get("content", {})
            parts = content.get("parts", [])

            # Check if AI requested any function calls
            function_calls = [p["functionCall"] for p in parts if "functionCall" in p]

            if not function_calls:
                # Text answer ready
                text_parts = [p.get("text", "") for p in parts if "text" in p]
                return {
                    "text": "".join(text_parts),
                    "tool_logs": tool_logs
                }

            # Append model's tool request to contents
            working_contents.append(content)

            # Execute tool calls
            tool_response_parts = []
            for fc in function_calls:
                f_name = fc.get("name")
                f_args = fc.get("args", {})
                tool_result = execute_vault_tool(vault, f_name, f_args)
                tool_logs.append({
                    "tool": f_name,
                    "args": f_args,
                    "result": tool_result
                })
                tool_response_parts.append({
                    "functionResponse": {
                        "name": f_name,
                        "response": tool_result
                    }
                })

            # Append function response as user/function turn
            working_contents.append({
                "role": "user",
                "parts": tool_response_parts
            })
            payload["contents"] = working_contents

        # Fallback if too many hops
        return {
            "text": "Đã hoàn thành các bước truy xuất file trong vault.",
            "tool_logs": tool_logs
        }
