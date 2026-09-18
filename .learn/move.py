#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import time
import json
import getpass

def get_subfolders(directory, show_hidden=False):
    """Returns a sorted list of subfolders in the directory."""
    try:
        items = os.listdir(directory)
        subfolders = []
        for item in items:
            if not show_hidden:
                if item.startswith('.'):
                    continue
            else:
                if item in [".git", "__pycache__"]:
                    continue
            path = os.path.join(directory, item)
            if os.path.isdir(path):
                subfolders.append(item)
        return sorted(subfolders)
    except Exception as e:
        print(f"\033[91m⚠️ Lỗi khi đọc thư mục: {e}\033[0m")
        return []

def count_files(directory, show_hidden=False):
    """Counts files in the directory."""
    try:
        count = 0
        for item in os.listdir(directory):
            if not show_hidden:
                if item.startswith('.'):
                    continue
            else:
                if item in [".git", "__pycache__"]:
                    continue
            if os.path.isfile(os.path.join(directory, item)):
                count += 1
        return count
    except Exception:
        return 0

def get_files(directory, show_hidden=False):
    """Returns a sorted list of files in the directory."""
    try:
        items = os.listdir(directory)
        files = []
        for item in items:
            if not show_hidden:
                if item.startswith('.'):
                    continue
            else:
                if item in [".git", "__pycache__"]:
                    continue
            if os.path.isfile(os.path.join(directory, item)):
                files.append(item)
        return sorted(files)
    except Exception:
        return []

def list_files_and_folders(directory, show_hidden=False):
    """Lists files and subfolders in directory with extensions, icons and sizes."""
    GREY = "\033[90m"
    RESET = "\033[0m"
    try:
        items = sorted(os.listdir(directory))
    except Exception as e:
        print(f"\033[91m⚠️ Lỗi khi đọc thư mục: {e}\033[0m")
        return

    if not show_hidden:
        items_to_show = [item for item in items if not item.startswith('.')]
    else:
        items_to_show = [item for item in items if item not in [".git", "__pycache__"]]
    folder_name = os.path.basename(directory) or directory

    print(f"\n\033[95m📄 [DANH SÁCH TỆP & THƯ MỤC: {folder_name}]\033[0m")

    if not items_to_show:
        print("  (Thư mục trống)")
    else:
        dirs = []
        files = []
        for item in items_to_show:
            full_path = os.path.join(directory, item)
            if os.path.isdir(full_path):
                dirs.append(item)
            else:
                files.append(item)

        for d in dirs:
            print(f"  \033[96m📁 {d}/\033[0m")

        for f in files:
            full_path = os.path.join(directory, f)
            try:
                size_bytes = os.path.getsize(full_path)
                if size_bytes < 1024:
                    size_str = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    size_str = f"{size_bytes / 1024:.1f} KB"
                else:
                    size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
            except Exception:
                size_str = ""

            ext = os.path.splitext(f)[1].lower()
            if ext == '.md':
                icon = "📝"
            elif ext == '.json':
                icon = "📊"
            elif ext == '.py':
                icon = "🐍"
            elif ext in ['.txt', '.csv', '.log']:
                icon = "📄"
            elif ext in ['.mp3', '.m4a', '.wav']:
                icon = "🔊"
            elif ext in ['.mp4', '.mkv']:
                icon = "🎬"
            elif ext in ['.png', '.jpg', '.jpeg']:
                icon = "🖼️"
            else:
                icon = "📄"

            size_fmt = f" \033[90m({size_str})\033[0m" if size_str else ""
            print(f"  {icon} {f}{size_fmt}")

    print("\033[90m--------------------------------------------------\033[0m")
    try:
        input(f"{GREY}Nhấn Enter để tiếp tục...{RESET}")
    except (KeyboardInterrupt, EOFError):
        pass

def to_tilde_path(abs_path, workspace_root=None):
    if abs_path.startswith("~"):
        return abs_path
    path = os.path.abspath(abs_path)

    try:
        real_path = os.path.realpath(path)
        real_home = os.path.realpath(os.path.expanduser("~"))
        if real_path == real_home:
            return "~"
        elif real_path.startswith(real_home + "/"):
            return "~" + real_path[len(real_home):]
    except Exception:
        pass

    for prefix in ["/storage/emulated/0", "/sdcard", "/mnt/sdcard"]:
        try:
            real_prefix = os.path.realpath(prefix)
            if real_path == real_prefix:
                return "~/storage/shared"
            elif real_path.startswith(real_prefix + "/"):
                return "~/storage/shared" + real_path[len(real_prefix):]
        except Exception:
            pass

    # Fallback to standard path if no match
    home = os.path.expanduser("~")
    if path == home:
        return "~"
    elif path.startswith(home + "/"):
        return "~" + path[len(home):]
    return path

def from_tilde_path(tilde_path, workspace_root=None):
    if (tilde_path == "~/english" or tilde_path.startswith("~/english/")):
        suffix = tilde_path[len("~/english"):].strip("/")
        return os.path.normpath(os.path.join(workspace_root, suffix))
    elif (tilde_path == "~/buddha" or tilde_path.startswith("~/buddha/")):
        suffix = tilde_path[len("~/buddha"):].strip("/")
        return os.path.normpath(os.path.join(workspace_root, "buddha", suffix))

    if tilde_path.startswith("~"):
        home = os.path.expanduser("~")
        return os.path.normpath(home + tilde_path[1:])
    return os.path.abspath(tilde_path)

def load_working_dirs(file_path, workspace_root):
    """Loads working directories (stored as tilde paths) from json file, pruning non-existent ones."""
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    normalized = []
                    changed = False
                    for p in data:
                        abs_p = from_tilde_path(p, workspace_root)
                        if os.path.isdir(abs_p):
                            new_tilde = to_tilde_path(abs_p, workspace_root)
                            normalized.append(new_tilde)
                            if new_tilde != p:
                                changed = True
                    if changed:
                        save_working_dirs(file_path, normalized)
                    return normalized
        except Exception:
            pass
    return [to_tilde_path(workspace_root, workspace_root)]

def save_working_dirs(file_path, dirs):
    """Saves the working directories list (relative paths) to the json file."""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(dirs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"\033[91m⚠️ Lỗi khi lưu danh sách working dirs: {e}\033[0m")

def load_path_aliases(file_path, workspace_root=None):
    """Loads path aliases dict from json file, normalizing keys."""
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    normalized = {}
                    changed = False
                    for k, v in data.items():
                        abs_k = from_tilde_path(k, workspace_root)
                        new_k = to_tilde_path(abs_k, workspace_root)
                        normalized[new_k] = v
                        if new_k != k:
                            changed = True
                    if changed:
                        save_path_aliases(file_path, normalized)
                    return normalized
        except Exception:
            pass
    return {to_tilde_path(workspace_root, workspace_root): "@en"} if workspace_root else {}

def save_path_aliases(file_path, aliases):
    """Saves path aliases dict to json file."""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(aliases, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"\033[91m⚠️ Lỗi khi lưu danh sách alias: {e}\033[0m")

def apply_aliases(tilde_path, aliases):
    """Shortens a path using aliases prefix matching. Returns (shortened_path, alias_used_name)."""
    # Sort keys by length descending to match the longest/deepest alias prefix first
    sorted_keys = sorted(aliases.keys(), key=len, reverse=True)
    for k in sorted_keys:
        alias_name = aliases[k]
        if tilde_path == k:
            return alias_name, alias_name
        elif tilde_path.startswith(k + "/"):
            suffix = tilde_path[len(k):]
            return alias_name + suffix, alias_name
    return tilde_path, None

def find_folder_by_name(workspace_root, target_name):
    """Recursively search for a folder with target_name in workspace_root (skipping hidden folders)."""
    matches = []
    for root, dirs, files in os.walk(workspace_root):
        # Filter hidden folders in-place to avoid walking into them
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for d in dirs:
            if d == target_name:
                matches.append(os.path.join(root, d))
    return matches

def check_quiz_exists(directory):
    # Auto-migrate legacy files inside directory
    if os.path.exists(directory):
        items = [directory] + [os.path.join(directory, d) for d in os.listdir(directory) if os.path.isdir(os.path.join(directory, d))]
        migrations = [
            ("questions.json", "preq.json"),
            ("preq.json", "preq.json"),
            ("voca.json", "preg.json"),
            ("preg.json", "preg.json"),
            ("words.md", "bold.md"),
            ("bold.md", "bold.md"),
            ("write.md", "scwr.md"),
            ("scwr.md", "scwr.md"),
            ("speak.md", "scsp.md"),
            ("scsp.md", "scsp.md"),
            ("sess.json", "sess-quiz.json"),
        ]
        for item in items:
            if os.path.exists(item):
                for old_name, new_name in migrations:
                    old_f = os.path.join(item, old_name)
                    new_f = os.path.join(item, new_name)
                    if os.path.exists(old_f) and not os.path.exists(new_f):
                        try:
                            os.rename(old_f, new_f)
                        except Exception:
                            pass

    """Checks if preq.json exists anywhere (shared, inside any user folder, or inside level folders) and at least one non-hidden md file exists."""
    json_exists = os.path.exists(os.path.join(directory, "preq.json"))

    # Check if preq.json exists in any user folder (starting with '.' or '👤')
    if not json_exists:
        try:
            for item in os.listdir(directory):
                if (item.startswith(".") or item.startswith("👤")) and item not in {".git", ".learning", ".learn", ".obsidian", ".agents"}:
                    item_path = os.path.join(directory, item)
                    if os.path.isdir(item_path):
                        # Try root of user folder
                        if os.path.exists(os.path.join(item_path, "preq.json")):
                            json_exists = True
                            break
                        # Try level subfolders
                        for idx in range(1, 6):
                            if os.path.exists(os.path.join(item_path, f"lv{idx}", "preq.json")):
                                json_exists = True
                                break
                        if json_exists:
                            break
        except Exception:
            pass

    # Helper to check if any non-hidden .md file exists in a directory
    def has_md_file(dir_path):
        if not os.path.isdir(dir_path):
            return False
        try:
            return any(f.endswith(".md") and not f.startswith(".") and f not in {"scwr.md", "scsp.md"} for f in os.listdir(dir_path))
        except Exception:
            return False

    vocab_exists = has_md_file(directory)
    if not vocab_exists:
        # Also check in user folders (including level folders)
        try:
            for item in os.listdir(directory):
                if (item.startswith(".") or item.startswith("👤")) and item not in {".git", ".learning", ".learn", ".obsidian", ".agents"}:
                    item_path = os.path.join(directory, item)
                    if os.path.isdir(item_path):
                        if has_md_file(item_path):
                            vocab_exists = True
                            break
                        # Check level subfolders
                        for idx in range(1, 6):
                            if has_md_file(os.path.join(item_path, f"lv{idx}")):
                                vocab_exists = True
                                break
                        if vocab_exists:
                            break
        except Exception:
            pass
    return json_exists and vocab_exists

def format_header_path(current_dir):
    path = os.path.abspath(current_dir)

    # Replace home directory with ~
    home = os.path.expanduser("~")
    if path == home:
        path_with_tilde = "~"
    elif path.startswith(home + "/"):
        path_with_tilde = "~" + path[len(home):]
    else:
        path_with_tilde = path

    base_prefix = ""
    middle_path = ""
    remain_path = ""

    if path_with_tilde.startswith("~"):
        base_prefix = "~"
        rest = path_with_tilde[1:].strip("/")
    elif path_with_tilde.startswith("/storage/emulated/0"):
        base_prefix = "/storage/emulated/0"
        rest = path_with_tilde[len("/storage/emulated/0"):].strip("/")
    elif path_with_tilde.startswith("/sdcard"):
        base_prefix = "/sdcard"
        rest = path_with_tilde[len("/sdcard"):].strip("/")
    else:
        # Fallback if not matching standard patterns
        if "LANGUAGE/english" in path_with_tilde:
            idx = path_with_tilde.find("LANGUAGE/english")
            base_prefix = path_with_tilde[:idx].rstrip("/")
            rest = path_with_tilde[idx:].strip("/")
        else:
            base_prefix = path_with_tilde
            rest = ""

    if base_prefix == "~":
        target_pattern = "english"
    else:
        target_pattern = "LANGUAGE/english"

    if rest:
        if rest.startswith(target_pattern):
            middle_path = target_pattern
            remain_path = rest[len(target_pattern):].strip("/")
        elif "english" in rest:
            idx = rest.find("english") + len("english")
            middle_path = rest[:idx].strip("/")
            remain_path = rest[idx:].strip("/")
        else:
            middle_path = rest
            remain_path = ""

    return [base_prefix, middle_path, remain_path]

def git_sync(current_dir):
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    GREY = "\033[90m"
    RESET = "\033[0m"

    try:
        git_root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=current_dir,
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
    except Exception:
        print(f"\n{RED}❌ Lỗi: Thư mục hiện tại (hoặc thư mục cha) không phải là một Git Repository!{RESET}")
        time.sleep(2)
        return

    print(f"\n{YELLOW}🚀 Khởi động Git Sync tại:{RESET} {git_root}")
    print(f"{GREY}--------------------------------------------------{RESET}")
    print(f"📄 Trạng thái thay đổi:")
    subprocess.run(["git", "status", "-s"], cwd=git_root)
    print(f"{GREY}--------------------------------------------------{RESET}")

    status_output = subprocess.check_output(["git", "status", "--porcelain"], cwd=git_root, text=True).strip()
    if not status_output:
        print(f"\n{GREEN}✨ Không có thay đổi nào cần đồng bộ! (Working directory clean){RESET}")
        try:
            input(f"\n{GREY}Nhấn Enter để quay lại...{RESET}")
        except (KeyboardInterrupt, EOFError):
            pass
        return

    try:
        commit_msg = input(f"Nhập tin nhắn commit (Enter để dùng: 'sync: <ngày giờ>'): ").strip()
    except (KeyboardInterrupt, EOFError):
        print(f"\n{RED}❌ Đã hủy Git Sync.{RESET}")
        time.sleep(1.5)
        return

    if not commit_msg:
        from datetime import datetime
        commit_msg = f"sync: {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    print(f"\n📤 1. Đang thêm các thay đổi (git add -A)...")
    subprocess.run(["git", "add", "-A"], cwd=git_root)

    print(f"💾 2. Đang tạo commit...")
    subprocess.run(["git", "commit", "-m", commit_msg], cwd=git_root)

    print(f"🚀 3. Đang đẩy lên server (git push)...")
    push_result = subprocess.run(["git", "push"], cwd=git_root)
    if push_result.returncode == 0:
        print(f"\n{GREEN}✅ Git Sync hoàn tất thành công!{RESET}")
    else:
        print(f"\n{RED}❌ Git Sync gặp lỗi khi push lên server.{RESET}")

    try:
        input(f"\n{GREY}Nhấn Enter để quay lại...{RESET}")
    except (KeyboardInterrupt, EOFError):
        pass

def main():
    GREY = "\033[90m"
    RESET = "\033[0m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    WHITE = "\033[97m"

    # Workspace root is the parent directory of .learn (where move.py resides)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_root = os.path.dirname(script_dir)

    # Locate files next to this script
    quiz_path = os.path.join(script_dir, "quiz.py")
    prep_path = os.path.join(script_dir, "prep.py")
    tran_path = os.path.join(script_dir, "tran.py")
    working_dirs_file = os.path.join(script_dir, "working_dirs.json")

    if not os.path.exists(quiz_path):
        print(f"\033[91m⚠️ Không tìm thấy quiz.py tại {quiz_path}!\033[0m")
        sys.exit(1)

    if not os.path.exists(prep_path):
        print(f"\033[91m⚠️ Không tìm thấy prep.py tại {prep_path}!\033[0m")
        sys.exit(1)

    if not os.path.exists(tran_path):
        print(f"\033[91m⚠️ Không tìm thấy tran.py tại {tran_path}!\033[0m")
        sys.exit(1)

    # Prioritize starting with Bookmarks view if any bookmarks exist
    working_rel_paths = load_working_dirs(working_dirs_file, workspace_root)
    show_working_only = bool(working_rel_paths)
    show_help = False
    show_hidden = False
    show_files = False
    show_dirs = True

    aliases_file = os.path.join(script_dir, "path_aliases.json")
    first_run = True

    while True:
        # Clear screen for clean UI
        os.system('clear' if os.name != 'nt' else 'cls')

        current_dir = os.getcwd()

        # Load working dirs as stored in json (tilde paths)
        working_rel_paths = load_working_dirs(working_dirs_file, workspace_root)

        # Calculate tilde path for current directory
        current_tilde_path = to_tilde_path(current_dir, workspace_root)
        is_bookmarked = current_tilde_path in working_rel_paths

        # Pre-calculate used aliases on this screen
        aliases = load_path_aliases(aliases_file, workspace_root)
        used_aliases_on_screen = set()

        # 1. Check current directory alias usage
        shortened_current_tilde, current_alias_used = apply_aliases(current_tilde_path, aliases)
        if current_alias_used:
            used_aliases_on_screen.add(current_alias_used)

        # 2. Check bookmarks list alias usage
        if show_working_only:
            for p in working_rel_paths:
                _, alias_used = apply_aliases(p, aliases)
                if alias_used:
                    used_aliases_on_screen.add(alias_used)
        # 3. Check subfolders list alias usage
        else:
            subfolders = get_subfolders(current_dir, show_hidden)
            for folder in subfolders:
                sub_abs = os.path.join(current_dir, folder)
                sub_tilde = to_tilde_path(sub_abs, workspace_root)
                _, alias_used = apply_aliases(sub_tilde, aliases)
                if alias_used:
                    used_aliases_on_screen.add(alias_used)

        # Check if preq.json/vocabulary files exist for the current directory
        has_quiz = check_quiz_exists(current_dir)

        # 1. Display aliases (always show all, but color inactive ones in 50% gray) on top
        if aliases:
            print("\n\033[93m🏷️  [DANH SÁCH ALIAS]\033[0m")
            for path, alias in sorted(aliases.items(), key=lambda x: x[1]):
                is_active = alias in used_aliases_on_screen
                if is_active:
                    print(f"  \033[92m{alias}\033[0m = {path}")
                else:
                    print(f"  \033[90m{alias} = {path}\033[0m")
            print("\033[90m--------------------------------------------------\033[0m")

        # 2. Display working dirs (if show_working_only is True) next
        if show_working_only:
            lead_nl = "" if aliases else "\n"
            print(f"{lead_nl}\033[95m📂 [DANH SÁCH WORKING DIRS (BOOKMARKS)]\033[0m")

            resolved_working_dirs = [] # list of tuples: (stored_rel_path, abs_path, is_valid)
            for path in working_rel_paths:
                # Resolve tilde path to absolute
                abs_path = from_tilde_path(path, workspace_root)
                is_valid = os.path.isdir(abs_path)
                resolved_working_dirs.append((path, abs_path, is_valid))

            if resolved_working_dirs:
                for idx, (rel, abs_p, valid) in enumerate(resolved_working_dirs, 1):
                    # Check if it has preq.json (only if path exists)
                    quiz_indicator = ""
                    if valid:
                        sub_quiz = check_quiz_exists(abs_p)
                        quiz_indicator = " 📝" if sub_quiz else ""
                        status_str = ""
                    else:
                        status_str = " \033[91m⚠️ [Không tìm thấy]\033[0m"

                    # Highlight if it is the current directory
                    prefix = "👉 " if abs_p == current_dir else "   "
                    shortened_rel, _ = apply_aliases(rel, aliases)
                    print(f"{prefix}[{idx}] {shortened_rel}{quiz_indicator}{status_str}")
            else:
                print("  (Chưa có thư mục working dir nào được đánh dấu)")
            print("\033[90m--------------------------------------------------\033[0m")

        # Display header (current directory path info - show actual current directory)
        current_tilde = to_tilde_path(current_dir, workspace_root)
        shortened_current, _ = apply_aliases(current_tilde, aliases)

        file_count = count_files(current_dir, show_hidden)
        file_count_str = f" ({file_count} tệp)"

        lead_nl = "" if (aliases or show_working_only) else "\n"
        print(f"{lead_nl}\033[97m📍 Thư mục hiện tại: {shortened_current}{file_count_str}\033[0m")

        # 4. Display subfolders (if show_working_only is False)
        if not show_working_only:
            # Display navigation options
            curr_folder = os.path.basename(current_dir) or "/"
            meta_parts = []
            if is_bookmarked:
                meta_parts.append("⭐")
            if has_quiz:
                meta_parts.append("📝")
            meta_suffix = f" [{' '.join(meta_parts)}]" if meta_parts else ""
            print(f"\033[96m{curr_folder}{meta_suffix}\033[0m")

            if show_dirs:
                # Get list of subfolders
                subfolders = get_subfolders(current_dir, show_hidden)
                if subfolders:
                    for idx, folder in enumerate(subfolders, 1):
                        sub_abs_path = os.path.join(current_dir, folder)
                        sub_tilde_path = to_tilde_path(sub_abs_path, workspace_root)

                        # Check if subfolder has quiz files
                        sub_quiz = check_quiz_exists(sub_abs_path)
                        quiz_indicator = " 📝" if sub_quiz else ""
                        # Check if subfolder is in working_rel_paths
                        is_sub_bookmarked = sub_tilde_path in working_rel_paths
                        bookmark_indicator = "⭐ " if is_sub_bookmarked else ""
                        # Check if subfolder has a direct alias
                        sub_alias = aliases.get(sub_tilde_path)
                        alias_lbl = f" [{sub_alias}]" if sub_alias else ""
                        print(f"  [{idx}] {bookmark_indicator}{folder}{alias_lbl}{quiz_indicator}")
                else:
                    print("  (Không có thư mục con)")

            if show_files:
                files_list = get_files(current_dir, show_hidden)
                if files_list:
                    print(f"  {GREY}📄 Tệp tin:{RESET}")
                    for f in files_list:
                        ext = os.path.splitext(f)[1].lower()
                        if ext == '.md':
                            icon = "📝"
                        elif ext == '.json':
                            icon = "📊"
                        elif ext == '.py':
                            icon = "🐍"
                        else:
                            icon = "📄"
                        print(f"     {icon} {f}")

        print("\033[90m--------------------------------------------------\033[0m")
        if show_help:
            print(f"{GREY}💡 HƯỚNG DẪN PHÍM TẮT:")

            print(f"\n🌐 Hệ thống (Global):")
            print(f"  .q      : Thoát chương trình")
            print(f"  .r      : Khởi động lại chương trình")
            print(f"  .h      : Ẩn hướng dẫn phím tắt này")
            print(f"  .cd     : Thoát và di chuyển shell terminal đến đây")
            print(f"  .gs     : Git Sync (add, commit & push toàn bộ thay đổi)")
            print(f"  .all    : Bật/Tắt hiển thị thư mục ẩn (như .learn)")
            print(f"  .sf     : Bật/Tắt hiển thị danh sách tệp tin (Show Files)")
            print(f"  .sd     : Bật/Tắt hiển thị danh sách thư mục con (Show Dirs)")
            print(f"  !<x>    : Chạy lệnh x")

            print(f"\n📌 Điều hướng (Navigation):")
            print(f"  <stt>   : Di chuyển đến thư mục tương ứng")
            print(f"  ..      : Quay lại thư mục cha")
            print(f"  n / b   : Chuyển sang thư mục kế tiếp / phía trước")
            print(f"  l       : Chuyển đổi view Bookmarks / Thư mục con")
            print(f"  ls      : Liệt kê các tệp & thư mục (vd: ls, ls1)")
            print(f"  nn      : Đổi tên thư mục n (vd: n1)")

            bookmark_desc = "Hủy bookmark thư mục hiện tại" if is_bookmarked else "Đánh dấu (bookmark) thư mục hiện tại"
            print(f"  x       : {bookmark_desc}")

            alias_desc = f"Xóa alias '{aliases[current_tilde_path]}' của thư mục này" if current_tilde_path in aliases else "Đặt alias cho thư mục hiện tại"
            print(f"  a       : {alias_desc}")

            print(f"\n📝 Soạn bài & Học (Prep & Quiz):")
            print(f"  p       : Soạn từ vựng (prep.py) thư mục hiện tại")
            print(f"  pn      : Soạn nhanh thư mục n (vd: p1)")
            print(f"  qn      : Học nhanh thư mục n (vd: q1)")
            print(f"  t       : Dịch bài & IPA (tran.py) thư mục hiện tại")
            print(f"  tn      : Dịch nhanh thư mục n (vd: t1)")
            print(f"--------------------------------------------------{RESET}\n")
        else:
            print(f"{GREY}💡 Nhập '.h' để hiển thị hướng dẫn đầy đủ.{RESET}")

        # Get user input
        try:
            choice = input(f"{GREY}Nhập STT hoặc lệnh: {RESET}").strip() # Keep original casing for shell commands
        except KeyboardInterrupt:
            print("\n👋 Tạm biệt!")
            break

        choice_lower = choice.lower()

        # Check if choice is a registered alias
        matched_alias_path = None
        for path, alias in aliases.items():
            if choice_lower == alias.lower():
                matched_alias_path = path
                break

        if choice_lower == '.q':
            print("\n👋 Tạm biệt!")
            break
        elif choice_lower == '.cd':
            cd_file = os.path.expanduser("~/.move_cd")
            try:
                with open(cd_file, "w", encoding="utf-8") as f:
                    f.write(current_dir)
            except Exception as e:
                print(f"\033[91m⚠️ Lỗi khi ghi file cd: {e}\033[0m")
            print(f"\n🚀 Đang thoát và di chuyển terminal đến {current_dir}...")
            break
        elif choice_lower == '.gs':
            git_sync(current_dir)
            continue
        elif choice_lower == '.sf':
            show_files = not show_files
            print(f"\n💡 Đã {'bật' if show_files else 'tắt'} hiển thị danh sách tệp tin.")
            time.sleep(1)
            continue
        elif choice_lower == '.sd':
            show_dirs = not show_dirs
            print(f"\n💡 Đã {'bật' if show_dirs else 'tắt'} hiển thị danh sách thư mục con.")
            time.sleep(1)
            continue
        elif choice_lower == '.all':
            show_hidden = not show_hidden
            print(f"\n💡 Đã {'bật' if show_hidden else 'tắt'} hiển thị thư mục ẩn.")
            time.sleep(1)
            continue
        elif choice.startswith('!'):
            shell_cmd = choice[1:].strip()
            if shell_cmd:
                print(f"\033[90m$ {shell_cmd}\033[0m")
                try:
                    subprocess.run(shell_cmd, shell=True)
                except KeyboardInterrupt:
                    pass
                except Exception as e:
                    print(f"\033[91m⚠️ Lỗi khi thực thi lệnh: {e}\033[0m")
                print("")
                try:
                    input("\033[90mNhấn Enter để tiếp tục...\033[0m")
                except (KeyboardInterrupt, EOFError):
                    pass
            continue
        elif choice_lower == 'ls' or choice_lower.startswith('ls'):
            target_path = current_dir
            arg = choice_lower[2:].strip()
            if arg:
                if arg.isdigit():
                    idx = int(arg)
                    if show_working_only:
                        if 1 <= idx <= len(resolved_working_dirs):
                            _, target_abs, is_valid = resolved_working_dirs[idx - 1]
                            if is_valid:
                                target_path = target_abs
                            else:
                                print(f"\n\033[91m⚠️ Thư mục không tồn tại.\033[0m")
                                time.sleep(1)
                                continue
                        else:
                            print(f"\033[93m⚠️ Số thứ tự không hợp lệ.\033[0m")
                            time.sleep(1)
                            continue
                    else:
                        subfolders = get_subfolders(current_dir, show_hidden)
                        if 1 <= idx <= len(subfolders):
                            selected_folder = subfolders[idx - 1]
                            target_path = os.path.join(current_dir, selected_folder)
                        else:
                            print(f"\033[93m⚠️ Số thứ tự không hợp lệ.\033[0m")
                            time.sleep(1)
                            continue
                else:
                    sub_abs = os.path.join(current_dir, arg)
                    if os.path.isdir(sub_abs):
                        target_path = sub_abs
                    else:
                        print(f"\n\033[91m⚠️ Không tìm thấy thư mục '{arg}'.\033[0m")
                        time.sleep(1)
                        continue
            list_files_and_folders(target_path, show_hidden)
        elif choice_lower == '.h':
            show_help = not show_help
            continue
        elif choice_lower == '~':
            home_dir = os.path.expanduser("~")
            os.chdir(home_dir)
            show_working_only = False
            print(f"\n🚀 Đang quay lại thư mục Home ({home_dir})...")
            time.sleep(1)
        elif choice_lower in ['n', 'b']:
            parent_dir = os.path.dirname(current_dir)
            siblings = get_subfolders(parent_dir, show_hidden)
            current_folder_name = os.path.basename(current_dir)

            if siblings and current_folder_name in siblings:
                idx = siblings.index(current_folder_name)
                target_idx = idx + 1 if choice_lower == 'n' else idx - 1

                if 0 <= target_idx < len(siblings):
                    target_name = siblings[target_idx]
                    target_abs = os.path.join(parent_dir, target_name)
                    os.chdir(target_abs)
                    show_working_only = False
                    direction_label = "kế tiếp" if choice_lower == 'n' else "phía trước"
                    print(f"\n🚀 Đang chuyển đến thư mục {direction_label}: {target_name}...")
                    time.sleep(1)
                else:
                    boundary_label = "cuối cùng" if choice_lower == 'n' else "đầu tiên"
                    print(f"\n\033[93m⚠️ Bạn đang ở thư mục {boundary_label} trong danh sách thư mục cha.\033[0m")
                    time.sleep(1.5)
            else:
                print("\n\033[93m⚠️ Không tìm thấy thư mục anh em để di chuyển.\033[0m")
                time.sleep(1.5)
        elif choice_lower in ['.', 'quiz']:
            if has_quiz:
                print("\n🚀 Đang khởi chạy quiz.py...")
                try:
                    # Execute quiz.py and pass the current directory
                    subprocess.run([sys.executable, quiz_path, current_dir])
                except KeyboardInterrupt:
                    pass
                except Exception as e:
                    print(f"\033[91m⚠️ Lỗi khi chạy quiz.py: {e}\033[0m")
                    try:
                        input("Nhấn Enter để tiếp tục...")
                    except (KeyboardInterrupt, EOFError):
                        pass
            else:
                print("\033[93m⚠️ Thư mục này không có preq.json! Không thể chạy test.\033[0m")
                time.sleep(1.5)
        elif choice_lower in ['p', 'prep']:
            print("\n🚀 Đang khởi chạy prep.py...")
            try:
                res = subprocess.run([sys.executable, prep_path, current_dir])
                if res.returncode != 0:
                    input(f"\n{GREY}Nhấn Enter để tiếp tục...{RESET}")
            except KeyboardInterrupt:
                pass
            except Exception as e:
                print(f"\033[91m⚠️ Lỗi khi chạy prep.py: {e}\033[0m")
                try:
                    input(f"\n{GREY}Nhấn Enter để tiếp tục...{RESET}")
                except (KeyboardInterrupt, EOFError):
                    pass
        elif choice_lower in ['t', 'tran']:
            print("\n🚀 Đang khởi chạy tran.py...")
            try:
                res = subprocess.run([sys.executable, tran_path, current_dir])
                if res.returncode != 0:
                    input(f"\n{GREY}Nhấn Enter để tiếp tục...{RESET}")
            except KeyboardInterrupt:
                pass
            except Exception as e:
                print(f"\033[91m⚠️ Lỗi khi chạy tran.py: {e}\033[0m")
                try:
                    input(f"\n{GREY}Nhấn Enter để tiếp tục...{RESET}")
                except (KeyboardInterrupt, EOFError):
                    pass
        elif matched_alias_path:
            abs_target = from_tilde_path(matched_alias_path, workspace_root)
            if os.path.isdir(abs_target):
                os.chdir(abs_target)
                show_working_only = False
                print(f"\n🚀 Đang dịch chuyển đến '{choice}'...")
                time.sleep(1)
            else:
                print(f"\n\033[91m⚠️ Thư mục của alias '{choice}' không tồn tại.\033[0m")
                time.sleep(1.5)
        elif choice_lower == 'x':
            # Toggle bookmark
            if is_bookmarked:
                working_rel_paths.remove(current_tilde_path)
                save_working_dirs(working_dirs_file, working_rel_paths)
                print("\033[93m❌ Đã xóa thư mục hiện tại khỏi Working Dirs!\033[0m")
            else:
                working_rel_paths.append(current_tilde_path)
                save_working_dirs(working_dirs_file, working_rel_paths)
                print("\033[92m✅ Đã đánh dấu thư mục hiện tại là Working Dir!\033[0m")
            time.sleep(1)
        elif choice_lower == 'a':
            if current_tilde_path in ["~", "~/english"]:
                print("\033[93m⚠️ Không thể tạo alias cho thư mục gốc (~ hoặc ~/english).\033[0m")
                time.sleep(1.5)
            else:
                if current_tilde_path in aliases:
                    old_alias = aliases.pop(current_tilde_path)
                    save_path_aliases(aliases_file, aliases)
                    print(f"\033[93m🗑️  Đã xóa alias '{old_alias}' cho thư mục hiện tại!\033[0m")
                else:
                    try:
                        alias_name = input("Đặt tên alias cho thư mục này (ví dụ: @ss): ").strip()
                        if alias_name:
                            if not alias_name.startswith("@"):
                                alias_name = "@" + alias_name
                            aliases[current_tilde_path] = alias_name
                            save_path_aliases(aliases_file, aliases)
                            print(f"\033[92m✅ Đã tạo alias '{alias_name}' thành công!\033[0m")
                        else:
                            print("❌ Hủy bỏ tạo alias.")
                    except KeyboardInterrupt:
                        print("\n❌ Hủy bỏ tạo alias.")
                time.sleep(1.5)
        elif choice_lower == '.r':
            os.system('clear' if os.name != 'nt' else 'cls')
            print("🔄 Đang khởi động lại move.py...")
            time.sleep(0.5)
            os.execv(sys.executable, [sys.executable] + sys.argv)
        elif choice_lower == 'l':
            show_working_only = not show_working_only
        elif choice_lower == '..':
            # Go up one level
            os.chdir('..')
        elif choice_lower.startswith('n') and choice_lower[1:].isdigit():
            idx = int(choice_lower[1:])
            target_path = None
            if show_working_only:
                if 1 <= idx <= len(resolved_working_dirs):
                    _, target_abs, is_valid = resolved_working_dirs[idx - 1]
                    if is_valid:
                        target_path = target_abs
                    else:
                        print(f"\n\033[91m⚠️ Thư mục không tồn tại.\033[0m")
                        time.sleep(1)
                else:
                    print(f"\033[93m⚠️ Số thứ tự không hợp lệ.\033[0m")
                    time.sleep(1)
            else:
                subfolders = get_subfolders(current_dir, show_hidden)
                if 1 <= idx <= len(subfolders):
                    selected_folder = subfolders[idx - 1]
                    target_path = os.path.join(current_dir, selected_folder)
                else:
                    print(f"\033[93m⚠️ Số thứ tự không hợp lệ.\033[0m")
                    time.sleep(1)

            if target_path:
                old_name = os.path.basename(target_path)
                try:
                    new_name = input(f"Nhập tên mới cho thư mục '{old_name}': ").strip()
                except KeyboardInterrupt:
                    new_name = ""

                if new_name:
                    parent_path = os.path.dirname(target_path)
                    new_path = os.path.join(parent_path, new_name)
                    if os.path.exists(new_path):
                        print(f"\033[91m⚠️ Tên thư mục '{new_name}' đã tồn tại.\033[0m")
                        time.sleep(1.5)
                    else:
                        try:
                            os.rename(target_path, new_path)
                            print(f"\033[92m✅ Đã đổi tên thư mục thành '{new_name}'.\033[0m")

                            # Update bookmarks (working dirs) and aliases!
                            old_tilde = to_tilde_path(target_path, workspace_root)
                            new_tilde = to_tilde_path(new_path, workspace_root)

                            # 1. Update working_rel_paths
                            updated_working = []
                            changed_working = False
                            for p in working_rel_paths:
                                if p == old_tilde:
                                    updated_working.append(new_tilde)
                                    changed_working = True
                                elif p.startswith(old_tilde + "/"):
                                    updated_working.append(new_tilde + p[len(old_tilde):])
                                    changed_working = True
                                else:
                                    updated_working.append(p)
                            if changed_working:
                                save_working_dirs(working_dirs_file, updated_working)

                            # 2. Update aliases
                            updated_aliases = {}
                            changed_aliases = False
                            for p, alias in aliases.items():
                                if p == old_tilde:
                                    updated_aliases[new_tilde] = alias
                                    changed_aliases = True
                                elif p.startswith(old_tilde + "/"):
                                    updated_aliases[new_tilde + p[len(old_tilde):]] = alias
                                    changed_aliases = True
                                else:
                                    updated_aliases[p] = alias
                            if changed_aliases:
                                save_path_aliases(aliases_file, updated_aliases)

                            # If we renamed the current folder we are inside, change directory
                            if target_path == current_dir:
                                os.chdir(new_path)

                        except Exception as e:
                            print(f"\033[91m⚠️ Lỗi khi đổi tên thư mục: {e}\033[0m")
                            time.sleep(1.5)
                else:
                    print("❌ Hủy bỏ đổi tên.")
                    time.sleep(1)
        elif choice_lower.startswith('q') and choice_lower[1:].isdigit():
            idx = int(choice_lower[1:])
            target_path = None
            if show_working_only:
                if 1 <= idx <= len(resolved_working_dirs):
                    target_rel, target_abs, is_valid = resolved_working_dirs[idx - 1]
                    if is_valid:
                        target_path = target_abs
                    else:
                        print(f"\n\033[91m⚠️ Thư mục '{target_rel}' không tồn tại.\033[0m")
                        time.sleep(1)
                else:
                    print(f"\033[93m⚠️ Số thứ tự không hợp lệ (1-{len(resolved_working_dirs)}).\033[0m")
                    time.sleep(1)
            else:
                subfolders = get_subfolders(current_dir, show_hidden)
                if 1 <= idx <= len(subfolders):
                    selected_folder = subfolders[idx - 1]
                    target_path = os.path.join(current_dir, selected_folder)
                else:
                    print(f"\033[93m⚠️ Số thứ tự không hợp lệ (1-{len(subfolders)}).\033[0m")
                    time.sleep(1)

            if target_path:
                if check_quiz_exists(target_path):
                    print(f"\n🚀 Đang khởi chạy quiz.py cho thư mục: {os.path.basename(target_path)}...")
                    try:
                        subprocess.run([sys.executable, quiz_path, target_path])
                    except KeyboardInterrupt:
                        pass
                    except Exception as e:
                        print(f"\033[91m⚠️ Lỗi khi chạy quiz.py: {e}\033[0m")
                        try:
                            input("Nhấn Enter để tiếp tục...")
                        except (KeyboardInterrupt, EOFError):
                            pass
                else:
                    print(f"\n\033[93m⚠️ Thư mục '{os.path.basename(target_path)}' không có sẵn câu hỏi để làm bài test.\033[0m")
                    time.sleep(1.5)
        elif choice_lower.startswith('p') and choice_lower[1:].isdigit():
            idx = int(choice_lower[1:])
            target_path = None
            if show_working_only:
                if 1 <= idx <= len(resolved_working_dirs):
                    target_rel, target_abs, is_valid = resolved_working_dirs[idx - 1]
                    if is_valid:
                        target_path = target_abs
                    else:
                        print(f"\n\033[91m⚠️ Thư mục '{target_rel}' không tồn tại.\033[0m")
                        time.sleep(1)
                else:
                    print(f"\033[93m⚠️ Số thứ tự không hợp lệ (1-{len(resolved_working_dirs)}).\033[0m")
                    time.sleep(1)
            else:
                subfolders = get_subfolders(current_dir, show_hidden)
                if 1 <= idx <= len(subfolders):
                    selected_folder = subfolders[idx - 1]
                    target_path = os.path.join(current_dir, selected_folder)
                else:
                    print(f"\033[93m⚠️ Số thứ tự không hợp lệ (1-{len(subfolders)}).\033[0m")
                    time.sleep(1)

            if target_path:
                print(f"\n🚀 Đang khởi chạy prep.py cho thư mục: {os.path.basename(target_path)}...")
                try:
                    res = subprocess.run([sys.executable, prep_path, target_path], cwd=target_path)
                    if res.returncode != 0:
                        input(f"\n{GREY}Nhấn Enter để tiếp tục...{RESET}")
                except KeyboardInterrupt:
                    pass
                except Exception as e:
                    print(f"\033[91m⚠️ Lỗi khi chạy prep.py: {e}\033[0m")
                    try:
                        input(f"\n{GREY}Nhấn Enter để tiếp tục...{RESET}")
                    except (KeyboardInterrupt, EOFError):
                        pass
        elif choice_lower.startswith('t') and choice_lower[1:].isdigit():
            idx = int(choice_lower[1:])
            target_path = None
            if show_working_only:
                if 1 <= idx <= len(resolved_working_dirs):
                    target_rel, target_abs, is_valid = resolved_working_dirs[idx - 1]
                    if is_valid:
                        target_path = target_abs
                    else:
                        print(f"\n\033[91m⚠️ Thư mục '{target_rel}' không tồn tại.\033[0m")
                        time.sleep(1)
                else:
                    print(f"\033[93m⚠️ Số thứ tự không hợp lệ (1-{len(resolved_working_dirs)}).\033[0m")
                    time.sleep(1)
            else:
                subfolders = get_subfolders(current_dir, show_hidden)
                if 1 <= idx <= len(subfolders):
                    selected_folder = subfolders[idx - 1]
                    target_path = os.path.join(current_dir, selected_folder)
                else:
                    print(f"\033[93m⚠️ Số thứ tự không hợp lệ (1-{len(subfolders)}).\033[0m")
                    time.sleep(1)

            if target_path:
                print(f"\n🚀 Đang khởi chạy tran.py cho thư mục: {os.path.basename(target_path)}...")
                try:
                    res = subprocess.run([sys.executable, tran_path, target_path], cwd=target_path)
                    if res.returncode != 0:
                        input(f"\n{GREY}Nhấn Enter để tiếp tục...{RESET}")
                except KeyboardInterrupt:
                    pass
                except Exception as e:
                    print(f"\033[91m⚠️ Lỗi khi chạy tran.py: {e}\033[0m")
                    try:
                        input(f"\n{GREY}Nhấn Enter để tiếp tục...{RESET}")
                    except (KeyboardInterrupt, EOFError):
                        pass
        elif choice_lower.isdigit():
            idx = int(choice_lower)
            if show_working_only:
                if 1 <= idx <= len(resolved_working_dirs):
                    target_rel, target_abs, is_valid = resolved_working_dirs[idx - 1]
                    if is_valid:
                        os.chdir(target_abs)
                        show_working_only = False
                    else:
                        print(f"\n\033[91m⚠️ Thư mục '{target_rel}' không tồn tại.\033[0m")
                        time.sleep(1)
                else:
                    print(f"\033[93m⚠️ Số thứ tự không hợp lệ (1-{len(resolved_working_dirs)}).\033[0m")
                    time.sleep(1)
            else:
                subfolders = get_subfolders(current_dir, show_hidden)
                if 1 <= idx <= len(subfolders):
                    selected_folder = subfolders[idx - 1]
                    os.chdir(selected_folder)
                else:
                    print(f"\033[93m⚠️ Số thứ tự không hợp lệ (1-{len(subfolders)}).\033[0m")
                    time.sleep(1)
        else:
            print("\033[93m⚠️ Lựa chọn không hợp lệ. Vui lòng nhập lại.\033[0m")
            time.sleep(1)

        # Set first_run to False after the first loop iteration
        first_run = False

if __name__ == "__main__":
    main()
