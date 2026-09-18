"""
Vault Manager for English Learning App
Provides safe local file access to Obsidian/local markdown/CSV vaults.
"""

import os
import glob
from pathlib import Path
from typing import List, Dict, Any, Optional

DEFAULT_VAULT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

class VaultManager:
    def __init__(self, root_path: Optional[str] = None):
        self.root_path = Path(root_path or DEFAULT_VAULT_ROOT).resolve()

    def set_root(self, path: str) -> bool:
        resolved = Path(path).resolve()
        if resolved.exists() and resolved.is_dir():
            self.root_path = resolved
            return True
        return False

    def _resolve_safe_path(self, rel_path: str) -> Path:
        clean = rel_path.strip().lstrip("/\\")
        target = (self.root_path / clean).resolve()
        try:
            target.relative_to(self.root_path)
        except ValueError:
            raise PermissionError(f"Access denied: path '{rel_path}' is outside vault root.")
        return target

    def list_files(self, subpath: str = "", max_depth: int = 3) -> List[Dict[str, Any]]:
        target_dir = self._resolve_safe_path(subpath)
        if not target_dir.exists() or not target_dir.is_dir():
            return []

        results = []
        base_depth = len(target_dir.parts)

        for root, dirs, files in os.walk(target_dir):
            current_depth = len(Path(root).parts) - base_depth
            if current_depth >= max_depth:
                dirs.clear()
                continue

            # Skip hidden folders like .git, .agents, .gemini
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]

            for f in sorted(files):
                if f.startswith("."):
                    continue
                full_path = Path(root) / f
                try:
                    rel_to_vault = str(full_path.relative_to(self.root_path))
                    stat = full_path.stat()
                    ext = full_path.suffix.lower()
                    results.append({
                        "name": f,
                        "path": rel_to_vault,
                        "size": stat.st_size,
                        "modified": int(stat.st_mtime),
                        "type": ext.lstrip(".") if ext else "file",
                        "is_markdown": ext == ".md",
                        "is_csv": ext == ".csv"
                    })
                except Exception:
                    continue

        return results

    def read_file(self, rel_path: str, max_bytes: int = 100000) -> Dict[str, Any]:
        target = self._resolve_safe_path(rel_path)
        if not target.exists():
            return {"error": f"File '{rel_path}' does not exist."}
        if not target.is_file():
            return {"error": f"'{rel_path}' is a directory, not a file."}

        try:
            content = target.read_text(encoding="utf-8", errors="replace")
            if len(content) > max_bytes:
                content = content[:max_bytes] + f"\n\n... [Content truncated, total {len(content)} characters] ..."
            return {
                "path": rel_path,
                "name": target.name,
                "content": content,
                "size": target.stat().st_size
            }
        except Exception as e:
            return {"error": f"Failed to read file: {str(e)}"}

    def write_file(self, rel_path: str, content: str, append: bool = False) -> Dict[str, Any]:
        target = self._resolve_safe_path(rel_path)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            mode = "a" if append else "w"
            with open(target, mode, encoding="utf-8") as f:
                f.write(content)
            return {
                "success": True,
                "path": rel_path,
                "bytes_written": len(content.encode("utf-8")),
                "mode": "append" if append else "overwrite"
            }
        except Exception as e:
            return {"error": f"Failed to write file: {str(e)}"}

    def search_vault(self, query: str, max_results: int = 15) -> List[Dict[str, Any]]:
        query_lower = query.lower()
        results = []

        allowed_exts = {".md", ".csv", ".txt", ".json"}
        for root, dirs, files in os.walk(self.root_path):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
            for f in files:
                ext = Path(f).suffix.lower()
                if ext not in allowed_exts:
                    continue
                file_path = Path(root) / f
                try:
                    rel_path = str(file_path.relative_to(self.root_path))
                    # Check filename match
                    if query_lower in f.lower():
                        results.append({
                            "path": rel_path,
                            "match_type": "filename",
                            "snippet": f"Filename matches '{query}'"
                        })
                        if len(results) >= max_results:
                            return results
                        continue

                    # Check text content match
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as stream:
                        for line_idx, line in enumerate(stream):
                            if query_lower in line.lower():
                                results.append({
                                    "path": rel_path,
                                    "match_type": "content",
                                    "line": line_idx + 1,
                                    "snippet": line.strip()[:200]
                                })
                                if len(results) >= max_results:
                                    return results
                                break
                except Exception:
                    continue

        return results
