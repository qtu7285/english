#!/usr/bin/env python3
import os
import sys
import time
import re
import json
import uuid
import urllib.request
import urllib.parse
from datetime import datetime

# ANSI Colors
GREY = "\033[90m"
RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"

def print_divider():
    print(f"{GREY}--------------------------------------------------{RESET}")

def decode_git_path(p):
    p = p.strip('"')
    def replace_octal(match):
        octals = match.group(0).split('\\')[1:]
        byte_arr = bytearray(int(o, 8) for o in octals if o)
        return byte_arr.decode('utf-8', errors='replace')
    pattern = re.compile(r'(?:\\[0-7]{3})+')
    return pattern.sub(replace_octal, p)

def get_lesson_dir():
    cwd = os.getcwd()
    path = cwd
    while path and path != "/":
        # Check if lesson.md or prepare.md exists
        if any(os.path.exists(os.path.join(path, f)) for f in ["💧 lesson.md", "lesson.md"]):
            return path
        path = os.path.dirname(path)
    # Fallback to check if we are in a parent folder that has dailydictation.com
    return None

def get_cached_username(cache_file):
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data.get("default_user")
        except Exception:
            pass
    return None

def save_cached_username(cache_file, username):
    try:
        data = {}
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    data = loaded
        data["default_user"] = username
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
def save_prep_session(user_path, level):
    sess_file = os.path.join(user_path, "sess-prep.json")
    sessions = []
    if os.path.exists(sess_file):
        try:
            with open(sess_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    sessions = data
        except Exception:
            pass

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    found = False
    for s in sessions:
        if s.get("level") == level:
            s["last_datetime"] = now_str
            found = True
            break
    if not found:
        sessions.append({
            "level": level,
            "last_datetime": now_str
        })

    sessions.sort(key=lambda x: x.get("last_datetime", ""), reverse=True)

    try:
        with open(sess_file, "w", encoding="utf-8") as f:
            json.dump(sessions, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
def format_session_time(dt_str):
    if not dt_str:
        return ""
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%H:%M %d/%m")
    except Exception:
        return ""
def fetch_word_api(word):
    """
    Fetches POS and IPA from public dictionary API, and Vietnamese meaning from Google Translate API.
    """
    pos = "n."
    ipa = ""
    meaning = ""

    # 1. Fetch IPA and POS from dictionaryapi.dev
    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(word)}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            if isinstance(data, list) and len(data) > 0:
                entry = data[0]
                # Extract POS
                meanings = entry.get("meanings", [])
                if meanings:
                    raw_pos = meanings[0].get("partOfSpeech", "noun")
                    # Map to abbreviations
                    pos_map = {"noun": "n.", "verb": "v.", "adjective": "adj.", "adverb": "adv.", "preposition": "prep."}
                    pos = pos_map.get(raw_pos, "n.")
                # Extract IPA
                phonetics = entry.get("phonetics", [])
                for ph in phonetics:
                    text = ph.get("text", "")
                    if text:
                        ipa = text.strip("/")
                        break
    except Exception:
        pass

    # 2. Fetch Vietnamese meaning from Google Translate
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=vi&dt=t&q={urllib.parse.quote(word)}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list) and len(data[0]) > 0:
                meaning = data[0][0][0].strip().lower()
                if not meaning.endswith("."):
                    meaning += "."
    except Exception:
        pass

    return pos, ipa, meaning

def bold_word_in_text(text, w):
    parts = text.split("**")
    for idx in range(len(parts)):
        if idx % 2 == 0:  # Non-bolded part
            if ' ' in w:
                pattern = r'\b(' + re.escape(w) + r')\b'
            else:
                pattern = r'\b(' + re.escape(w) + r'[a-zA-Z]*)\b'
            parts[idx] = re.sub(pattern, r'**\1**', parts[idx], flags=re.IGNORECASE)
    return "".join(parts).replace("****", "")

class GoBackException(Exception):
    pass

class QuitException(Exception):
    pass

class RestartException(Exception):
    pass

class ShowInfoException(Exception):
    pass

SHORTCUTS_DB = {
    ".q": {"cmd": ".q", "desc": "Lưu tiến độ và thoát"},
    "..": {"cmd": "..", "desc": "Lưu tạm tiến độ và học tiếp"},
    ".._back": {"cmd": "..", "desc": "Quay lại bước trước đó"},
    ".._to_user": {"cmd": "..", "desc": "Quay lại màn hình thiết lập học viên (User)"},
    ".._to_level": {"cmd": "..", "desc": "Quay lại màn hình chọn cấp độ học"},
    "...": {"cmd": "...", "desc": "Xem bảng tiến độ học tập"},
    ".b": {"cmd": ".b", "desc": "Quay lại bước trước đó"},
    ".b_to_user": {"cmd": ".b", "desc": "Quay lại màn hình thiết lập học viên (User)"},
    ".b_to_level": {"cmd": ".b", "desc": "Quay lại màn hình chọn cấp độ học"},
    ".r": {"cmd": ".r", "desc": "Khởi động lại chương trình soạn bài"},
    ".h": {"cmd": ".h", "desc": "Xem hướng dẫn phím tắt này"},
    ".sel": {"cmd": ".sel [start] [end]", "desc": "Chọn khoảng câu học cho Level 0 (ví dụ: .sel 1 10)"},
    ".i": {"cmd": ".i", "desc": "Xem thông tin chi tiết của phiên học hiện tại"},
    ".": {"cmd": ".", "desc": "Bỏ qua câu hiện tại (không bôi đậm từ nào)"},
    ".u": {"cmd": ".u", "desc": "Bỏ check hoàn thành (chuyển về trạng thái chưa check ⏳)"},
    "xn_user": {"cmd": "x[n]", "desc": "Xóa User n hoặc mặc định (x* xóa tất cả)"},
    "xn_sess": {"cmd": "x[n]", "desc": "Xóa phiên n hoặc mặc định (x* xóa tất cả)"},
    "sn": {"cmd": "s[n]", "desc": "Sửa Level của phiên n hoặc mặc định"},
    "nn": {"cmd": "nn", "desc": "Đổi tên User thứ n (vd: n1)"},
    "new_sess": {"cmd": "n", "desc": "Tạo phiên soạn từ mới"},
    "[Enter]": {"cmd": "[Enter]", "desc": "Giữ nguyên trạng thái từ bôi đậm cũ/Đánh dấu check"},
    "words": {"cmd": "word1, word2", "desc": "Nhập từ bôi đậm mới (ngăn cách bởi dấu phẩy)"}
}

CONTEXTS_MAP = {
    "user_input": [".q", ".r", ".h", "nn", "xn_user"],
    "level_select": ["..", ".q", ".r", ".h", ".sel"],
    "session_select": [".q", ".r", ".h", "new_sess", "sn", "xn_sess"],
    "word_input": ["words", ".", ".u", "[Enter]", "..", ".q", ".r", ".h", ".i"]
}

def print_prep_guide(context):
    if context not in CONTEXTS_MAP:
        return

    keys = CONTEXTS_MAP[context]
    global_keys = [k for k in keys if k in [".q", ".r", "..", ".h"]]
    local_keys = [k for k in keys if k not in [".q", ".r", "..", ".h"]]

    all_keys = [k for k in keys if k in SHORTCUTS_DB]
    cmds = [SHORTCUTS_DB[k]["cmd"] for k in all_keys]
    max_cmd_len = max(len(c) for c in cmds) if cmds else 12

    print(f"\n{GREY}💡 HƯỚNG DẪN PHÍM TẮT:")

    if global_keys:
        print(f"\n🌐 Hệ thống (Global):")
        for key in global_keys:
            if key in SHORTCUTS_DB:
                item = SHORTCUTS_DB[key]
                print(f"  {item['cmd']:<{max_cmd_len}} : {item['desc']}")

    if local_keys:
        print(f"\n📌 Chức năng (Private):")
        for key in local_keys:
            if key in SHORTCUTS_DB:
                item = SHORTCUTS_DB[key]
                print(f"  {item['cmd']:<{max_cmd_len}} : {item['desc']}")

    print(f"--------------------------------------------------{RESET}\n")

def update_scbn_learn_range(user_path, start, end):
    updated_any = False
    for filename in ["scbn.md", "scbk.md"]:
        lvl_f = os.path.join(user_path, "lv0", filename)
        if not os.path.exists(lvl_f):
            continue
        try:
            with open(lvl_f, "r", encoding="utf-8") as f:
                lines = f.readlines()

            new_lines = []
            updated = False
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("|"):
                    cols = [c.replace(r"\|", "|").strip() for c in re.split(r'(?<!\\)\|', stripped)[1:-1]]
                    if cols:
                        if cols[0].lower() == "stt":
                            line = "| STT | NAME | ENGLISH | SCORE | LEARN |\n"
                        elif cols[0].startswith(":---") or cols[0].endswith("---:"):
                            line = "| :---: | :--- | :--- | :---: | :---: |\n"
                        elif cols[0].isdigit():
                            stt = int(cols[0])
                            status = "Y" if start <= stt <= end else "-"
                            name_val = cols[1].replace("|", r"\|")
                            eng_val = cols[2].replace("|", r"\|")
                            score_val = cols[3] if len(cols) >= 4 else "0"
                            line = f"| {stt} | {name_val} | {eng_val} | {score_val} | {status} |\n"
                            updated = True
                new_lines.append(line)

            if updated:
                with open(lvl_f, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
                updated_any = True
        except Exception as e:
            print(f"\033[91m⚠️ Lỗi khi cập nhật {filename}: {e}\033[0m")

    return updated_any

def prep_input(prompt, context):
    while True:
        try:
            val = input(prompt).strip()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Tạm biệt!")
            sys.exit(0)

        val_lower = val.lower()
        if val_lower == ".q":
            raise QuitException()
        elif val_lower == ".r":
            raise RestartException()
        elif val_lower == "..":
            raise GoBackException()
        elif val_lower == ".h":
            print_prep_guide(context)
            continue
        elif val_lower == ".i":
            raise ShowInfoException()
        return val

def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if not arg.startswith("-") and os.path.isdir(arg):
            os.chdir(arg)

    os.system('clear' if os.name != 'nt' else 'cls')
    lesson_dir = get_lesson_dir()
    if not lesson_dir:
        print(f"{RED}❌ Lỗi: Không tìm thấy thư mục bài học chứa '💧 lesson.md' hoặc 'lesson.md'.{RESET}")
        sys.exit(1)

    # Find lesson file
    lesson_file = os.path.join(lesson_dir, "💧 lesson.md")
    if not os.path.exists(lesson_file):
        lesson_file = os.path.join(lesson_dir, "lesson.md")

    # Find prepare file
    prepare_file = os.path.join(lesson_dir, "🪺 prepare.md")
    if not os.path.exists(prepare_file):
        prepare_file = os.path.join(lesson_dir, "prepare.md")
        if not os.path.exists(prepare_file):
            print(f"{YELLOW}⚠️ Cảnh báo: Không tìm thấy tệp '🪺 prepare.md'.{RESET}")
            try:
                confirm = input("Bạn có muốn tự động tạo bản dịch & phiên âm thô bằng tran.py không? (⭐y/n): ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                confirm = "n"
            if confirm in ["", "y", "yes", "co", "có"]:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                tran_script = os.path.join(script_dir, "tran.py")
                if os.path.exists(tran_script):
                    import subprocess
                    print("🚀 Đang khởi chạy tran.py để chuẩn bị bài học...")
                    try:
                        subprocess.run([sys.executable, tran_script, lesson_dir])
                        prepare_file = os.path.join(lesson_dir, "🪺 prepare.md")
                    except Exception as e:
                        print(f"{RED}❌ Lỗi khi khởi chạy tran.py: {e}{RESET}")
                        sys.exit(1)
                else:
                    print(f"{RED}❌ Lỗi: Không tìm thấy tệp 'tran.py' tại {tran_script}.{RESET}")
                    sys.exit(1)
            else:
                print(f"{GREY}💡 Mẹo: Bạn có thể dùng Agent @pre trong giao diện chat để dịch nghĩa chuẩn và sinh phiên âm cả câu trước.{RESET}")
                sys.exit(1)

            if not os.path.exists(prepare_file):
                print(f"{RED}❌ Lỗi: Không tìm thấy tệp '🪺 prepare.md' sau khi chạy tran.py.{RESET}")
                sys.exit(1)

            try:
                start_prep = input(f"\n❓ Bạn có muốn bắt đầu soạn từ vựng ngay không? (y/n) [Mặc định: n - Enter để thoát]: ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                start_prep = "n"
            if start_prep not in ["y", "yes", "co", "có"]:
                print(f"\n{GREEN}👋 Đã tạo xong bản dịch thô. Quay lại Terminal!{RESET}\n")
                sys.exit(0)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    cache_file = os.path.join(script_dir, "user-cache.json")

    # Detect CWD context
    cwd = os.getcwd()
    username = None
    level = None

    # Try parsing context from CWD path
    # e.g., .../👤 qtu/lv1
    match_lv = re.search(r"👤\s*([^/]+)/lv(\d+)", cwd)
    match_usr = re.search(r"👤\s*([^/]+)$", cwd)

    if match_lv:
        username = match_lv.group(1).strip()
        level = int(match_lv.group(2))
    elif match_usr:
        username = match_usr.group(1).strip()

    # Step 1: Parse lesson metadata (YAML frontmatter)
    lid = str(uuid.uuid4())
    lesson_title = os.path.basename(lesson_dir)
    if os.path.exists(lesson_file):
        with open(lesson_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        in_fm = False
        for line in lines:
            if line.strip() == "---":
                in_fm = not in_fm
                continue
            if in_fm:
                m_id = re.match(r"^id:\s*(.*)$", line.strip())
                if m_id:
                    lid = m_id.group(1).strip()
            elif line.strip().startswith("#"):
                lesson_title = line.strip().lstrip("#").strip()

    # Step 2: Parse prepare.md table
    sentences = {}
    with open(prepare_file, "r", encoding="utf-8") as f:
        prep_lines = f.readlines()

    header_indices = {}
    parsed_headers = False

    for line in prep_lines:
        line_str = line.strip()
        if line_str.startswith("|"):
            cols = [c.replace(r"\|", "|").strip() for c in re.split(r'(?<!\\)\|', line_str)[1:-1]]
            if not cols:
                continue

            # Check if this is a separator line (e.g. |---|---|)
            if all(re.match(r'^[-:\s]+$', c) for c in cols):
                continue

            # Parse header row
            if not parsed_headers:
                lower_cols = [c.lower() for c in cols]
                for idx, col in enumerate(lower_cols):
                    if any(x in col for x in ["stt", "no.", "no", "id", "thứ tự", "thu tu"]):
                        header_indices["stt"] = idx
                    elif any(x in col for x in ["english", "eng", "tiếng anh", "tieng anh"]):
                        header_indices["english"] = idx
                    elif any(x in col for x in ["vietnamese", "vi", "viet", "tiếng việt", "tieng viet", "dịch", "dich"]):
                        header_indices["vietnamese"] = idx
                    elif any(x in col for x in ["ipa", "phiên âm", "phien am"]):
                        header_indices["ipa"] = idx
                    elif any(x in col for x in ["name", "tên", "ten"]):
                        header_indices["name"] = idx
                parsed_headers = True
                continue

            # Parse data rows
            stt_idx = header_indices.get("stt", 0)
            if stt_idx < len(cols) and cols[stt_idx].isdigit():
                eng_idx = header_indices.get("english", 1)
                vi_idx = header_indices.get("vietnamese", 2)
                ipa_idx = header_indices.get("ipa")
                name_idx = header_indices.get("name")

                stt = int(cols[stt_idx])
                eng = cols[eng_idx] if eng_idx < len(cols) else ""
                vi = cols[vi_idx] if vi_idx < len(cols) else ""
                ipa = cols[ipa_idx] if (ipa_idx is not None and ipa_idx < len(cols)) else ""
                name_val = cols[name_idx] if (name_idx is not None and name_idx < len(cols)) else None

                sentences[stt] = {"english": eng, "vietnamese": vi, "ipa": ipa, "name": name_val}

    if not sentences:
        print(f"{RED}❌ Lỗi: Không đọc được câu nào từ bảng trong tệp '🪺 prepare.md'.{RESET}")
        sys.exit(1)

    # Start loop for user/level selection
    # Start loop for user/level selection
    should_exit = False
    while True:
        try:
            # 1. Gather all prep sessions from all users
            all_sessions = []
            user_folders = [f.replace("👤", "").strip() for f in os.listdir(lesson_dir) if f.startswith("👤") and os.path.isdir(os.path.join(lesson_dir, f))]
            user_folders = sorted(list(set(user_folders)))

            for u in user_folders:
                sess_file = os.path.join(lesson_dir, f"👤 {u}", "sess-prep.json")
                if os.path.exists(sess_file):
                    try:
                        with open(sess_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                for item in data:
                                    if isinstance(item, dict) and "level" in item:
                                        all_sessions.append({
                                            "username": u,
                                            "level": item["level"],
                                            "last_datetime": item.get("last_datetime", "")
                                        })
                    except Exception:
                        pass

            all_sessions.sort(key=lambda x: x.get("last_datetime", ""), reverse=True)

            # 2. Determine user and level
            active_user = None
            active_level = None

            # If username and level are passed via CLI/CWD, use them directly
            if username is not None and level is not None:
                active_user = username
                active_level = level
            elif all_sessions:
                print(f"\n{YELLOW}📊 Danh sách phiên soạn từ:{RESET}\n")
                for idx, s in enumerate(all_sessions, 1):
                    marker = " (⭐)" if idx == 1 else ""
                    time_str = format_session_time(s.get("last_datetime", ""))
                    time_prefix = f"{time_str} " if time_str else ""
                    print(f"  [{idx}] {time_prefix}{s['username']} - Lv{s['level']}{marker}")
                print()
                try:
                    choice = prep_input(f"{GREY}Chọn STT hoặc 'n' để tạo mới: {RESET}", "session_select").strip().lower()
                except GoBackException:
                    print("\n👋 Tạm biệt!")
                    sys.exit(0)

                if choice == "":
                    choice = "1"

                if choice == "n":
                    pass
                elif choice.startswith('x'):
                    targets = []
                    is_all = False

                    if choice == 'x':
                        if all_sessions:
                            targets = [all_sessions[0]]
                    elif choice == 'x*':
                        targets = all_sessions
                        is_all = True
                    elif choice[1:].isdigit():
                        idx = int(choice[1:])
                        if 1 <= idx <= len(all_sessions):
                            targets = [all_sessions[idx - 1]]

                    if targets:
                        if is_all:
                            try:
                                confirm = prep_input(f"\n{RED}⚠️ Xóa tất cả các phiên? (⭐y/n): {RESET}", "level_select").strip().lower()
                            except GoBackException:
                                os.system('clear' if os.name != 'nt' else 'cls')
                                continue
                            if confirm in ["", "y", "yes", "co", "có"]:
                                for s in targets:
                                    u = s["username"]
                                    lv = s["level"]
                                    del_path = os.path.join(lesson_dir, f"👤 {u}", f"lv{lv}")
                                    if os.path.isdir(del_path):
                                        import shutil
                                        try:
                                            shutil.rmtree(del_path)
                                        except Exception:
                                            pass
                                    sess_file = os.path.join(lesson_dir, f"👤 {u}", "sess-prep.json")
                                    if os.path.exists(sess_file):
                                        try:
                                            os.remove(sess_file)
                                        except Exception:
                                            pass
                                print(f"\n{GREEN}✅ Đã xóa toàn bộ các phiên thành công.{RESET}")
                                time.sleep(1.5)
                            else:
                                print(f"\n{YELLOW}Hủy bỏ xóa.{RESET}")
                                time.sleep(1)
                        else:
                            del_sess = targets[0]
                            del_user = del_sess["username"]
                            del_lv = del_sess["level"]
                            try:
                                confirm = prep_input(f"\n{RED}⚠️ Xóa phiên '{del_user} - Lv{del_lv}'? (⭐y/n): {RESET}", "level_select").strip().lower()
                            except GoBackException:
                                os.system('clear' if os.name != 'nt' else 'cls')
                                continue
                            if confirm in ["", "y", "yes", "co", "có"]:
                                del_path = os.path.join(lesson_dir, f"👤 {del_user}", f"lv{del_lv}")
                                if os.path.isdir(del_path):
                                    import shutil
                                    try:
                                        shutil.rmtree(del_path)
                                        print(f"\n{GREEN}✅ Đã xóa tiến trình phiên '{del_user} - Lv{del_lv}' thành công.{RESET}")
                                    except Exception as e:
                                        print(f"\n{RED}⚠️ Lỗi khi xóa: {e}{RESET}")
                                else:
                                    print(f"\n{RED}⚠️ Không tìm thấy thư mục tiến trình của phiên này.{RESET}")

                                sess_file = os.path.join(lesson_dir, f"👤 {del_user}", "sess-prep.json")
                                if os.path.exists(sess_file):
                                    try:
                                        with open(sess_file, "r", encoding="utf-8") as f:
                                            data = json.load(f)
                                        if isinstance(data, list):
                                            updated_data = [item for item in data if item.get("level") != del_lv]
                                            with open(sess_file, "w", encoding="utf-8") as f:
                                                json.dump(updated_data, f, ensure_ascii=False, indent=2)
                                    except Exception:
                                        pass
                                time.sleep(1.5)
                            else:
                                print(f"\n{YELLOW}Hủy bỏ xóa phiên.{RESET}")
                                time.sleep(1)
                        os.system('clear' if os.name != 'nt' else 'cls')
                        continue
                    else:
                        print(f"{RED}⚠️ Số thứ tự hoặc cú pháp không hợp lệ.{RESET}")
                        time.sleep(1.5)
                        os.system('clear' if os.name != 'nt' else 'cls')
                        continue
                elif choice.startswith('s'):
                    target = None
                    if choice == 's':
                        if all_sessions:
                            target = all_sessions[0]
                    elif choice[1:].isdigit():
                        idx = int(choice[1:])
                        if 1 <= idx <= len(all_sessions):
                            target = all_sessions[idx - 1]

                    if target:
                        sess_user = target["username"]
                        sess_lv = target["level"]
                        try:
                            print()
                            lv_input = prep_input(f"{GREY}Nhập Level mới cho User '{sess_user}' (0-5): {RESET}", "level_select").strip()
                        except GoBackException:
                            os.system('clear' if os.name != 'nt' else 'cls')
                            continue

                        if lv_input.isdigit() and (0 <= int(lv_input) <= 5):
                            new_lv = int(lv_input)
                            sess_file = os.path.join(lesson_dir, f"👤 {sess_user}", "sess-prep.json")
                            if os.path.exists(sess_file):
                                try:
                                    with open(sess_file, "r", encoding="utf-8") as f:
                                        data = json.load(f)
                                    if isinstance(data, list):
                                        found = False
                                        for s in data:
                                            if s.get("level") == sess_lv:
                                                s["level"] = new_lv
                                                s["last_datetime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                                found = True
                                                break
                                        if found:
                                            seen = set()
                                            unique_data = []
                                            for s in data:
                                                lvl = s.get("level")
                                                if lvl not in seen:
                                                    seen.add(lvl)
                                                    unique_data.append(s)
                                            unique_data.sort(key=lambda x: x.get("last_datetime", ""), reverse=True)
                                            with open(sess_file, "w", encoding="utf-8") as f:
                                                json.dump(unique_data, f, ensure_ascii=False, indent=2)
                                            print(f"\n{GREEN}✅ Đã chuyển phiên của User '{sess_user}' sang Lv{new_lv}.{RESET}")
                                        else:
                                            save_prep_session(os.path.dirname(sess_file), new_lv)
                                            print(f"\n{GREEN}✅ Đã tạo phiên Lv{new_lv} cho User '{sess_user}'.{RESET}")
                                    time.sleep(1.5)
                                except Exception as e:
                                    print(f"\n{RED}⚠️ Lỗi khi sửa phiên: {e}{RESET}")
                                    time.sleep(1.5)
                            else:
                                user_path = os.path.join(lesson_dir, f"👤 {sess_user}")
                                save_prep_session(user_path, new_lv)
                                print(f"\n{GREEN}✅ Đã tạo phiên Lv{new_lv} cho User '{sess_user}'.{RESET}")
                                time.sleep(1.5)
                        else:
                            print(f"{RED}⚠️ Level không hợp lệ.{RESET}")
                            time.sleep(1.5)
                        os.system('clear' if os.name != 'nt' else 'cls')
                        continue
                    else:
                        print(f"{RED}⚠️ Số thứ tự hoặc cú pháp không hợp lệ.{RESET}")
                        time.sleep(1.5)
                        os.system('clear' if os.name != 'nt' else 'cls')
                        continue
                elif choice.isdigit():
                    sel = int(choice)
                    if 1 <= sel <= len(all_sessions):
                        active_user = all_sessions[sel - 1]["username"]
                        active_level = all_sessions[sel - 1]["level"]
                    else:
                        print(f"{RED}⚠️ Số thứ tự không hợp lệ.{RESET}")
                        time.sleep(1)
                        os.system('clear' if os.name != 'nt' else 'cls')
                        continue
                else:
                    print(f"{RED}⚠️ Nhập không hợp lệ.{RESET}")
                    time.sleep(1)
                    os.system('clear' if os.name != 'nt' else 'cls')
                    continue

            # 3. Resolve username if not set
            if not active_user:
                print(f"\n{GREEN}👉 TẠO PHIÊN SOẠN TỪ:{RESET}")
                active_user = username
                if active_user:
                    save_cached_username(cache_file, active_user)
                else:
                    if user_folders:
                        print("\n👤 Users:\n")
                        cached_user = get_cached_username(cache_file)
                        default_user = cached_user
                        if not default_user or default_user not in user_folders:
                            default_user = user_folders[0]

                        default_idx = None
                        for idx, u in enumerate(user_folders, 1):
                            is_default = (u == default_user)
                            marker = " (⭐)" if is_default else ""
                            if is_default:
                                default_idx = idx
                            print(f"  [{idx}] {u}{marker}")

                        print()
                        prompt_msg = f"{GREY}Chọn hoặc nhập username: {RESET}"
                        user_input = prep_input(prompt_msg, "user_input").strip()
                        user_input_lower = user_input.lower()

                        if user_input_lower.startswith('x'):
                            targets_user = []
                            is_all_users = False
                            if user_input_lower == 'x':
                                if default_user:
                                    targets_user = [default_user]
                            elif user_input_lower == 'x*':
                                targets_user = user_folders
                                is_all_users = True
                            elif user_input_lower[1:].isdigit():
                                idx = int(user_input_lower[1:])
                                if 1 <= idx <= len(user_folders):
                                    targets_user = [user_folders[idx - 1]]

                            if targets_user:
                                if is_all_users:
                                    try:
                                        confirm = prep_input(f"\n{RED}⚠️ Xóa tất cả các User? (⭐y/n): {RESET}", "level_select").strip().lower()
                                    except GoBackException:
                                        continue
                                    if confirm in ["", "y", "yes", "co", "có"]:
                                        for u in targets_user:
                                            del_path = os.path.join(lesson_dir, f"👤 {u}")
                                            if os.path.isdir(del_path):
                                                import shutil
                                                try:
                                                    shutil.rmtree(del_path)
                                                except Exception:
                                                    pass
                                        save_cached_username(cache_file, "")
                                        print(f"\n{GREEN}✅ Đã xóa toàn bộ User thành công.{RESET}")
                                        time.sleep(1.5)
                                    else:
                                        print(f"\n{YELLOW}Hủy bỏ xóa.{RESET}")
                                        time.sleep(1)
                                else:
                                    del_user = targets_user[0]
                                    try:
                                        confirm = prep_input(f"\n{RED}⚠️ Xóa User '{del_user}'? (⭐y/n): {RESET}", "level_select").strip().lower()
                                    except GoBackException:
                                        continue
                                    if confirm in ["", "y", "yes", "co", "có"]:
                                        del_path = os.path.join(lesson_dir, f"👤 {del_user}")
                                        if os.path.isdir(del_path):
                                            import shutil
                                            try:
                                                shutil.rmtree(del_path)
                                                print(f"\n{GREEN}✅ Đã xóa User '{del_user}' thành công.{RESET}")
                                            except Exception as e:
                                                print(f"\n{RED}⚠️ Lỗi khi xóa: {e}{RESET}")
                                        else:
                                            print(f"\n{RED}⚠️ Không tìm thấy thư mục của User '{del_user}'.{RESET}")
                                        if cached_user == del_user:
                                            save_cached_username(cache_file, "")
                                        time.sleep(1.5)
                                    else:
                                        print(f"\n{YELLOW}Hủy bỏ xóa User.{RESET}")
                                        time.sleep(1)
                                os.system('clear' if os.name != 'nt' else 'cls')
                                continue
                            else:
                                print(f"{RED}⚠️ Số thứ tự hoặc cú pháp không hợp lệ.{RESET}")
                                time.sleep(1.5)
                                os.system('clear' if os.name != 'nt' else 'cls')
                                continue

                        if user_input_lower.startswith('n') and user_input_lower[1:].isdigit():
                            idx = int(user_input_lower[1:])
                            if 1 <= idx <= len(user_folders):
                                old_user = user_folders[idx - 1]
                                try:
                                    new_name_raw = prep_input(f"Nhập tên mới cho User '{old_user}': ", "user_input").strip()
                                except GoBackException:
                                    os.system('clear' if os.name != 'nt' else 'cls')
                                    continue

                                new_user = "".join(c for c in new_name_raw if c.isalnum() or c in ('-', '_')).strip()
                                if not new_user:
                                    print(f"{RED}⚠️ Tên mới không hợp lệ.{RESET}")
                                    time.sleep(1.5)
                                elif new_user in user_folders:
                                    print(f"{RED}⚠️ Tên User '{new_user}' đã tồn tại.{RESET}")
                                    time.sleep(1.5)
                                else:
                                    old_path = os.path.join(lesson_dir, f"👤 {old_user}")
                                    new_path = os.path.join(lesson_dir, f"👤 {new_user}")
                                    if os.path.isdir(old_path):
                                        try:
                                            os.rename(old_path, new_path)
                                            print(f"\n{GREEN}✅ Đã đổi tên User '{old_user}' thành '{new_user}'.{RESET}")
                                            if cached_user == old_user:
                                                save_cached_username(cache_file, new_user)
                                                cached_user = new_user
                                        except Exception as e:
                                            print(f"\n{RED}⚠️ Lỗi khi đổi tên: {e}{RESET}")
                                    else:
                                        print(f"\n{RED}⚠️ Không tìm thấy thư mục của User '{old_user}'.{RESET}")
                                    time.sleep(1.5)
                                os.system('clear' if os.name != 'nt' else 'cls')
                                continue
                            else:
                                print(f"{RED}Số thứ tự không hợp lệ.{RESET}")
                                time.sleep(1.5)
                                os.system('clear' if os.name != 'nt' else 'cls')
                                continue

                        if not user_input:
                            if default_user:
                                active_user = default_user
                            else:
                                print(f"{RED}Tên User không được trống.{RESET}")
                                continue
                        elif user_input.isdigit():
                            sel = int(user_input)
                            if 1 <= sel <= len(user_folders):
                                active_user = user_folders[sel - 1]
                            else:
                                print(f"{RED}Số thứ tự không hợp lệ.{RESET}")
                                continue
                        else:
                            active_user = "".join(c for c in user_input if c.isalnum() or c in ('-', '_')).strip()
                            if not active_user:
                                print(f"{RED}Tên User không hợp lệ.{RESET}")
                                continue
                    else:
                        prompt_msg = f"{GREY}Nhập username mới: {RESET}"
                        user_input = prep_input(prompt_msg, "user_input").strip()
                        if not user_input:
                            print(f"{RED}Tên User không được trống.{RESET}")
                            continue
                        active_user = "".join(c for c in user_input if c.isalnum() or c in ('-', '_')).strip()
                        if not active_user:
                            print(f"{RED}Tên User không hợp lệ.{RESET}")
                            continue

                    save_cached_username(cache_file, active_user)

            # 4. Resolve level if not set
            if active_level is None:
                active_level = level
                if active_level is None:
                    try:
                        print()
                        print("\033[93m💡 Gợi ý: Gõ '.sel [bắt đầu] [kết thúc]' (vd: .sel 1 10) để giới hạn khoảng câu soạn Level 0.\033[0m")
                        lv_input = prep_input(f"{GREY}Chọn Level (0-5): {RESET}", "level_select")
                    except GoBackException:
                        username = None
                        os.system('clear' if os.name != 'nt' else 'cls')
                        continue
                    if lv_input.lower().startswith(".sel"):
                        parts = lv_input.split()
                        start_num = None
                        end_num = None
                        if len(parts) >= 3:
                            try:
                                start_num = int(parts[1])
                                end_num = int(parts[2])
                            except ValueError:
                                pass

                        if start_num is None or end_num is None:
                            try:
                                start_str = input("Nhập STT bắt đầu: ").strip()
                                end_str = input("Nhập STT kết thúc: ").strip()
                                start_num = int(start_str)
                                end_num = int(end_str)
                            except (ValueError, KeyboardInterrupt, EOFError):
                                print(f"\n{RED}⚠️ Lỗi: Khoảng STT không hợp lệ.{RESET}\n")
                                continue

                        if start_num is not None and end_num is not None:
                            if start_num > end_num:
                                start_num, end_num = end_num, start_num

                            user_folder_name = f"👤 {active_user}"
                            user_path = os.path.join(lesson_dir, user_folder_name)
                            success = update_scbn_learn_range(user_path, start_num, end_num)
                            if success:
                                print(f"\n{GREEN}✅ Đã chọn khoảng câu từ {start_num} đến {end_num} thành 'Y'. Các câu khác thành '-'.{RESET}")
                                print(f"{YELLOW}🚀 Tự động tiến hành soạn bài Level 0 cho các câu đã chọn...{RESET}\n")
                                time.sleep(1.5)
                                active_level = 0
                            else:
                                continue
                        else:
                            continue
                    elif not lv_input.isdigit() or not (0 <= int(lv_input) <= 5):
                        print(f"{RED}Level phải là số từ 0 đến 5.{RESET}")
                        continue
                    else:
                        active_level = int(lv_input)

            username = active_user
            level = active_level

            user_folder_name = f"👤 {active_user}"
            user_path = os.path.join(lesson_dir, user_folder_name)
            level_path = os.path.join(user_path, f"lv{active_level}")
            os.makedirs(level_path, exist_ok=True)

            save_prep_session(user_path, active_level)

            if active_level == 0:
                # Direct generation of lv0 files (preq.json, scbn.md & scbk.md)
                lv0_preq = os.path.join(level_path, "preq.json")

                # Read existing learn status from scbn.md (or scbk.md as fallback)
                lv0_existing_learn = {}
                for filename in ["scbn.md", "scbk.md"]:
                    lv0_f = os.path.join(level_path, filename)
                    if os.path.exists(lv0_f):
                        try:
                            with open(lv0_f, "r", encoding="utf-8") as f:
                                lines = f.readlines()
                            for line in lines:
                                if line.strip().startswith("|"):
                                    cols = [c.replace(r"\|", "|").strip() for c in re.split(r'(?<!\\)\|', line.strip())[1:-1]]
                                    if cols and cols[0].isdigit() and len(cols) >= 5:
                                        lv0_existing_learn[int(cols[0])] = cols[4]
                        except Exception:
                            pass

                # 1. preq.json (Write all sentences)
                lv0_preq_words = []
                for s_stt in sorted(sentences.keys()):
                    s_info = sentences[s_stt]
                    w_clean = s_info["english"].strip()
                    q_item = {
                        "id": str(uuid.uuid4()),
                        "lid": lid,
                        "word": w_clean,
                        "stt": s_stt,
                        "sentence_no": s_stt,
                        "sentence_original": f"{s_stt}. 🛫 {s_info['english']}",
                        "masked_sentence": s_info['english'],
                        "targets": [s_info['english']],
                        "meaning": s_info.get("name") or "Nhớ câu",
                        "translation": s_info["vietnamese"],
                        "ipa": s_info["ipa"]
                    }
                    if s_info.get("name"):
                        q_item["name"] = s_info["name"]
                    lv0_preq_words.append(q_item)
                with open(lv0_preq, "w", encoding="utf-8") as f:
                    json.dump({"words": lv0_preq_words}, f, ensure_ascii=False, indent=2)

                # 2. Write both scbn.md and scbk.md
                for filename in ["scbn.md", "scbk.md"]:
                    lv0_f = os.path.join(level_path, filename)
                    lv0_existing_scores = {}
                    if os.path.exists(lv0_f):
                        try:
                            with open(lv0_f, "r", encoding="utf-8") as f:
                                lines = f.readlines()
                            for line in lines:
                                if line.strip().startswith("|"):
                                    cols = [c.replace(r"\|", "|").strip() for c in re.split(r'(?<!\\)\|', line.strip())[1:-1]]
                                    if cols and cols[0].isdigit() and len(cols) >= 4:
                                        lv0_existing_scores[int(cols[0])] = int(cols[3])
                        except Exception:
                            pass

                    lv0_f_lines = [
                        "## 📊 Tiến độ học theo Tên (Name)\n\n" if filename == "scbn.md" else "## 📊 Tiến độ học theo STT (Key)\n\n",
                        "| STT | NAME | ENGLISH | SCORE | LEARN |\n",
                        "| :---: | :--- | :--- | :---: | :---: |\n"
                    ]
                    for s_stt in sorted(sentences.keys()):
                        s_info = sentences[s_stt]
                        name_val = (s_info.get("name") or "").replace("|", r"\|")
                        eng_val = s_info["english"].replace("|", r"\|")
                        score_val = lv0_existing_scores.get(s_stt, 0)
                        status_val = "Y"
                        lv0_f_lines.append(f"| {s_stt} | {name_val} | {eng_val} | {score_val} | {status_val} |\n")
                    with open(lv0_f, "w", encoding="utf-8") as f:
                        f.writelines(lv0_f_lines)

                # Create basic quiz session for Mode N if missing
                quiz_sess_file = os.path.join(user_path, "sess-quiz.json")
                if not os.path.exists(quiz_sess_file):
                    initial_sess = [
                        {
                            "input_mode": "N",
                            "priority_mode": 3,
                            "levels": [0],
                            "last_datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                    ]
                    with open(quiz_sess_file, "w", encoding="utf-8") as f:
                        json.dump(initial_sess, f, ensure_ascii=False, indent=2)

                print(f"\n{GREEN}✅ Đã hoàn tất soạn và đồng bộ toàn bộ tệp tin cho Level 0 (Mode N)!{RESET}")
                time.sleep(1.5)

                # Ask if they want to continue
                print_divider()
                choice = input("Bạn muốn tiếp tục không?\n"
                               " u: Chọn User và Level khác\n"
                               " .sel: Chọn lại khoảng câu cho Level 0\n"
                               " Enter để thoát\n"
                               " Lựa chọn của bạn (u/Enter/.sel): ").strip().lower()

                if choice.startswith(".sel"):
                    parts = choice.split()
                    start_num = None
                    end_num = None
                    if len(parts) >= 3:
                        try:
                            start_num = int(parts[1])
                            end_num = int(parts[2])
                        except ValueError:
                            pass

                    if start_num is None or end_num is None:
                        try:
                            start_str = input("Nhập STT bắt đầu: ").strip()
                            end_str = input("Nhập STT kết thúc: ").strip()
                            start_num = int(start_str)
                            end_num = int(end_str)
                        except (ValueError, KeyboardInterrupt, EOFError):
                            print(f"\n{RED}⚠️ Lỗi: Khoảng STT không hợp lệ.{RESET}\n")
                            continue

                    if start_num is not None and end_num is not None:
                        if start_num > end_num:
                            start_num, end_num = end_num, start_num

                        user_folder_name = f"👤 {active_user}"
                        user_path = os.path.join(lesson_dir, user_folder_name)
                        success = update_scbn_learn_range(user_path, start_num, end_num)
                        if success:
                            print(f"\n{GREEN}✅ Đã chọn khoảng câu từ {start_num} đến {end_num} thành 'Y'. Các câu khác thành '-'.{RESET}")
                            print(f"{YELLOW}🚀 Tự động tiến hành soạn lại bài Level 0 cho các câu đã chọn...{RESET}\n")
                            time.sleep(1.5)
                            active_level = 0
                            username = active_user
                            level = active_level
                            continue
                    continue
                elif choice == "u":
                    username = None
                    level = None
                    os.system('clear' if os.name != 'nt' else 'cls')
                    continue
                else:
                    print(f"\n{GREEN}👋 Tạm biệt! Hẹn gặp lại.{RESET}")
                    break

            bold_file = os.path.join(level_path, "bold.md")
            preg_file = os.path.join(level_path, "preg.json")
            preq_file = os.path.join(level_path, "preq.json")

            # Load existing bold.md progress if it exists
            bold_progress = {}
            if os.path.exists(bold_file):
                with open(bold_file, "r", encoding="utf-8") as f:
                    b_lines = f.readlines()
                for line in b_lines:
                    if line.strip().startswith("|"):
                        cols = [c.replace(r"\|", "|").strip() for c in re.split(r'(?<!\\)\|', line.strip())[1:-1]]
                        if cols and cols[0].isdigit():
                            stt = int(cols[0])
                            eng_cell = cols[1]
                            status_cell = cols[2] if len(cols) > 2 else "⏳"
                            # Extract bolded words from cell
                            b_words = re.findall(r"\*\*([^*]+)\*\*", eng_cell)
                            bold_progress[stt] = {"words": b_words, "status": status_cell}

            # Initialize bold_progress for missing sentences
            for stt in sentences.keys():
                if stt not in bold_progress:
                    bold_progress[stt] = {"words": [], "status": "⏳"}

            # Check checked vs unchecked status
            checked_count = sum(1 for stt in sentences.keys() if bold_progress.get(stt, {}).get("status") == "✅")
            total_sentences = len(sentences)
            sorted_stt_list = sorted(sentences.keys())

            if checked_count > 0:
                menu_loop = True
                while menu_loop:
                    os.system('clear' if os.name != 'nt' else 'cls')
                    # Recalculate checked count in case of reset inside loop
                    checked_count = sum(1 for stt in sentences.keys() if bold_progress.get(stt, {}).get("status") == "✅")
                    print(f"\n{YELLOW}📊 Đã soạn {checked_count}/{total_sentences} câu.{RESET}\n")
                    if checked_count < total_sentences:
                        print("  [1] Soạn tiếp câu chưa check (⭐)")
                    else:
                        print("  [1] (Đã hoàn thành tất cả)")
                    print("  [2] Soạn lại toàn bộ (giữ từ)")
                    if checked_count > 0:
                        print("  [3] Sửa các câu đã check")
                    else:
                        print("  [3] (Chưa có câu nào được check)")
                    print("  [4] Liệt kê câu đã check")
                    print("  [5] Liệt kê câu chưa check")
                    print("  [6] Liệt kê tất cả câu")
                    print("  [7] Reset tiến trình (xóa hết)")
                    print("  [8] Quay lại Cấp độ")
                    print()
                    try:
                        choice = prep_input(f"{GREY}Chọn (1-8): {RESET}", "level_select").strip()
                    except GoBackException:
                        username = None
                        level = None
                        os.system('clear' if os.name != 'nt' else 'cls')
                        break

                    if choice == "":
                        if checked_count < total_sentences:
                            choice = "1"
                        else:
                            choice = "2"

                    if choice == "1":
                        if checked_count < total_sentences:
                            sorted_stt_list = [stt for stt in sorted(sentences.keys()) if bold_progress.get(stt, {}).get("status") != "✅"]
                            menu_loop = False
                        else:
                            print(f"\n{RED}⚠️ Không còn câu chưa check nào!{RESET}")
                            time.sleep(1.5)
                    elif choice == "2":
                        sorted_stt_list = sorted(sentences.keys())
                        menu_loop = False
                    elif choice == "3":
                        if checked_count > 0:
                            sorted_stt_list = [stt for stt in sorted(sentences.keys()) if bold_progress.get(stt, {}).get("status") == "✅"]
                            menu_loop = False
                        else:
                            print(f"\n{RED}⚠️ Chưa có câu nào được check!{RESET}")
                            time.sleep(1.5)
                    elif choice == "4":
                        print(f"\n{GREEN}📋 CÁC CÂU ĐÃ CHECK (HOÀN THÀNH):{RESET}")
                        print_divider()
                        count = 0
                        for s_stt in sorted(sentences.keys()):
                            if bold_progress.get(s_stt, {}).get("status") == "✅":
                                eng_text = sentences[s_stt]["english"]
                                for w in bold_progress[s_stt]["words"]:
                                    eng_text = bold_word_in_text(eng_text, w)
                                words_str = ", ".join(bold_progress[s_stt]["words"]) or "(không chọn từ)"
                                name_val = sentences[s_stt].get("name")
                                name_prefix = f"👤 {name_val.strip()}: " if (name_val and name_val.strip()) else ""
                                print(f"[{s_stt}] {name_prefix}{eng_text}")
                                print(f"    {GREY}💬 {sentences[s_stt]['vietnamese']}{RESET}")
                                print(f"    {GREY}📦 Từ vựng: {words_str}{RESET}")
                                print_divider()
                                count += 1
                        if count == 0:
                            print("  (Chưa có câu nào được check)")
                        input(f"\n{YELLOW}Nhấn Enter để quay lại menu...{RESET}")
                    elif choice == "5":
                        print(f"\n{GREEN}📋 CÁC CÂU CHƯA CHECK (CHƯA HOÀN THÀNH):{RESET}")
                        print_divider()
                        count = 0
                        for s_stt in sorted(sentences.keys()):
                            if bold_progress.get(s_stt, {}).get("status") != "✅":
                                eng_text = sentences[s_stt]["english"]
                                name_val = sentences[s_stt].get("name")
                                name_prefix = f"👤 {name_val.strip()}: " if (name_val and name_val.strip()) else ""
                                print(f"[{s_stt}] {name_prefix}{eng_text}")
                                print(f"    {GREY}💬 {sentences[s_stt]['vietnamese']}{RESET}")
                                print_divider()
                                count += 1
                        if count == 0:
                            print("  (Không có câu nào chưa check)")
                        input(f"\n{YELLOW}Nhấn Enter để quay lại menu...{RESET}")
                    elif choice == "6":
                        print(f"\n{GREEN}📋 TẤT CẢ CÁC CÂU TRONG BÀI HỌC:{RESET}")
                        print_divider()
                        for s_stt in sorted(sentences.keys()):
                            status_char = bold_progress.get(s_stt, {}).get("status", "⏳")
                            eng_text = sentences[s_stt]["english"]
                            for w in bold_progress.get(s_stt, {}).get("words", []):
                                eng_text = bold_word_in_text(eng_text, w)
                            words_str = ", ".join(bold_progress.get(s_stt, {}).get("words", []))
                            words_suffix = f" [Từ: {words_str}]" if words_str else ""
                            name_val = sentences[s_stt].get("name")
                            name_prefix = f"👤 {name_val.strip()}: " if (name_val and name_val.strip()) else ""
                            print(f"[{s_stt}] [{status_char}] {name_prefix}{eng_text}{words_suffix}")
                            print(f"    {GREY}💬 {sentences[s_stt]['vietnamese']}{RESET}")
                            print_divider()
                        input(f"\n{YELLOW}Nhấn Enter để quay lại menu...{RESET}")
                    elif choice == "7":
                        try:
                            confirm = prep_input(f"\n{RED}⚠️ Reset tiến trình và từ vựng? (⭐y/n): {RESET}", "level_select").strip().lower()
                        except GoBackException:
                            continue
                        if confirm in ["", "y", "yes", "co", "có"]:
                            # Reset bold_progress
                            for s in sentences.keys():
                                bold_progress[s] = {"words": [], "status": "⏳"}
                            # Save empty bold.md
                            bold_lines = [
                                "---\n",
                                f"id: {lid}\n",
                                f"lc: \"1\"\n",
                                "---\n",
                                f"# {lesson_title} 🔑\n\n",
                                "| STT | English | TT |\n",
                                "| :---: | :--- | :---: |\n"
                            ]
                            for s_stt in sorted(sentences.keys()):
                                bold_lines.append(f"| {s_stt} | {sentences[s_stt]['english']} | ⏳ |\n")
                            with open(bold_file, "w", encoding="utf-8") as f:
                                f.writelines(bold_lines)

                            # Delete JSON files if they exist
                            for f_path in [preg_file, preq_file]:
                                if os.path.exists(f_path):
                                    try:
                                        os.remove(f_path)
                                    except Exception:
                                        pass

                            print(f"\n{GREEN}✅ Đã reset toàn bộ tiến trình.{RESET}")
                            time.sleep(1)
                        else:
                            print(f"\n{YELLOW}Hủy bỏ reset.{RESET}")
                            time.sleep(1)
                    elif choice == "8":
                        username = None
                        level = None
                        os.system('clear' if os.name != 'nt' else 'cls')
                        break
                    else:
                        print(f"\n{RED}⚠️ Lựa chọn không hợp lệ!{RESET}")
                        time.sleep(1)

                if username is None or level is None:
                    continue
            else:
                # If checked_count == 0, go straight to checking all
                sorted_stt_list = sorted(sentences.keys())

            # Interactive loop sentence by sentence
            stt_index = 0

            while stt_index < len(sorted_stt_list):
                stt = sorted_stt_list[stt_index]
                os.system('clear' if os.name != 'nt' else 'cls')
                print(f"\n{GREEN}🏁 SOẠN BÀI: {active_user} - Lv{active_level}{RESET}\n")

                s_data = sentences[stt]
                clean_eng = s_data["english"]
                vi_trans = s_data["vietnamese"]

                # Retrieve currently selected words
                current_words = bold_progress[stt]["words"]
                current_status = bold_progress[stt]["status"]

                name_val = s_data.get("name")
                header_text = f" [CH {stt} / {total_sentences}] "
                print(f"\033[90m{header_text.center(50, '-')}\033[0m")
                if name_val and name_val.strip():
                    print(f"\033[96m👤  {name_val.strip()}\033[0m")
                print(f"👉  {clean_eng}")
                print(f"\033[90m💬  {vi_trans}\033[0m")
                if current_words:
                    print(f"\033[90m📦 Đang chọn: {', '.join(current_words)} ({current_status})\033[0m")
                print("\033[2;90m--------------------------------------------------\033[0m")

                try:
                    val = prep_input("📝 Nhập từ: ", "word_input")
                except GoBackException:
                    if stt_index > 0:
                        stt_index -= 1
                    else:
                        print(f"{YELLOW}⚠️ Đây đã là câu đầu tiên, không thể quay lại.{RESET}")
                        time.sleep(1)
                    continue
                except ShowInfoException:
                    os.system('clear' if os.name != 'nt' else 'cls')
                    print(f"\n{YELLOW}📊 THÔNG TIN PHIÊN SOẠN BÀI:{RESET}")
                    print(f"  - Học viên : {active_user}")
                    print(f"  - Cấp độ   : Lv{active_level}")

                    c_count = sum(1 for s in sentences.keys() if bold_progress.get(s, {}).get("status") == "✅")
                    pct = int(c_count * 100 / total_sentences) if total_sentences else 0
                    print(f"  - Tiến trình: {c_count}/{total_sentences} câu ({pct}%)")

                    rel_bold_file = bold_file.replace(lesson_dir, "").strip("/")
                    print(f"  - File lưu : {rel_bold_file}")
                    print(f"\n{GREY}--------------------------------------------------{RESET}")
                    try:
                        input(f"\n{YELLOW}Nhấn Enter để quay lại soạn bài...{RESET}")
                    except (KeyboardInterrupt, EOFError):
                        pass
                    continue

                if val.lower() == "q":
                    print(f"\n{YELLOW}⚠️ Đang dừng phiên soạn bài...{RESET}")
                    should_exit = True
                    break
                elif val == ".":
                    bold_progress[stt] = {"words": [], "status": "✅"}
                elif val.lower() == ".u":
                    bold_progress[stt]["status"] = "⏳"
                elif val == "":
                    # Keep existing
                    bold_progress[stt]["status"] = "✅"
                else:
                    # User typed new words
                    selected_words = [w.strip() for w in val.split(",") if w.strip()]
                    bold_progress[stt] = {"words": selected_words, "status": "✅"}

                # Live save bold.md
                # Construct bold.md content
                bold_lines = [
                    "---\n",
                    f"id: {lid}\n",
                    f"lc: \"1\"\n",
                    "---\n",
                    f"# {lesson_title} 🔑\n\n",
                    "| STT | English | TT |\n",
                    "| :---: | :--- | :---: |\n"
                ]
                for s_stt in sorted(sentences.keys()):
                    eng_text = sentences[s_stt]["english"]
                    # Apply bolds
                    for w in bold_progress[s_stt]["words"]:
                        eng_text = bold_word_in_text(eng_text, w)
                    status_char = bold_progress[s_stt]["status"]
                    bold_lines.append(f"| {s_stt} | {eng_text} | {status_char} |\n")

                with open(bold_file, "w", encoding="utf-8") as f:
                    f.writelines(bold_lines)
                print(f"💾 Saved {os.path.basename(bold_file)}")
                stt_index += 1

            pass

        except GoBackException:
            username = None
            level = None
            os.system('clear' if os.name != 'nt' else 'cls')
            continue
        except RestartException:
            os.system('clear' if os.name != 'nt' else 'cls')
            print("🔄 Đang khởi động lại prep.py...")
            time.sleep(0.5)
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except QuitException:
            print(f"\n{YELLOW}⚠️ Đang dừng phiên soạn bài...{RESET}")
            should_exit = True

        # Check if we completed or exited early
        is_completed = all(bold_progress[s]["status"] == "✅" for s in sentences.keys())
        has_any_words = any(len(bold_progress[s]["words"]) > 0 for s in sentences.keys())

        should_save = True
        if should_exit and not is_completed and has_any_words:
            try:
                confirm = input(f"\n{YELLOW}❓ Bạn có muốn cập nhật dữ liệu JSON cho phần đã soạn dở dang không? (y/n) [Mặc định: y]: {RESET}").strip().lower()
                if confirm in ["n", "no", "k", "không"]:
                    should_save = False
            except (KeyboardInterrupt, EOFError):
                should_save = False

        if should_save and (is_completed or has_any_words):
            if is_completed:
                print(f"\n{GREEN}🎉 Hoàn thành duyệt {total_sentences} câu! Đang tạo cấu trúc dữ liệu JSON...{RESET}")
            else:
                print(f"\n{YELLOW}💾 Đang cập nhật dữ liệu JSON cho các câu đã soạn dở dang...{RESET}")

            # Collect all selected words
            all_selected_words = []
            word_sentence_map = []

            for s_stt in sorted(sentences.keys()):
                for w in bold_progress[s_stt]["words"]:
                    # Clean word casing/punctuation
                    clean_w = w.strip().lower()
                    if clean_w not in all_selected_words:
                        all_selected_words.append(clean_w)
                    word_sentence_map.append({
                        "word": clean_w,
                        "bold_word": w,
                        "sentence_no": s_stt
                    })

            # 1. Fetch info for words (preg.json)
            # Try to load existing preg.json in other levels to avoid network lookup
            known_words = {}
            for other_lv in range(1, 6):
                other_preg = os.path.join(user_path, f"lv{other_lv}", "preg.json")
                if os.path.exists(other_preg):
                    try:
                        with open(other_preg, "r", encoding="utf-8") as f:
                            other_data = json.load(f)
                            for item in other_data:
                                known_words[item["word"]] = item
                    except Exception:
                        pass

            preg_data = []
            print(f"🔍 Đang tra cứu nghĩa và phiên âm cho {len(all_selected_words)} từ vựng...")

            for idx, w in enumerate(all_selected_words, 1):
                if w in known_words:
                    item = known_words[w]
                    print(f"   [{idx}/{len(all_selected_words)}] (Đã biết) {w} -> {item.get('meaning')}")
                    preg_data.append(item)
                else:
                    print(f"   [{idx}/{len(all_selected_words)}] (Mới) {w}...", end="", flush=True)
                    pos, ipa, meaning = fetch_word_api(w)
                    audio_url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=en&client=tw-ob&q={urllib.parse.quote(w)},%20{urllib.parse.quote(w)},%20{urllib.parse.quote(w)}"
                    item = {
                        "word": w,
                        "pos": pos,
                        "ipa": ipa,
                        "audio": audio_url,
                        "meaning": meaning or "chưa dịch."
                    }
                    print(f" {item['ipa']} -> {item['meaning']}")
                    preg_data.append(item)

            # Write preg.json with correct ordering
            with open(preg_file, "w", encoding="utf-8") as f:
                json.dump(preg_data, f, ensure_ascii=False, indent=2)
            print(f"💾 Saved {preg_file}")

            # 2. Build preq.json (Questions database)
            preq_words = []
            word_stt_map = {item["word"]: idx for idx, item in enumerate(preg_data, 1)}

            for mapping in word_sentence_map:
                w_lower = mapping["word"]
                bold_w = mapping["bold_word"]
                s_no = mapping["sentence_no"]

                # Fetch sentence translation/ipa from prepare.md
                s_info = sentences[s_no]
                s_eng = s_info["english"]
                s_vi = s_info["vietnamese"]
                s_ipa = s_info["ipa"]

                # Get word specific details
                w_details = next((item for item in preg_data if item["word"] == w_lower), {})

                # Generate masked sentence
                # Split original sentence by word boundary and replace target word
                # Let's count how many selected words are in this sentence
                s_selected_words = bold_progress[s_no]["words"]

                masked_sentence = s_eng
                targets = []

                if len(s_selected_words) == 1:
                    # Single word replace with _______
                    # Using case insensitive regex replace with word boundaries
                    target_word = s_selected_words[0]
                    # We match target word + letters
                    pattern = r'\b' + re.escape(target_word) + r'[a-zA-Z]*\b'
                    match = re.search(pattern, masked_sentence, flags=re.IGNORECASE)
                    if match:
                        targets.append(match.group(0))
                        masked_sentence = re.sub(pattern, "_______", masked_sentence, flags=re.IGNORECASE)
                else:
                    # Multiple words replaced with _______ (1), _______ (2)
                    # We sort them by their appearance order in the sentence
                    # Find all occurrences of selected words
                    occurrences = []
                    for tw in s_selected_words:
                        pattern = r'\b' + re.escape(tw) + r'[a-zA-Z]*\b'
                        for match in re.finditer(pattern, s_eng, flags=re.IGNORECASE):
                            occurrences.append((match.start(), match.group(0), pattern))

                    # Sort by start index
                    occurrences.sort()

                    # Perform replacement sequentially from right to left to preserve indices
                    occurrences_reversed = reversed(occurrences)
                    # We need target list from left to right
                    targets = [occ[1] for occ in occurrences]

                    # Convert to list to modify string indices
                    for i_idx, (start, word_matched, pattern) in enumerate(reversed(occurrences)):
                        item_num = len(occurrences) - i_idx
                        # Replace only that specific match
                        masked_sentence = masked_sentence[:start] + f"_______ ({item_num})" + masked_sentence[start + len(word_matched):]

                # Create question item
                q_item = {
                    "id": str(uuid.uuid4()),
                    "lid": lid,
                    "word": w_lower,
                    "stt": word_stt_map.get(w_lower, 999),
                    "sentence_no": s_no,
                    "sentence_original": f"{s_no}. 🛫 " + bold_word_in_text(s_eng, bold_w),  # Keep legacy compatibility with quiz.py
                    "masked_sentence": masked_sentence,
                    "targets": targets or [w_lower],
                    "meaning": w_details.get("meaning", ""),
                    "translation": s_vi,
                    "ipa": s_ipa
                }
                if s_info.get("name"):
                    q_item["name"] = s_info["name"]
                preq_words.append(q_item)

            # Write preq.json
            preq_data = {"words": preq_words}
            with open(preq_file, "w", encoding="utf-8") as f:
                json.dump(preq_data, f, ensure_ascii=False, indent=2)
            print(f"💾 Saved {preq_file}")

            # 3. Create basic sessions file if missing
            sess_file = os.path.join(user_path, "sess-quiz.json")
            if not os.path.exists(sess_file):
                initial_sess = [
                    {
                        "input_mode": "W",
                        "priority_mode": 3,
                        "levels": [active_level],
                        "last_datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                ]
                with open(sess_file, "w", encoding="utf-8") as f:
                    json.dump(initial_sess, f, ensure_ascii=False, indent=2)
                print(f"💾 Created {sess_file}")

            # Automatically generate/sync level 0 files
            try:
                lv0_path = os.path.join(user_path, "lv0")
                os.makedirs(lv0_path, exist_ok=True)
                lv0_preq = os.path.join(lv0_path, "preq.json")

                # Read existing learn status from scbn.md (or scbk.md as fallback)
                lv0_existing_learn = {}
                for filename in ["scbn.md", "scbk.md"]:
                    lv0_f = os.path.join(lv0_path, filename)
                    if os.path.exists(lv0_f):
                        try:
                            with open(lv0_f, "r", encoding="utf-8") as f:
                                lines = f.readlines()
                            for line in lines:
                                if line.strip().startswith("|"):
                                    cols = [c.replace(r"\|", "|").strip() for c in re.split(r'(?<!\\)\|', line.strip())[1:-1]]
                                    if cols and cols[0].isdigit() and len(cols) >= 5:
                                        lv0_existing_learn[int(cols[0])] = cols[4]
                        except Exception:
                            pass

                # 1. preq.json (Only write Y sentences)
                lv0_preq_words = []
                for s_stt in sorted(sentences.keys()):
                    s_info = sentences[s_stt]
                    is_learn = lv0_existing_learn.get(s_stt, "Y")
                    if is_learn != "Y":
                        continue

                    w_clean = s_info["english"].strip()
                    q_item = {
                        "id": str(uuid.uuid4()),
                        "lid": lid,
                        "word": w_clean,
                        "stt": s_stt,
                        "sentence_no": s_stt,
                        "sentence_original": f"{s_stt}. 🛫 {s_info['english']}",
                        "masked_sentence": s_info['english'],
                        "targets": [s_info['english']],
                        "meaning": s_info.get("name") or "Nhớ câu",
                        "translation": s_info["vietnamese"],
                        "ipa": s_info["ipa"]
                    }
                    if s_info.get("name"):
                        q_item["name"] = s_info["name"]
                    lv0_preq_words.append(q_item)
                with open(lv0_preq, "w", encoding="utf-8") as f:
                    json.dump({"words": lv0_preq_words}, f, ensure_ascii=False, indent=2)

                # 2. Write both scbn.md and scbk.md
                for filename in ["scbn.md", "scbk.md"]:
                    lv0_f = os.path.join(lv0_path, filename)
                    lv0_existing_scores = {}
                    if os.path.exists(lv0_f):
                        try:
                            with open(lv0_f, "r", encoding="utf-8") as f:
                                lines = f.readlines()
                            for line in lines:
                                if line.strip().startswith("|"):
                                    cols = [c.replace(r"\|", "|").strip() for c in re.split(r'(?<!\\)\|', line.strip())[1:-1]]
                                    if cols and cols[0].isdigit() and len(cols) >= 4:
                                        lv0_existing_scores[int(cols[0])] = int(cols[3])
                        except Exception:
                            pass

                    lv0_f_lines = [
                        "## 📊 Tiến độ học theo Tên (Name)\n\n" if filename == "scbn.md" else "## 📊 Tiến độ học theo STT (Key)\n\n",
                        "| STT | NAME | ENGLISH | SCORE | LEARN |\n",
                        "| :---: | :--- | :--- | :---: | :---: |\n"
                    ]
                    for s_stt in sorted(sentences.keys()):
                        s_info = sentences[s_stt]
                        name_val = (s_info.get("name") or "").replace("|", r"\|")
                        eng_val = s_info["english"].replace("|", r"\|")
                        score_val = lv0_existing_scores.get(s_stt, 0)
                        status_val = lv0_existing_learn.get(s_stt, "Y")
                        lv0_f_lines.append(f"| {s_stt} | {name_val} | {eng_val} | {score_val} | {status_val} |\n")
                    with open(lv0_f, "w", encoding="utf-8") as f:
                        f.writelines(lv0_f_lines)
                print(f"💾 Automatically generated/updated Level 0 (Mode N/K) files in {lv0_path}")
            except Exception as e:
                print(f"⚠️ Warning: Could not automatically generate Level 0 files: {e}")

            print(f"\n{GREEN}✅ Đã hoàn tất soạn và đồng bộ toàn bộ tệp tin cho Level {active_level}!{RESET}")

        if should_exit:
            break

        # Interactive option for next steps
        print_divider()
        choice = input("Bạn muốn tiếp tục không?\n"
                       " u: Chọn User và Level khác\n"
                       " l: Chọn Level khác cho cùng User\n"
                       " r: Làm lại từ đầu cho User và Level hiện hành\n"
                       " .sel: Chọn lại khoảng câu cho Level 0\n"
                       " Nhấn Enter để thoát\n"
                       " Lựa chọn của bạn (u/l/r/Enter/.sel): ").strip().lower()

        if choice.startswith(".sel"):
            parts = choice.split()
            start_num = None
            end_num = None
            if len(parts) >= 3:
                try:
                    start_num = int(parts[1])
                    end_num = int(parts[2])
                except ValueError:
                    pass

            if start_num is None or end_num is None:
                try:
                    start_str = input("Nhập STT bắt đầu: ").strip()
                    end_str = input("Nhập STT kết thúc: ").strip()
                    start_num = int(start_str)
                    end_num = int(end_str)
                except (ValueError, KeyboardInterrupt, EOFError):
                    print(f"\n{RED}⚠️ Lỗi: Khoảng STT không hợp lệ.{RESET}\n")
                    continue

            if start_num is not None and end_num is not None:
                if start_num > end_num:
                    start_num, end_num = end_num, start_num

                user_folder_name = f"👤 {active_user}"
                user_path = os.path.join(lesson_dir, user_folder_name)
                success = update_scbn_learn_range(user_path, start_num, end_num)
                if success:
                    print(f"\n{GREEN}✅ Đã chọn khoảng câu từ {start_num} đến {end_num} thành 'Y'. Các câu khác thành '-'.{RESET}")
                    print(f"{YELLOW}🚀 Tự động tiến hành soạn lại bài Level 0 cho các câu đã chọn...{RESET}\n")
                    time.sleep(1.5)
                    active_level = 0
                    username = active_user
                    level = active_level
                    continue
            continue

        if choice == "u":
            username = None
            level = None
            continue
        elif choice == "l":
            level = None
            continue
        elif choice == "r":
            # Clear status and restart loop
            for s in bold_progress.keys():
                bold_progress[s] = {"words": [], "status": "⏳"}
            # Write empty bold.md
            bold_lines = [
                "---\n", f"id: {lid}\n", "lc: \"1\"\n", "---\n",
                f"# {lesson_title} 🔑\n\n",
                "| STT | English | TT |\n",
                "| :---: | :--- | :---: |\n"
            ]
            for s_stt in sorted(sentences.keys()):
                bold_lines.append(f"| {s_stt} | {sentences[s_stt]['english']} | ⏳ |\n")
            with open(bold_file, "w", encoding="utf-8") as f:
                f.writelines(bold_lines)
            print(f"💾 Cleared progress in {bold_file}")
            continue
        else:
            print(f"\n{GREEN}👋 Tạm biệt! Hẹn gặp lại.{RESET}")
            break

if __name__ == "__main__":
    main()
