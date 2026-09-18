#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

def migrate_legacy_json_files(lesson_dir, user_dir):
    # 1. Shared files in lesson_dir
    migrations = [
        ("questions.json", "preq.json"),
        ("preq.json", "preq.json"),
        ("voca.json", "preg.json"),
        ("preg.json", "preg.json"),
        ("words.md", "bold.md"),
        ("bold.md", "bold.md"),
    ]
    for old_name, new_name in migrations:
        old_f = os.path.join(lesson_dir, old_name)
        new_f = os.path.join(lesson_dir, new_name)
        if os.path.exists(old_f) and not os.path.exists(new_f):
            try:
                os.rename(old_f, new_f)
            except Exception:
                pass

    # 2. User files in user_dir and its level folders
    if user_dir:
        user_folders = [user_dir] + [os.path.join(user_dir, f"lv{idx}") for idx in range(0, 6)]
        user_migrations = migrations + [
            ("write.md", "scwr.md"),
            ("scwr.md", "scwr.md"),
            ("speak.md", "scsp.md"),
            ("scsp.md", "scsp.md"),
            ("sess.json", "sess-quiz.json"),
        ]
        for folder in user_folders:
            if os.path.exists(folder):
                for old_name, new_name in user_migrations:
                    old_f = os.path.join(folder, old_name)
                    new_f = os.path.join(folder, new_name)
                    if os.path.exists(old_f) and not os.path.exists(new_f):
                        try:
                            os.rename(old_f, new_f)
                        except Exception:
                            pass

import json
import re
import random
import time
from datetime import datetime

class GoBackException(Exception):
    """Exception raised to go back to level selection."""
    pass

class QuitException(Exception):
    """Exception raised to quit the program."""
    pass

class RestartException(Exception):
    """Exception raised to restart the program."""
    pass

class RestartSessionException(Exception):
    """Exception raised to restart the session/quiz."""
    pass

def quiz_input(prompt=""):
    try:
        val = input(prompt)
    except (KeyboardInterrupt, EOFError):
        raise
    val_clean = val.strip().lower()
    if val_clean == "..":
        raise GoBackException()
    if val_clean == ".q":
        raise QuitException()
    if val_clean == ".r":
        raise RestartException()
    if val_clean == ".r.":
        raise RestartSessionException()
    return val

# Global variables for files to be resolved dynamically
LESSON_FILE = ""
USER_DIR = ""
LESSON_DIR = ""
SELECTED_LEVELS = [1]

def is_session_muted(session_dict):
    if not session_dict:
        return False
    m_mode = session_dict.get("input_mode", "W")
    return session_dict.get("mute", m_mode in ["N", "K"])

def update_scbn_learn_range(user_dir, start, end):
    updated_any = False
    for filename in ["scbn.md", "scbk.md"]:
        lvl_f = os.path.join(user_dir, "lv0", filename)
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

def rebuild_lv0_preq(user_dir, lesson_dir):
    lv0_dir = os.path.join(user_dir, "lv0")
    lv0_preq = os.path.join(lv0_dir, "preq.json")
    scbn_file = os.path.join(lv0_dir, "scbn.md")

    if not os.path.exists(scbn_file):
        return False

    learn_map = {}
    try:
        with open(scbn_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("|"):
                    cols = [c.replace(r"\|", "|").strip() for c in re.split(r'(?<!\\)\|', line.strip())[1:-1]]
                    if cols and cols[0].isdigit() and len(cols) >= 5:
                        learn_map[int(cols[0])] = cols[4]
    except Exception:
        pass

    existing_items_by_stt = {}
    if os.path.exists(lv0_preq):
        try:
            with open(lv0_preq, "r", encoding="utf-8") as f:
                data = json.load(f)
                for w in data.get("words", []):
                    stt = w.get("stt", w.get("sentence_no"))
                    if stt is not None:
                        existing_items_by_stt[stt] = w
        except Exception:
            pass

    if existing_items_by_stt:
        new_words = []
        for stt in sorted(existing_items_by_stt.keys()):
            if learn_map.get(stt, "Y") == "Y":
                new_words.append(existing_items_by_stt[stt])
        if new_words:
            with open(lv0_preq, "w", encoding="utf-8") as f:
                json.dump({"words": new_words}, f, ensure_ascii=False, indent=2)
            return True

    return False

def handle_sel_command(ans):
    parts = ans.split()
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
            start_str = quiz_input("Nhập STT bắt đầu: ").strip()
            end_str = quiz_input("Nhập STT kết thúc: ").strip()
            start_num = int(start_str)
            end_num = int(end_str)
        except (ValueError, KeyboardInterrupt, EOFError):
            print(f"\n\033[91m⚠️ Lỗi: Khoảng STT không hợp lệ.\033[0m\n")
            return False

    if start_num is not None and end_num is not None:
        if start_num > end_num:
            start_num, end_num = end_num, start_num

        master_sessions = load_sessions()
        for s in master_sessions:
            if s.get("levels") == SELECTED_LEVELS:
                s["sel_range"] = [start_num, end_num]
        save_sessions(master_sessions)

        print(f"\n\033[92m✅ Đã chọn khoảng câu STT từ {start_num} đến {end_num} cho phiên học.\033[0m")
        print(f"\033[92m🔄 Tự động áp dụng khoảng câu mới cho phiên học!\033[0m\n")
        time.sleep(1.0)
        return True
    return False

def perform_reset_scores(user_dir, file_types, start_num=None, end_num=None):
    target_files = []
    if "scbn" in file_types:
        target_files.append(os.path.join(user_dir, "lv0", "scbn.md"))
    if "scbk" in file_types:
        target_files.append(os.path.join(user_dir, "lv0", "scbk.md"))

    for lv in range(1, 6):
        if "scwr" in file_types:
            target_files.append(os.path.join(user_dir, f"lv{lv}", "scwr.md"))
        if "scsp" in file_types:
            target_files.append(os.path.join(user_dir, f"lv{lv}", "scsp.md"))

    reset_count = 0
    updated_files = 0
    for filepath in target_files:
        if not os.path.exists(filepath):
            continue
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            new_lines = []
            file_updated = False
            is_sc0 = filepath.endswith("scbn.md") or filepath.endswith("scbk.md")

            for line in lines:
                stripped = line.strip()
                if stripped.startswith("|"):
                    cols = [c.replace(r"\|", "|").strip() for c in re.split(r'(?<!\\)\|', stripped)[1:-1]]
                    if cols and cols[0].isdigit():
                        stt = int(cols[0])
                        if start_num is not None and end_num is not None:
                            in_range = (start_num <= stt <= end_num)
                        else:
                            in_range = True

                        if in_range:
                            if is_sc0 and len(cols) >= 5:
                                name_val = cols[1].replace("|", r"\|")
                                eng_val = cols[2].replace("|", r"\|")
                                status_val = cols[4]
                                line = f"| {stt} | {name_val} | {eng_val} | 0 | {status_val} |\n"
                                file_updated = True
                                reset_count += 1
                            elif not is_sc0 and len(cols) >= 3:
                                word_val = cols[1].replace("|", r"\|")
                                line = f"| {stt} | {word_val} | 0 |\n"
                                file_updated = True
                                reset_count += 1
                new_lines.append(line)

            if file_updated:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
                updated_files += 1
        except Exception as e:
            print(f"\033[91m⚠️ Lỗi khi reset file {filepath}: {e}\033[0m")

    return updated_files, reset_count

def handle_reset_scores_command(ans):
    parts = ans.split()
    file_choice = None
    start_num = None
    end_num = None

    if len(parts) > 1:
        first_arg = parts[1].lower()
        if first_arg in ["scbn", "scbk", "scwr", "scsp", "all", "tatca", "tất cả"]:
            file_choice = "all" if first_arg in ["all", "tatca", "tất cả"] else first_arg
            if len(parts) >= 4 and parts[2].isdigit() and parts[3].isdigit():
                start_num = int(parts[2])
                end_num = int(parts[3])
        elif first_arg.isdigit() and len(parts) >= 3 and parts[2].isdigit():
            start_num = int(parts[1])
            end_num = int(parts[2])

    if not file_choice:
        print("\n⚡ [RESET ĐIỂM SỐ]")
        print("  1. scbn.md (Level 0 - Mode N: Tên)")
        print("  2. scbk.md (Level 0 - Mode K: STT)")
        print("  3. scwr.md (Level 1-5 - Mode W: Viết)")
        print("  4. scsp.md (Level 1-5 - Mode S: Nói)")
        print("  a. Tất cả các loại tiến độ (All files)")
        choice = quiz_input("Chọn loại tiến độ muốn reset (1-4 / a) <⭐a>: ").strip().lower()
        if choice in ["..", ".b"]:
            return False
        if choice == "1" or choice == "scbn":
            file_choice = "scbn"
        elif choice == "2" or choice == "scbk":
            file_choice = "scbk"
        elif choice == "3" or choice == "scwr":
            file_choice = "scwr"
        elif choice == "4" or choice == "scsp":
            file_choice = "scsp"
        else:
            file_choice = "all"

    if start_num is None:
        print("\n🎯 PHẠM VI RESET ĐIỂM:")
        print("  1. Tất cả các câu")
        print("  2. Theo khoảng câu STT (ví dụ: 1 đến 10)")
        scope = quiz_input("Chọn phạm vi (1-2) <⭐1>: ").strip().lower()
        if scope in ["..", ".b"]:
            return False
        if scope == "2":
            rng = quiz_input("Nhập khoảng STT (ví dụ: 1 10 hoặc 1-10): ").strip()
            rng_parts = re.findall(r'\d+', rng)
            if len(rng_parts) >= 2:
                start_num = int(rng_parts[0])
                end_num = int(rng_parts[1])
            else:
                print("⚠️ Nhập khoảng câu không hợp lệ. Hủy thao tác.")
                return False

    if start_num is not None and end_num is not None and start_num > end_num:
        start_num, end_num = end_num, start_num

    if file_choice == "all":
        file_types = ["scbn", "scbk", "scwr", "scsp"]
        type_str = "tất cả tệp tiến độ (scbn, scbk, scwr, scsp)"
    else:
        file_types = [file_choice]
        type_str = f"tệp {file_choice}.md"

    range_str = f"từ câu STT {start_num} đến {end_num}" if (start_num is not None and end_num is not None) else "tất cả các câu"

    confirm = quiz_input(f"\n⚠️  XÁC NHẬN: Reset điểm về 0 cho {type_str} ({range_str})? (y/N): ").strip().lower()
    if confirm in ["y", "yes", "c", "có"]:
        updated_files, reset_count = perform_reset_scores(USER_DIR, file_types, start_num, end_num)
        if updated_files > 0:
            print(f"\n\033[92m✅ Đã reset điểm về 0 thành công cho {reset_count} mục trong {updated_files} tệp!\033[0m\n")
            time.sleep(1.0)
            return True
        else:
            print("\n⚠️ Không tìm thấy dữ liệu tệp tiến độ phù hợp để reset.\n")
    else:
        print("\n❌ Đã hủy thao tác reset điểm.\n")
    return False

def clean_terminal_output(text):
    """
    Ensure 100% terminal compatibility by removing colorful emojis.
    Preserves keyboard-safe geometric shapes: ☆, ◇, •.
    """
    emoji_pattern = re.compile(
        u"[\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\u2702-\u27B0"           # dingbats
        u"\u24C2-\U0001F251"
        u"\u2600-\u26FF"           # misc symbols
        u"]+", flags=re.UNICODE
    )
    cleaned = emoji_pattern.sub("", text)
    cleaned = re.sub(r' +', ' ', cleaned).strip()
    return cleaned

def speak_sentence(sentence):
    """
    Pronounce the sentence using termux-tts-speak if available.
    """
    import subprocess
    clean_text = sentence.replace("**", "").replace("*", "").strip()
    if not clean_text:
        return
    try:
        subprocess.Popen(
            ["termux-tts-speak", "-l", "en-US", clean_text],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception:
        pass

def parse_answers(user_input, targets_list):
    """
    Parses user input into list of individual answers.
    Supports splitting by comma, semicolon, slash, vertical bar, or spaces.
    """
    if len(targets_list) <= 1:
        return [user_input.strip()]

    for sep in [",", ";", "/", "|"]:
        if sep in user_input:
            parts = [p.strip() for p in user_input.split(sep)]
            if len(parts) == len(targets_list):
                return parts

    space_parts = [p.strip() for p in user_input.split() if p.strip()]
    target_word_counts = [len(t.split()) for t in targets_list]
    if len(space_parts) == sum(target_word_counts):
        res = []
        curr = 0
        for count in target_word_counts:
            res.append(" ".join(space_parts[curr:curr+count]))
            curr += count
        return res

    if len(space_parts) == len(targets_list):
        return space_parts

    return space_parts

def copy_questions_from_other_users(target_dir, user_dir, username):
    """
    Scans for preq.json in other user directories or target_dir,
    and prompts the user to copy one to user_dir.
    Returns: bool (True if successfully copied, False otherwise)
    """
    import shutil
    import time

    options = []

    # 1. Check for shared preq.json (legacy fallback option)
    shared_json = os.path.join(target_dir, "preq.json")
    if os.path.exists(shared_json):
        options.append(("Shared (Dùng chung)", shared_json))

    # 2. Check for other user folders (subdirectories starting with '.' or '👤')
    ignored_folders = {".git", ".learning", ".learn", ".obsidian", ".agents", f".{username}", f"👤{username}", f"👤 {username}"}
    lvl_name = os.path.basename(user_dir) # e.g. 'lv1' or user folder name
    try:
        for item in os.listdir(target_dir):
            if (item.startswith(".") or item.startswith("👤")) and item not in ignored_folders:
                item_path = os.path.join(target_dir, item)
                if os.path.isdir(item_path):
                    # Try current level json first
                    other_lvl_json = os.path.join(item_path, lvl_name, "preq.json")
                    if os.path.exists(other_lvl_json):
                        other_user = item[1:].strip()
                        options.append((f"User '{other_user}' ({lvl_name.upper()})", other_lvl_json))
                        continue

                    # Try root json second
                    other_root_json = os.path.join(item_path, "preq.json")
                    if os.path.exists(other_root_json):
                        other_user = item[1:].strip()
                        options.append((f"User '{other_user}' (Root)", other_root_json))
                        continue

                    # Try other levels as fallback
                    for idx in range(0, 6):
                        fallback_json = os.path.join(item_path, f"lv{idx}", "preq.json")
                        if os.path.exists(fallback_json):
                            other_user = item[1:].strip()
                            options.append((f"User '{other_user}' (LV{idx})", fallback_json))
                            break
    except Exception:
        pass

    if not options:
        return False

    # Prompt the user
    print(f"\n\033[93m⚠️ Cảnh báo: Không tìm thấy preq.json cho user '{username}'.\033[0m")
    print("Phát hiện các nguồn dữ liệu câu hỏi khác trong bài học này:")
    for idx, (label, _) in enumerate(options, 1):
        print(f"  [{idx}] {label}")
    print("  [q] Thoát")

    while True:
        try:
            choice = quiz_input(f"Chọn nguồn để sao chép preq.json sang user '{username}' (1-{len(options)} hoặc 'q'): ").strip().lower()
        except KeyboardInterrupt:
            print("\n👋 Tạm biệt!")
            sys.exit(0)

        if choice == 'q':
            sys.exit(0)
        elif choice.isdigit():
            sel = int(choice)
            if 1 <= sel <= len(options):
                source_label, source_path = options[sel - 1]
                target_path = os.path.join(user_dir, "preq.json")
                try:
                    shutil.copy(source_path, target_path)
                    print(f"\033[92m✅ Đã sao chép preq.json thành công từ {source_label}!\033[0m")
                    time.sleep(1)
                    return True
                except Exception as e:
                    print(f"\033[91m⚠️ Lỗi khi sao chép file: {e}\033[0m")
                    return False
            else:
                print(f"⚠️ Vui lòng nhập số từ 1 đến {len(options)}.")
        else:
            print("⚠️ Nhập không hợp lệ.")

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

def resolve_username(target_dir, cache_file, ignore_cache=False):
    while True:
        # 1. Global cache (last used username)
        cached_user = get_cached_username(cache_file) if not ignore_cache else None
        if cached_user:
            return cached_user

        # 2. Detect from lesson folder
        detected_users = []
        ignored_folders = {".git", ".learning", ".learn", ".obsidian", ".agents"}
        if os.path.exists(target_dir):
            try:
                for item in os.listdir(target_dir):
                    if (item.startswith(".") or item.startswith("👤")) and item not in ignored_folders:
                        item_path = os.path.join(target_dir, item)
                        if os.path.isdir(item_path):
                            has_questions = False
                            for idx in range(0, 6):
                                if os.path.exists(os.path.join(item_path, f"lv{idx}", "preq.json")):
                                    has_questions = True
                                    break
                            if has_questions:
                                user_name = item[1:].strip() # strip leading dot or emoji
                                if user_name not in detected_users:
                                    detected_users.append(user_name)
            except Exception:
                pass

        # 3. Prompt user to choose or input
        print("\n👤 [THIẾT LẬP USER]")
        if detected_users:
            print("Phát hiện các user trong bài học này:")
            for idx, u in enumerate(detected_users, 1):
                suffix = " <⭐>" if idx == 1 else ""
                print(f"  [{idx}] {u}{suffix}")
            print("  [n] Tạo user mới")

            reload_step = False
            while True:
                try:
                    choice = input("Chọn số thứ tự <⭐1> hoặc nhập 'n': ").strip().lower()
                except KeyboardInterrupt:
                    print("\n👋 Tạm biệt!")
                    sys.exit(0)

                if choice == ".r":
                    os.system('clear' if os.name != 'nt' else 'cls')
                    print("🔄 Đang khởi động lại quiz.py...")
                    time.sleep(0.5)
                    os.execv(sys.executable, [sys.executable] + sys.argv)
                elif choice == ".r.":
                    reload_step = True
                    break
                elif choice == ".q":
                    print("\n👋 Tạm biệt!")
                    sys.exit(0)
                elif choice == "":
                    user = detected_users[0]
                    save_cached_username(cache_file, user)
                    return user
                elif choice == 'n':
                    break
                elif choice.isdigit():
                    sel = int(choice)
                    if 1 <= sel <= len(detected_users):
                        user = detected_users[sel - 1]
                        save_cached_username(cache_file, user)
                        return user
                print("⚠️ Nhập không hợp lệ.")

            if reload_step:
                os.system('clear' if os.name != 'nt' else 'cls')
                continue

        # Input new username
        reload_step = False
        while True:
            try:
                new_user = input("Nhập tên viết tắt hoặc nickname của bạn (ví dụ: qtu): ").strip()
            except KeyboardInterrupt:
                print("\n👋 Tạm biệt!")
                sys.exit(0)

            if new_user.lower() == ".r":
                os.system('clear' if os.name != 'nt' else 'cls')
                print("🔄 Đang khởi động lại quiz.py...")
                time.sleep(0.5)
                os.execv(sys.executable, [sys.executable] + sys.argv)
            elif new_user.lower() == ".r.":
                reload_step = True
                break
            elif new_user.lower() == ".q":
                print("\n👋 Tạm biệt!")
                sys.exit(0)

            username = "".join(c for c in new_user if c.isalnum() or c in ('-', '_')).strip()
            if username:
                save_cached_username(cache_file, username)
                return username
            print("⚠️ Tên user không hợp lệ. Vui lòng nhập lại.")

        if reload_step:
            os.system('clear' if os.name != 'nt' else 'cls')
            continue

def auto_partition_questions_and_progress(user_dir):
    """
    If level preq.json files do not exist, partitions the main preq.json
    into lv1-lv5 folders.
    """
    main_json = os.path.join(user_dir, "preq.json")
    if not os.path.exists(main_json):
        return

    try:
        with open(main_json, "r", encoding="utf-8") as f:
            main_data = json.load(f)
    except Exception:
        return

    words_db = main_data.get("words", [])

    # Load voca groups to know which words belong to which level
    voca_groups = {1: set(), 2: set(), 3: set(), 4: set(), 5: set()}
    for idx in range(1, 6):
        voca_path = os.path.join(user_dir, f"lv{idx}", "preg.json")
        if os.path.exists(voca_path):
            try:
                with open(voca_path, "r", encoding="utf-8") as f:
                    v_list = json.load(f)
                voca_groups[idx] = {w["word"].lower() for w in v_list}
            except Exception:
                pass

    # Partition words_db
    partitioned_words = {1: [], 2: [], 3: [], 4: [], 5: []}
    for q in words_db:
        w_name = q["word"].lower()
        matched_lv = None
        for idx in range(1, 6):
            if w_name in voca_groups[idx]:
                matched_lv = idx
                break
        if matched_lv is None:
            # Fallback by word count
            word_count = len(q["word"].split())
            if word_count == 1:
                matched_lv = 1
            elif word_count == 2:
                matched_lv = 2
            elif word_count == 3:
                matched_lv = 3
            else:
                matched_lv = 4
        partitioned_words[matched_lv].append(q)

    # Write partitioned preq.json to each level
    for idx in range(1, 6):
        lv_dir = os.path.join(user_dir, f"lv{idx}")
        os.makedirs(lv_dir, exist_ok=True)
        lv_json_path = os.path.join(lv_dir, "preq.json")
        if not os.path.exists(lv_json_path):
            lv_data = {
                "words": partitioned_words[idx]
            }
            with open(lv_json_path, "w", encoding="utf-8") as f:
                json.dump(lv_data, f, ensure_ascii=False, indent=2)

def handle_audio_shortcut(cmd, targets_list, original_sentence):
    if cmd.startswith(".w"):
        times = 3
        if len(cmd) > 2:
            num_part = cmd[2:]
            if num_part.isdigit() and int(num_part) > 0:
                times = int(num_part)
            else:
                print("⚠️ Lệnh phát âm không hợp lệ. Ví dụ: .w hoặc .w3\n")
                return True
        for t_idx, target in enumerate(targets_list):
            clean_target = target.replace("**", "").strip()
            print(f"🗣️  Đang đọc từ '{clean_target}' {times} lần...")
            for i in range(times):
                speak_sentence(clean_target)
                if i < times - 1:
                    time.sleep(1.5)
            if t_idx < len(targets_list) - 1:
                time.sleep(1.0)
        print()
        return True
    elif cmd.startswith(".p"):
        times = 3
        if len(cmd) > 2:
            num_part = cmd[2:]
            if num_part.isdigit() and int(num_part) > 0:
                times = int(num_part)
            else:
                print("⚠️ Lệnh phát âm không hợp lệ. Ví dụ: .p hoặc .p3\n")
                return True
        targets_str = ", ".join(targets_list)
        print(f"🗣️  Đang đọc cụm từ '{targets_str}' {times} lần...")
        for i in range(times):
            speak_sentence(targets_str)
            if i < times - 1:
                time.sleep(1.5)
        print()
        return True
    elif cmd.startswith(".s"):
        times = 3
        if len(cmd) > 2:
            num_part = cmd[2:]
            if num_part.isdigit() and int(num_part) > 0:
                times = int(num_part)
            else:
                print("⚠️ Lệnh phát âm không hợp lệ. Ví dụ: .s hoặc .s3\n")
                return True
        print(f"🗣️  Đang đọc cả câu {times} lần...")
        for i in range(times):
            speak_sentence(original_sentence)
            if i < times - 1:
                time.sleep(2.0)
        print()
        return True
    return False

def visual_ljust(s, width):
    """
    Left-justifies a string, counting wide emojis as 2 cells and standard characters as 1.
    Ignores Unicode variation selectors like \ufe0f.
    """
    visual_len = 0
    for char in s:
        if char == '\ufe0f':
            continue
        if ord(char) >= 0x2300: # Emojis, geometric shapes, wide symbols
            visual_len += 2
        else:
            visual_len += 1
    pad_needed = max(0, width - visual_len)
    return s + " " * pad_needed

def visual_center(s, width, fillchar='-'):
    """
    Centers a string, counting wide emojis as 2 cells and standard characters as 1.
    Ignores Unicode variation selectors like \ufe0f.
    """
    visual_len = 0
    for char in s:
        if char == '\ufe0f':
            continue
        if ord(char) >= 0x2300: # Emojis, geometric shapes, wide symbols
            visual_len += 2
        else:
            visual_len += 1
    total_pad = max(0, width - visual_len)
    left_pad = total_pad // 2
    right_pad = total_pad - left_pad
    return fillchar * left_pad + s + fillchar * right_pad

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
    ".r": {"cmd": ".r", "desc": "Khởi động lại ứng dụng (Reload Code)"},
    ".r.": {"cmd": ".r.", "desc": "Làm lại bài từ câu CH 1"},
    ".r._level": {"cmd": ".r.", "desc": "Tải lại trang chọn cấp độ học"},
    ".m": {"cmd": ".m", "desc": "Tắt/Bật phát âm tự động (Mute/Unmute)"},
    ".w / .wn": {"cmd": ".w / .wn", "desc": "Đọc từng từ đáp án 3 / n lần"},
    ".p / .pn": {"cmd": ".p / .pn", "desc": "Đọc ghép cụm đáp án 3 / n lần"},
    ".s / .sn": {"cmd": ".s / .sn", "desc": "Đọc cả câu 3 / n lần"},
    ".": {"cmd": ".", "desc": "Làm lại câu hỏi hiện tại"},
    ".h": {"cmd": ".h", "desc": "Xem hướng dẫn phím tắt này"},
    ".sel": {"cmd": ".sel [start] [end]", "desc": "Chọn khoảng câu để học Level 0 (ví dụ: .sel 1 10)"},
    ".reset": {"cmd": ".reset / rst", "desc": "Reset điểm số về 0 (chọn tệp scbn/scbk/scwr/scsp hoặc khoảng câu)"},
    "rx": {"cmd": "rx", "desc": "Xóa phiên học số x (ví dụ: r1)"},
    "ux": {"cmd": "ux", "desc": "Cập nhật phiên học số x (ví dụ: u1)"},
    "stt": {"cmd": "[STT]", "desc": "Chọn phiên học cũ theo số thứ tự hoặc 'n' tạo mới"},
    "space_hint": {"cmd": "[Space] / ?", "desc": "Xem gợi ý đáp án (không cộng điểm)"},
    "enter_next": {"cmd": "[Enter]", "desc": "Tiếp tục qua câu hỏi mới"}
}

CONTEXTS_MAP = {
    "session_select": ["stt", "rx", "ux", "...", ".sel", ".reset", ".b_to_level", ".._to_level", ".q", ".h"],
    "level_select": [".b_to_user", ".._to_user", ".q", ".r", ".r._level", ".h"],
    "quiz_input": ["space_hint", ".", "..", "...", ".b", ".m", ".r", ".r.", ".q", ".h"],
    "quiz_pause": ["enter_next", ".", "..", "...", ".b", ".m", ".w / .wn", ".p / .pn", ".s / .sn", ".r", ".r.", ".q", ".h"]
}

def print_shortcuts_guide(context="quiz_input"):
    if context not in CONTEXTS_MAP:
        return
    print("\n\033[90m💡 Phím tắt khả dụng:")
    keys = CONTEXTS_MAP[context]
    cmds = [SHORTCUTS_DB[k]["cmd"] for k in keys if k in SHORTCUTS_DB]
    max_cmd_len = max(len(c) for c in cmds) if cmds else 12

    for key in keys:
        if key in SHORTCUTS_DB:
            item = SHORTCUTS_DB[key]
            cmd_formatted = f"  {item['cmd']:<{max_cmd_len}}"
            print(f"{cmd_formatted} : {item['desc']}")
    print("--------------------------------------------------\033[0m\n")

def parse_levels(choice):
    """
    Parses a string representing level choices (e.g. 0, 1, 1,2, 1-3)
    and returns a sorted list of unique level integers, or None if invalid.
    """
    choice = choice.strip().lower()
    if choice == "":
        return None
    if choice in ["all", "t", "th", "tong hop", "tổng hợp"]:
        return [1, 2, 3, 4, 5]
    if choice == "0":
        return [0]
    if choice == "1":
        return [1]

    parts = []
    if "-" in choice:
        match_range = re.match(r'^([0-5])-([0-5])$', choice)
        if match_range:
            start_lv = int(match_range.group(1))
            end_lv = int(match_range.group(2))
            parts = list(range(min(start_lv, end_lv), max(start_lv, end_lv) + 1))
    else:
        parts_str = re.split(r'[\s,]+', choice)
        try:
            parts = [int(p) for p in parts_str if p.isdigit()]
        except Exception:
            pass

    valid_parts = [p for p in parts if 0 <= p <= 5]
    if valid_parts:
        return sorted(list(set(valid_parts)))
    return None

def restart_quiz():
    user_arg = []
    if 'USER_DIR' in globals() and USER_DIR:
        username = os.path.basename(USER_DIR).replace("👤", "").strip()
        user_arg = ["--user", username]

    level_arg = []
    if 'SELECTED_LEVELS' in globals() and SELECTED_LEVELS:
        level_arg = ["--levels", ",".join(map(str, SELECTED_LEVELS))]

    clean_argv = []
    skip = 0
    for idx, arg in enumerate(sys.argv):
        if skip > 0:
            skip -= 1
            continue
        if arg in ["--user", "--levels"]:
            skip = 1
            continue
        clean_argv.append(arg)

    os.system('clear' if os.name != 'nt' else 'cls')
    print("🔄 Đang khởi động lại quiz.py...")
    time.sleep(0.5)
    os.execv(sys.executable, [sys.executable] + clean_argv + user_arg + level_arg)

def resolve_paths():
    """
    Resolves the paths for bold.md, preq.json, scwr.md, scsp.md, and sess-quiz.json.
    Supports multi-user and multi-level (lv1 to lv5) folder structures, including combinations.
    """
    global USER_DIR, SELECTED_LEVELS, LESSON_DIR
    target_dir = os.getcwd()

    passed_user = None
    passed_levels = None
    if "--user" in sys.argv:
        u_idx = sys.argv.index("--user")
        if u_idx + 1 < len(sys.argv):
            passed_user = sys.argv[u_idx + 1]
    if "--levels" in sys.argv:
        l_idx = sys.argv.index("--levels")
        if l_idx + 1 < len(sys.argv):
            passed_levels = sys.argv[l_idx + 1]

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if not arg.startswith("-"):
            if os.path.isdir(arg):
                target_dir = os.path.abspath(arg)
            elif os.path.isfile(arg):
                if arg.endswith(".json"):
                    target_dir = os.path.dirname(os.path.abspath(arg))

    script_dir = os.path.dirname(os.path.abspath(__file__))
    cache_file = os.path.join(script_dir, "user-cache.json")

    # 1. Check if target_dir is already a level directory (e.g. CLI direct execution)
    is_lv_dir = False
    lvl = "lv1"
    last_folder = os.path.basename(target_dir)
    if last_folder in ["lv0", "lv1", "lv2", "lv3", "lv4", "lv5"]:
        is_lv_dir = True
        lvl = last_folder
        SELECTED_LEVELS = [int(lvl[2])]
        user_dir = os.path.dirname(target_dir)
        lesson_dir = os.path.dirname(user_dir)
        username = os.path.basename(user_dir)
        if username.startswith("👤") or username.startswith("."):
            username = username[1:].strip()
        USER_DIR = user_dir
        LESSON_DIR = lesson_dir
        migrate_legacy_json_files(lesson_dir, user_dir)
    else:
        lesson_dir = target_dir
        LESSON_DIR = lesson_dir
        ignore_cache = False
        while True:
            if passed_user:
                username = passed_user
            else:
                username = resolve_username(lesson_dir, cache_file, ignore_cache=ignore_cache)

            legacy_dir = os.path.join(lesson_dir, f".{username}")
            legacy_dir2 = os.path.join(lesson_dir, f"👤{username}")
            user_dir = os.path.join(lesson_dir, f"👤 {username}")
            if os.path.isdir(legacy_dir) and not os.path.exists(user_dir):
                try:
                    os.rename(legacy_dir, user_dir)
                    print(f"\033[92m🔄 Đã di chuyển dữ liệu cũ từ {legacy_dir} sang {user_dir} để tương thích với Obsidian!\033[0m")
                    time.sleep(1.5)
                except Exception:
                    user_dir = legacy_dir
            if os.path.isdir(legacy_dir2) and not os.path.exists(user_dir):
                try:
                    os.rename(legacy_dir2, user_dir)
                    print(f"\033[92m🔄 Đã thêm dấu cách vào tên thư mục của học viên: {legacy_dir2} -> {user_dir}\033[0m")
                    time.sleep(1.5)
                except Exception:
                    pass
            os.makedirs(user_dir, exist_ok=True)
            USER_DIR = user_dir

            migrate_legacy_json_files(lesson_dir, user_dir)

            # Partition preq.json to levels if not already done
            auto_partition_questions_and_progress(user_dir)

            # Prompt user to select level
            if passed_levels:
                selected_lvs = [int(x) for x in passed_levels.split(",") if x.isdigit()]
                break
            else:
                print("\n⚡ [CHỌN CẤP ĐỘ HỌC]")
                print("  0. Cấp độ 0 (Nhớ câu/Name - Mode N)")
                print("  1. Cấp độ 1 (Từ đơn)")
                print("  2. Cấp độ 2 (Cụm 2 từ)")
                print("  3. Cấp độ 3 (Cụm 3 từ)")
                print("  4. Cấp độ 4 (Cụm 4 từ trở lên)")
                print("  5. Cấp độ 5 (Ôn tập tự soạn)")
                print("  t. Tổng hợp cấp độ 1-5")
                print("  (Có thể chọn danh sách ví dụ: 1,2 hoặc dải ví dụ: 1-3)")

                level_back = False
                level_reload = False
                while True:
                    try:
                        choice = input("Chọn cấp độ học <⭐1>: ").strip()
                    except KeyboardInterrupt:
                        print("\n👋 Tạm biệt!")
                        sys.exit(0)

                    if choice.lower() == ".q":
                        print("\n👋 Tạm biệt!")
                        sys.exit(0)
                    if choice.lower() == "..":
                        level_back = True
                        break
                    if choice.lower() == ".r.":
                        level_reload = True
                        break
                    if choice.lower() == ".h":
                        print_shortcuts_guide("level_select")
                        continue
                    if choice.lower() == ".r":
                        os.system('clear' if os.name != 'nt' else 'cls')
                        print("🔄 Đang khởi động lại quiz.py...")
                        time.sleep(0.5)
                        os.execv(sys.executable, [sys.executable] + sys.argv)

                    if choice == "":
                        selected_lvs = [1]
                        break

                    parsed = parse_levels(choice)
                    if parsed is not None:
                        selected_lvs = parsed
                        break

                    print("⚠️ Nhập không hợp lệ. Vui lòng chọn số (0-5), danh sách (ví dụ: 1,2), hoặc dải (ví dụ: 1-3).")

                if level_back:
                    ignore_cache = True
                    os.system('clear' if os.name != 'nt' else 'cls')
                    continue
                elif level_reload:
                    os.system('clear' if os.name != 'nt' else 'cls')
                    continue
                else:
                    break

        SELECTED_LEVELS = selected_lvs

    # Ensure preq.json exists for each selected level
    for lv in SELECTED_LEVELS:
        lvl_dir = os.path.join(user_dir, f"lv{lv}")
        os.makedirs(lvl_dir, exist_ok=True)
        lv_json = os.path.join(lvl_dir, "preq.json")
        if not os.path.exists(lv_json):
            copied = copy_questions_from_other_users(lesson_dir, lvl_dir, username)
            if not copied:
                print(f"Error: preq.json not found in level directory: {lvl_dir}")
                sys.exit(1)

    # Delete legacy scbn.md in lv1 to lv5
    for lv in range(1, 6):
        legacy_scbn = os.path.join(user_dir, f"lv{lv}", "scbn.md")
        if os.path.exists(legacy_scbn):
            try:
                os.remove(legacy_scbn)
            except Exception:
                pass

    # Determine files to resolve
    sessions_file = os.path.join(user_dir, "sess-quiz.json")
    legacy_sess_file = os.path.join(user_dir, "sess.json")
    if os.path.exists(legacy_sess_file) and not os.path.exists(sessions_file):
        try:
            os.rename(legacy_sess_file, sessions_file)
        except Exception:
            pass
    if len(SELECTED_LEVELS) == 1:
        lvl_dir = os.path.join(user_dir, f"lv{SELECTED_LEVELS[0]}")
        os.makedirs(lvl_dir, exist_ok=True)
        lesson_file = os.path.join(lvl_dir, "bold.md")
        if not os.path.exists(lesson_file):
            target_md_files = [f for f in os.listdir(lesson_dir) if f.endswith(".md") and not f.startswith(".") and f not in {"scwr.md", "scsp.md"} and os.path.isfile(os.path.join(lesson_dir, f))] if os.path.exists(lesson_dir) else []
            lesson_file = os.path.join(lesson_dir, target_md_files[0]) if target_md_files else ""
    else:
        # Combined levels
        target_md_files = [f for f in os.listdir(lesson_dir) if f.endswith(".md") and not f.startswith(".") and f not in {"scwr.md", "scsp.md"} and os.path.isfile(os.path.join(lesson_dir, f))] if os.path.exists(lesson_dir) else []
        lesson_file = os.path.join(lesson_dir, target_md_files[0]) if target_md_files else ""

    # Sentinel files (not used directly when in global mode, but resolved for compat)
    json_file = ""
    w_md_file = ""
    s_md_file = ""

    return lesson_file, json_file, w_md_file, s_md_file, sessions_file


def load_all_scores():
    """
    Loads scores for W, S, and N from scwr.md, scsp.md, and scbn.md across all selected levels.
    """
    scores = {}

    def parse_md_table(file_path):
        word_scores = {}
        if os.path.exists(file_path):
            is_scbn = file_path.endswith("scbn.md") or file_path.endswith("scbk.md")
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for line in lines:
                if line.strip().startswith("|"):
                    cols = [c.replace(r"\|", "|").strip() for c in re.split(r'(?<!\\)\|', line.strip())[1:-1]]
                    if cols and cols[0].isdigit():
                        stt = int(cols[0])
                        if is_scbn:
                            if len(cols) >= 4:
                                word = cols[2].replace("**", "").strip()
                                try:
                                    score = int(cols[3])
                                except ValueError as e:
                                    print(f"\nDEBUG - file_path: {file_path}")
                                    print(f"DEBUG - line: {repr(line)}")
                                    print(f"DEBUG - cols: {cols}")
                                    raise e
                                word_scores[word] = (score, stt)
                        else:
                            word = cols[1].replace("**", "").strip()
                            score = int(cols[2])
                            word_scores[word] = (score, stt)
        return word_scores

    for lv in SELECTED_LEVELS:
        lvl_w = os.path.join(USER_DIR, f"lv{lv}", "scwr.md")
        lvl_s = os.path.join(USER_DIR, f"lv{lv}", "scsp.md")
        lvl_n = os.path.join(USER_DIR, f"lv{lv}", "scbn.md")
        lvl_k = os.path.join(USER_DIR, f"lv{lv}", "scbk.md")

        w_scores = parse_md_table(lvl_w)
        s_scores = parse_md_table(lvl_s)
        n_scores = parse_md_table(lvl_n)
        k_scores = parse_md_table(lvl_k)

        # Keep only words that belong to this level's questions
        lv_json = os.path.join(USER_DIR, f"lv{lv}", "preq.json")
        valid_words = set()
        if os.path.exists(lv_json):
            try:
                with open(lv_json, "r", encoding="utf-8") as f:
                    lv_data = json.load(f)
                valid_words = {w["word"] for w in lv_data.get("words", [])}
            except Exception:
                pass

        if w_scores or s_scores or n_scores or k_scores:
            all_words = set(w_scores.keys()).union(s_scores.keys()).union(n_scores.keys()).union(k_scores.keys())
            for word in all_words:
                if not valid_words or word in valid_words:
                    w_val, w_stt = w_scores.get(word, (0, 999))
                    s_val, s_stt = s_scores.get(word, (0, 999))
                    n_val, n_stt = n_scores.get(word, (0, 999))
                    k_val, k_stt = k_scores.get(word, (0, 999))
                    stt = w_stt if w_stt != 999 else (s_stt if s_stt != 999 else (n_stt if n_stt != 999 else k_stt))
                    scores[word] = [w_val, s_val, n_val, k_val, stt]

    # Fallback to parse from lesson.md (legacy progress table) if scores is empty
    if not scores and LESSON_FILE and os.path.exists(LESSON_FILE):
        try:
            with open(LESSON_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for line in lines:
                if line.strip().startswith("|"):
                    cols = [c.replace(r"\|", "|").strip() for c in re.split(r'(?<!\\)\|', line.strip())[1:-1]]
                    if cols and cols[0].isdigit() and len(cols) >= 4:
                        stt = int(cols[0])
                        word = cols[1].replace("**", "").strip()
                        w_score = int(cols[2])
                        s_score = int(cols[3])
                        scores[word] = [w_score, s_score, 0, 0, stt]
        except Exception:
            pass

    # Initialize scorecards if we parsed legacy scores
    if scores and not any(os.path.exists(os.path.join(USER_DIR, f"lv{lv}", "scwr.md")) for lv in SELECTED_LEVELS):
        save_all_scores(scores)

    return scores

def save_all_scores(scores):
    """
    Saves scores back to scwr.md, scsp.md, and scbn.md partitioned by level.
    """
    lv_words_map = {}
    for lv in SELECTED_LEVELS:
        lv_json = os.path.join(USER_DIR, f"lv{lv}", "preq.json")
        if os.path.exists(lv_json):
            try:
                with open(lv_json, "r", encoding="utf-8") as f:
                    lv_data = json.load(f)
                lv_words_map[lv] = {w["word"] for w in lv_data.get("words", [])}
            except Exception:
                lv_words_map[lv] = set()
        else:
            lv_words_map[lv] = set()

    # Partition the input scores into levels
    partitioned_scores = {lv: {} for lv in SELECTED_LEVELS}
    for word, val in scores.items():
        matched_lv = None
        for lv in SELECTED_LEVELS:
            if word in lv_words_map[lv]:
                matched_lv = lv
                break
        if matched_lv is None:
            matched_lv = SELECTED_LEVELS[0]
        partitioned_scores[matched_lv][word] = val

    # Write scwr.md, scsp.md, and scbn.md for each level
    for lv in SELECTED_LEVELS:
        lv_scores = partitioned_scores[lv]
        if not lv_scores:
            continue

        if lv == 0:
            for filename, score_idx, mode_name in [("scbn.md", 2, "Tên (Name)"), ("scbk.md", 3, "STT (Key)")]:
                lvl_f = os.path.join(USER_DIR, "lv0", filename)
                os.makedirs(os.path.dirname(lvl_f), exist_ok=True)

                # Read existing learn status if it exists
                existing_learn = {}
                if os.path.exists(lvl_f):
                    try:
                        with open(lvl_f, "r", encoding="utf-8") as f_in:
                            for line in f_in:
                                if line.strip().startswith("|"):
                                    cols = [c.replace(r"\|", "|").strip() for c in re.split(r'(?<!\\)\|', line.strip())[1:-1]]
                                    if cols and cols[0].isdigit():
                                        stt = int(cols[0])
                                        if len(cols) >= 5:
                                            existing_learn[stt] = cols[4]
                    except Exception:
                        pass

                # Read lv0/preq.json to map English sentences to their STT and Name
                word_details = {}
                lv0_json = os.path.join(USER_DIR, "lv0", "preq.json")
                if os.path.exists(lv0_json):
                    try:
                        with open(lv0_json, "r", encoding="utf-8") as f:
                            lv_data = json.load(f)
                        for q in lv_data.get("words", []):
                            word_details[q["word"]] = {
                                "stt": q.get("sentence_no", 999),
                                "name": q.get("name") or "",
                                "english": q.get("sentence_original") or q["word"]
                            }
                            # clean english sentence_original if it starts with "🛫 " or "1. "
                            eng = word_details[q["word"]]["english"]
                            eng = re.sub(r'^\d+\.\s*(🛫\s*)?', '', eng).strip()
                            word_details[q["word"]]["english"] = eng
                    except Exception:
                        pass

                # Sort items by STT
                sorted_items = sorted(
                    lv_scores.items(),
                    key=lambda x: word_details.get(x[0], {}).get("stt", 999)
                )

                with open(lvl_f, "w", encoding="utf-8") as f:
                    f.write(f"## 📊 Tiến độ học theo {mode_name}\n\n")
                    f.write("| STT | NAME | ENGLISH | SCORE | LEARN |\n")
                    f.write("| :---: | :--- | :--- | :---: | :---: |\n")
                    for idx, (word, val) in enumerate(sorted_items, 1):
                        details = word_details.get(word, {})
                        stt_val = details.get("stt", idx)
                        name_val = details.get("name", "").replace("|", r"\|")
                        eng_val = details.get("english", word).replace("|", r"\|")
                        score_val = val[score_idx] if len(val) > score_idx else 0
                        status_val = existing_learn.get(stt_val, "Y")
                        f.write(f"| {stt_val} | {name_val} | {eng_val} | {score_val} | {status_val} |\n")
        else:
            lvl_w = os.path.join(USER_DIR, f"lv{lv}", "scwr.md")
            lvl_s = os.path.join(USER_DIR, f"lv{lv}", "scsp.md")
            os.makedirs(os.path.dirname(lvl_w), exist_ok=True)

            sorted_items = sorted(lv_scores.items(), key=lambda x: x[1][-1] if x[1] else 999)

            with open(lvl_w, "w", encoding="utf-8") as f:
                f.write("## 📊 Tiến độ học Viết (Writing)\n\n")
                f.write("| STT | WORDS | SCORE |\n")
                f.write("| :---: | :--- | :---: |\n")
                for idx, (word, val) in enumerate(sorted_items, 1):
                    f.write(f"| {idx} | {word} | {val[0]} |\n")

            with open(lvl_s, "w", encoding="utf-8") as f:
                f.write("## 📊 Tiến độ học Nói (Speaking)\n\n")
                f.write("| STT | WORDS | SCORE |\n")
                f.write("| :---: | :--- | :---: |\n")
                for idx, (word, val) in enumerate(sorted_items, 1):
                    f.write(f"| {idx} | {word} | {val[1]} |\n")

    print("\n\033[90m--------------------------------------------------")
    print("💾 Đã đồng bộ tiến độ học tập thành công!")
    print("--------------------------------------------------\033[0m")

def print_progress_table(scores_db, mode):
    sorted_scores = sorted(scores_db.items(), key=lambda x: x[1][-1] if x[1] else 999)
    if mode == "W":
        mode_index = 0
    elif mode == "S":
        mode_index = 1
    elif mode == "N":
        mode_index = 2
    else:
        mode_index = 3
    max_score = max(val[mode_index] if len(val) > mode_index else 0 for val in scores_db.values()) if scores_db else 0
    print("\033[90m------------------- [TIẾN ĐỘ] --------------------")
    print(f"{'STT':<5} {'TỪ VỰNG':<20} {'ĐIỂM':<6} {'TT':<3}")
    for idx, (word, val) in enumerate(sorted_scores, 1):
        score = val[mode_index] if len(val) > mode_index else 0
        status = "*" if score < max_score else ""
        print(f"{idx:<5} {word:<20} {score:<6} {status:<3}")
    print("--------------------------------------------------\033[0m\n")

def sort_words(words, priority_mode, scores_db, mode_index):
    if priority_mode == 1:
        words.sort(key=lambda x: x.get("stt", 0))
    elif priority_mode == 2:
        words.sort(key=lambda x: x.get("stt", 0), reverse=True)
    elif priority_mode == 3 or priority_mode == 7:
        words.sort(key=lambda x: scores_db.get(x["word"], [0,0,0,0,0])[mode_index])
    elif priority_mode == 4 or priority_mode == 8:
        words.sort(key=lambda x: scores_db.get(x["word"], [0,0,0,0,0])[mode_index], reverse=True)
    elif priority_mode == 5:
        words.sort(key=lambda x: len(x["word"]), reverse=True)
    elif priority_mode == 6:
        words.sort(key=lambda x: len(x["word"]))
    elif priority_mode == 9:
        random.shuffle(words)
    return words

PRIORITY_NAMES = {
    1: "Thứ tự bài học tăng dần",
    2: "Thứ tự bài học giảm dần",
    3: "Ưu tiên từ thấp điểm",
    4: "Ưu tiên từ cao điểm",
    5: "Ưu tiên từ dài",
    6: "Ưu tiên từ ngắn",
    7: "Ưu tiên từ dễ",
    8: "Ưu tiên từ khó",
    9: "Ngẫu nhiên"
}

def load_sessions():
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                sessions_list = []
                if isinstance(data, list):
                    sessions_list = data
                elif isinstance(data, dict):
                    sessions_list = [data]

                normalized = []
                for s in sessions_list:
                    # Normalize legacy keys and values (Writing -> W, Speaking -> S)
                    inp_mode = s.get("input_mode", s.get("input-mode", s.get("mode", "W")))
                    if inp_mode == "Writing":
                        inp_mode = "W"
                    elif inp_mode == "Speaking":
                        inp_mode = "S"

                    pri_mode = s.get("priority_mode", s.get("priority-mode", 3))
                    last_dt = s.get("last_datetime", "")

                    s_normalized = {
                        "input_mode": inp_mode,
                        "priority_mode": pri_mode,
                        "last_datetime": last_dt,
                        "levels": s.get("levels", [1])
                    }
                    if "target_level" in s:
                        s_normalized["target_level"] = s["target_level"]
                    if "mute" in s:
                        s_normalized["mute"] = s["mute"]
                    if "sel_range" in s:
                        s_normalized["sel_range"] = s["sel_range"]
                    normalized.append(s_normalized)
                return normalized
        except:
            pass
    return []

def save_sessions(sessions):
    if SESSIONS_FILE:
        os.makedirs(os.path.dirname(os.path.abspath(SESSIONS_FILE)), exist_ok=True)
    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)

def ensure_lesson_id_and_reference(lesson_file, json_file, lesson_data):
    """
    Ensures that the lesson .md file has an 'id' in its YAML frontmatter.
    Then ensures that all questions in json_file (lesson_data) have a 'lid' key pointing to this id.
    """
    if not lesson_file or not os.path.exists(lesson_file):
        return False

    try:
        with open(lesson_file, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return False

    has_frontmatter = False
    lines = content.splitlines()
    frontmatter_lines = []
    content_lines = []

    if len(lines) > 1 and lines[0].strip() == "---":
        closing_idx = -1
        for idx in range(1, len(lines)):
            if lines[idx].strip() == "---":
                closing_idx = idx
                break
        if closing_idx != -1:
            has_frontmatter = True
            frontmatter_lines = lines[1:closing_idx]
            content_lines = lines[closing_idx+1:]

    frontmatter_dict = {}
    if has_frontmatter:
        for line in frontmatter_lines:
            if ":" in line:
                k, v = line.split(":", 1)
                frontmatter_dict[k.strip()] = v.strip().strip('"').strip("'")

    lesson_id = frontmatter_dict.get("id")
    import uuid
    updated_lesson_file = False

    if not lesson_id:
        lesson_id = str(uuid.uuid4())
        frontmatter_dict["id"] = lesson_id
        updated_lesson_file = True

    # Rename legacy emoji 🪻, ltn, or li to lc (listening count)
    for legacy_key in ["🪻", "ltn", "li"]:
        if legacy_key in frontmatter_dict:
            frontmatter_dict["lc"] = frontmatter_dict.pop(legacy_key)
            updated_lesson_file = True

    if updated_lesson_file:
        new_frontmatter_lines = ["---"]
        # Ensure id is always at the top of frontmatter for neatness
        if "id" in frontmatter_dict:
            new_frontmatter_lines.append(f"id: {frontmatter_dict['id']}")
        for k, v in frontmatter_dict.items():
            if k != "id":
                new_frontmatter_lines.append(f"{k}: \"{v}\"")
        new_frontmatter_lines.append("---")

        if has_frontmatter:
            new_content = "\n".join(new_frontmatter_lines) + "\n" + "\n".join(content_lines)
        else:
            new_content = "\n".join(new_frontmatter_lines) + "\n" + content

        try:
            with open(lesson_file, "w", encoding="utf-8") as f:
                f.write(new_content)
        except Exception:
            pass

    updated_questions = False
    words_db = lesson_data.get("words", [])
    for word_item in words_db:
        if word_item.get("lid") != lesson_id:
            word_item["lid"] = lesson_id
            updated_questions = True

    return updated_questions

def run_session():
    global LESSON_FILE, SESSIONS_FILE, W_MD_FILE, S_MD_FILE, SELECTED_LEVELS, USER_DIR, LESSON_DIR

    # 1. Resolve path settings based on target lesson folder
    lesson_file, json_file, w_md_file, s_md_file, sessions_file = resolve_paths()
    LESSON_FILE = lesson_file
    W_MD_FILE = w_md_file
    S_MD_FILE = s_md_file
    SESSIONS_FILE = sessions_file

    # Clear console immediately upon starting
    os.system('clear' if os.name != 'nt' else 'cls')

    # Print the lesson folder title and current user
    lesson_dir = os.path.dirname(USER_DIR)
    if len(SELECTED_LEVELS) == 1:
        level_suffix = f" (LV{SELECTED_LEVELS[0]})"
    else:
        if len(SELECTED_LEVELS) == 5:
            level_suffix = " (TỔNG HỢP)"
        else:
            level_suffix = f" (LV{','.join(map(str, SELECTED_LEVELS))})"

    username = os.path.basename(USER_DIR)
    if username.startswith("👤") or username.startswith("."):
        username = username[1:].strip()
    username = f"{username}{level_suffix}"

    script_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_root = os.path.dirname(script_dir)
    try:
        lesson_title = os.path.relpath(lesson_dir, start=workspace_root)
        if lesson_title.startswith(".."):
            lesson_title = os.path.basename(lesson_dir)
    except:
        lesson_title = os.path.basename(lesson_dir)

    print(f"📖 Bài học: {lesson_title}")
    print(f"👤 Học viên: {username}\n")

    print_shortcuts_guide("session_select")

    session_state = None
    # Session loop
    while True:
        try:
            if session_state is not None:
                mode = session_state["mode"]
                mode_index = session_state["mode_index"]
                target_level = session_state["target_level"]
                tested_sentences = list(session_state["initial_tested_sentences"])
                active_words = session_state["active_words"]
                master_sessions = session_state["master_sessions"]
                active_session = session_state["active_session"]
                scores_db = session_state["scores_db"]
                words_db = session_state["words_db"]
                unique_count = session_state["unique_count"]
                ideal_total = session_state["ideal_total"]
                in_quiz_phase = True
                bypass_setup = True
            else:
                mode = "W"
                priority_mode = 3
                use_saved = False
                in_quiz_phase = False
                bypass_setup = False

            # Outer loop for session selection/deletion
            while not bypass_setup:
                master_sessions = load_sessions()
                if not master_sessions:
                    use_saved = False
                    break

                # Find index of the session with the maximum last_datetime among matching levels
                default_idx = None
                latest_time = ""
                for idx, s in enumerate(master_sessions, 1):
                    if s.get("levels") == SELECTED_LEVELS:
                        s_time = s.get("last_datetime", "")
                        if s_time > latest_time:
                            latest_time = s_time
                            default_idx = idx

                if SELECTED_LEVELS == [1, 2, 3, 4, 5]:
                    lvl_suffix = "TỔNG HỢP"
                else:
                    lvl_suffix = "LV" + ",".join(map(str, SELECTED_LEVELS))
                print(f"📂 PHIÊN HỌC CŨ ({lvl_suffix})")
                short_p_names = {
                    1: "📈",
                    2: "📉",
                    3: "⬆️",
                    4: "⬇️",
                    5: "📏",
                    6: "✂️",
                    7: "🟢",
                    8: "🔴",
                    9: "🎲"
                }

                # Dynamically calculate the maximum visual width of the level column
                max_lvl_len = 6
                for s in master_sessions:
                    s_lvs = s.get("levels", [1])
                    s_r = s.get("sel_range")
                    r_suffix = f" ({s_r[0]}-{s_r[1]})" if s_r else ""
                    if s_lvs == [1, 2, 3, 4, 5]:
                        lvl_lbl = "🏷️ TỔNG HỢP" + r_suffix
                    else:
                        lvl_lbl = f"🏷️ LV{','.join(map(str, s_lvs))}" + r_suffix
                    v_len = sum(2 if ord(c) >= 0x2300 else 1 for c in lvl_lbl if c != '\ufe0f')
                    if v_len > max_lvl_len:
                        max_lvl_len = v_len

                sessions = master_sessions
                for idx, s in enumerate(sessions, 1):
                    m_val = s.get("input_mode", "W")
                    m_emoji = "⚡"
                    m_label = "W" if m_val == "W" else ("S" if m_val == "S" else ("N" if m_val == "N" else "K"))
                    p_val = s.get("priority_mode", 3)
                    p_label = short_p_names.get(p_val, "🎯")
                    tgt_val = s.get("target_level")

                    s_lvs = s.get("levels", [1])
                    s_r = s.get("sel_range")
                    r_suffix = f" ({s_r[0]}-{s_r[1]})" if s_r else ""
                    if s_lvs == [1, 2, 3, 4, 5]:
                        s_lvl_label = "TỔNG HỢP" + r_suffix
                    else:
                        s_lvl_label = "LV" + ",".join(map(str, s_lvs)) + r_suffix

                    star = " ⭐" if idx == default_idx else ""

                    delta_val = ""
                    dt_str = s.get("last_datetime", "")
                    if dt_str:
                        try:
                            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                            diff = datetime.now() - dt
                            if diff.total_seconds() < 0:
                                years = 0
                                months = 0
                                days = 0
                                hours = 0
                                minutes = 0
                            else:
                                total_days = diff.days
                                years = total_days // 365
                                months = (total_days % 365) // 30
                                days = (total_days % 365) % 30
                                hours = diff.seconds // 3600
                                minutes = (diff.seconds % 3600) // 60
                            delta_val = f"{years:02d}:{months:02d} ⏳ {days:02d}:{hours:02d}:{minutes:02d}"
                        except:
                            pass

                    s_muted = is_session_muted(s)
                    sound_icon = "🔇" if s_muted else "🔊"
                    col_idx_mode_pri = visual_ljust(f"  [{idx}] {m_emoji} {m_label} {sound_icon} - {p_label}", 18)
                    col_tgt = visual_ljust(f"🎯 {tgt_val}" if tgt_val else "", 5)
                    col_lvl = visual_ljust(f"🏷️ {s_lvl_label}", max_lvl_len)
                    col_delta = visual_ljust(delta_val, 17)

                    line_str = f"{col_idx_mode_pri} | {col_tgt} | {col_lvl} | {col_delta} |{star}"
                    if s_lvs == SELECTED_LEVELS:
                        print(line_str)
                    else:
                        print(f"\033[90m{line_str}\033[0m")
                print()

                if 0 in SELECTED_LEVELS:
                    print("\033[93m💡 Gợi ý: Gõ '.sel [bắt đầu] [kết thúc]' (vd: .sel 1 10) chọn khoảng câu học, hoặc '.reset' để reset điểm.\033[0m\n")

                inner_break = False
                while True:
                    prompt_suffix = f" <⭐{default_idx}>" if default_idx is not None else ""
                    ans = quiz_input(f"Chọn phiên theo STT{prompt_suffix} hoặc 'n' tạo mới: ").strip().lower()
                    if ans.startswith(".sel"):
                        handle_sel_command(ans)
                        continue
                    elif ans.startswith(".reset") or ans.startswith("reset") or ans.startswith("rst"):
                        if handle_reset_scores_command(ans):
                            inner_break = True
                            break
                        continue
                    elif ans == ".h":
                        print_shortcuts_guide("session_select")
                        continue
                    elif ans == "...":
                        # Temporary load for progress table
                        temp_words_db = []
                        for lv in SELECTED_LEVELS:
                            lv_json = os.path.join(USER_DIR, f"lv{lv}", "preq.json")
                            if os.path.exists(lv_json):
                                try:
                                    with open(lv_json, "r", encoding="utf-8") as f:
                                        temp_words_db.extend(json.load(f).get("words", []))
                                except:
                                    pass
                        temp_scores_db = load_all_scores()
                        valid_w = {w["word"] for w in temp_words_db}
                        filtered = {w: val for w, val in temp_scores_db.items() if w in valid_w}
                        print_progress_table(filtered, "W")
                        continue
                    elif ans == ".":
                        sys.exit(0)
                    elif ans == "..":
                        raise GoBackException()
                    elif ans == "n":
                        use_saved = False
                        inner_break = True
                        break
                    elif (ans.startswith("-") or ans.startswith("r")) and len(ans) > 1 and ans[1:].isdigit():
                        del_idx = int(ans[1:])
                        if 1 <= del_idx <= len(sessions):
                            target_session = sessions[del_idx - 1]
                            master_sessions.remove(target_session)
                            save_sessions(master_sessions)
                            print(f"\n🗑️  Đã xóa phiên học số {del_idx}!\n")
                            inner_break = True
                            break
                        else:
                            print(f"⚠️ Không tìm thấy phiên học số {del_idx}.")
                            continue
                    elif ans.startswith("u") and len(ans) > 1 and ans[1:].isdigit():
                        u_idx = int(ans[1:])
                        if 1 <= u_idx <= len(sessions):
                            target_session = sessions[u_idx - 1]
                            print(f"\n⚙️  CẬP NHẬT PHIÊN HỌC SỐ {u_idx}")

                            # Update levels
                            curr_lvs = target_session.get("levels", [1])
                            if curr_lvs == [1, 2, 3, 4, 5]:
                                curr_lvs_str = "0"
                            else:
                                curr_lvs_str = ",".join(map(str, curr_lvs))
                            while True:
                                l_in = quiz_input(f" Chọn cấp độ học mới (0-5 hoặc danh sách/dải) [hiện tại {curr_lvs_str}]: ").strip()
                                if l_in == "..":
                                    raise GoBackException()
                                if l_in == "":
                                    break
                                parsed_lvs = parse_levels(l_in)
                                if parsed_lvs is not None:
                                    target_session["levels"] = parsed_lvs
                                    break
                                print("  ⚠️ Nhập không hợp lệ. Vui lòng chọn số (0-5), danh sách (ví dụ: 1,2), hoặc dải (ví dụ: 1-3).")

                            # Update input_mode
                            curr_mode = target_session.get("input_mode", "W")
                            m_in = quiz_input(f" Chọn chế độ (W: Viết / S: Nói / N: Tên / K: STT) [hiện tại {curr_mode}]: ").strip().upper()
                            if m_in == "..":
                                raise GoBackException()
                            if m_in in ["W", "S", "N", "K"]:
                                target_session["input_mode"] = m_in

                            # Update priority_mode
                            curr_pri = target_session.get("priority_mode", 3)
                            print("  Chọn chế độ ưu tiên câu hỏi:")
                            print("   1. 📈 Tăng dần  | 2. 📉 Giảm dần  | 3. ⬆️ Thấp điểm | 4. ⬇️ Cao điểm | 5. 📏 Từ dài")
                            print("   6. ✂️ Từ ngắn  | 7. 🟢 Từ dễ     | 8. 🔴 Từ khó    | 9. 🎲 Ngẫu nhiên")
                            p_in = quiz_input(f"  Nhập lựa chọn (1-9) [hiện tại {curr_pri}]: ").strip()
                            if p_in == "..":
                                raise GoBackException()
                            if p_in.isdigit() and 1 <= int(p_in) <= 9:
                                target_session["priority_mode"] = int(p_in)

                            # Update target_level
                            curr_tgt = target_session.get("target_level", "")
                            curr_tgt_str = str(curr_tgt) if curr_tgt else "chưa có"
                            t_in = quiz_input(f"  Nhập mục tiêu mới (số điểm) [hiện tại {curr_tgt_str}]: ").strip()
                            if t_in == "..":
                                raise GoBackException()
                            if t_in.isdigit():
                                target_session["target_level"] = int(t_in)
                            elif t_in.lower() in ["xoa", "xóa", "-"]:
                                if "target_level" in target_session:
                                    del target_session["target_level"]

                            # Update mute (sound) setting
                            curr_mode_updated = target_session.get("input_mode", "W")
                            default_m = is_session_muted(target_session)
                            curr_m_str = "Tắt" if default_m else "Bật"
                            curr_m_char = "n" if default_m else "y"
                            sound_in = quiz_input(f"  Phát âm (y: Bật, n: Tắt) [hiện tại {curr_m_str}] <⭐{curr_m_char}>: ").strip().lower()
                            if sound_in == "..":
                                raise GoBackException()
                            if sound_in in ["n", "no", "t", "tat", "tắt", "0"]:
                                target_session["mute"] = True
                            elif sound_in in ["y", "yes", "b", "bat", "bật", "1"]:
                                target_session["mute"] = False

                            # Update STT range (sel_range)
                            curr_r = target_session.get("sel_range")
                            curr_r_str = f"{curr_r[0]}-{curr_r[1]}" if curr_r else "Tất cả"
                            r_in = quiz_input(f"  Khoảng câu STT học (vd: 1 10, '-' = Tất cả) [hiện tại {curr_r_str}]: ").strip().lower()
                            if r_in == "..":
                                raise GoBackException()
                            if r_in in ["-", "all", "tatca", "tất cả"]:
                                target_session["sel_range"] = None
                            elif r_in:
                                rng_parts = re.findall(r'\d+', r_in)
                                if len(rng_parts) >= 2:
                                    s_start = int(rng_parts[0])
                                    s_end = int(rng_parts[1])
                                    if s_start > s_end:
                                        s_start, s_end = s_end, s_start
                                    target_session["sel_range"] = [s_start, s_end]

                            # Update last_datetime to bubble it up as the latest
                            target_session["last_datetime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                            save_sessions(master_sessions)
                            print(f"\n✅ Đã cập nhật phiên học số {u_idx} thành công!\n")
                            inner_break = True
                            break
                        else:
                            print(f"⚠️ Không tìm thấy phiên học số {u_idx}.")
                            continue
                    elif ans == "":
                        if default_idx is not None:
                            selected = sessions[default_idx - 1]
                            s_lvs = selected.get("levels", [1])
                            if s_lvs != SELECTED_LEVELS:
                                SELECTED_LEVELS = s_lvs
                                if SELECTED_LEVELS == [1, 2, 3, 4, 5]:
                                    lvl_lbl = "TỔNG HỢP"
                                else:
                                    lvl_lbl = "LV" + ",".join(map(str, SELECTED_LEVELS))
                                print(f"\n🔄 Tự động chuyển sang cấp độ: {lvl_lbl}\n")

                                # Copy questions if missing
                                for lv in SELECTED_LEVELS:
                                    lvl_dir = os.path.join(USER_DIR, f"lv{lv}")
                                    os.makedirs(lvl_dir, exist_ok=True)
                                    lv_json = os.path.join(lvl_dir, "preq.json")
                                    if not os.path.exists(lv_json):
                                        copied = copy_questions_from_other_users(LESSON_DIR, lvl_dir, username)
                                        if not copied:
                                            print(f"Error: preq.json not found in level directory: {lvl_dir}")
                                            sys.exit(1)

                            mode = selected.get("input_mode", "W")
                            priority_mode = selected.get("priority_mode", 3)
                            use_saved = True
                            inner_break = True
                            active_session = selected
                            break
                        else:
                            use_saved = False
                            inner_break = True
                            break
                    elif ans.isdigit():
                        sel = int(ans)
                        if 1 <= sel <= len(sessions):
                            selected = sessions[sel - 1]
                            s_lvs = selected.get("levels", [1])
                            if s_lvs != SELECTED_LEVELS:
                                SELECTED_LEVELS = s_lvs
                                if SELECTED_LEVELS == [1, 2, 3, 4, 5]:
                                    lvl_lbl = "TỔNG HỢP"
                                else:
                                    lvl_lbl = "LV" + ",".join(map(str, SELECTED_LEVELS))
                                print(f"\n🔄 Tự động chuyển sang cấp độ: {lvl_lbl}\n")

                                # Copy questions if missing
                                for lv in SELECTED_LEVELS:
                                    lvl_dir = os.path.join(USER_DIR, f"lv{lv}")
                                    os.makedirs(lvl_dir, exist_ok=True)
                                    lv_json = os.path.join(lvl_dir, "preq.json")
                                    if not os.path.exists(lv_json):
                                        copied = copy_questions_from_other_users(LESSON_DIR, lvl_dir, username)
                                        if not copied:
                                            print(f"Error: preq.json not found in level directory: {lvl_dir}")
                                            sys.exit(1)

                            mode = selected.get("input_mode", "W")
                            priority_mode = selected.get("priority_mode", 3)
                            use_saved = True
                            inner_break = True
                            active_session = selected
                            break
                        else:
                            print(f"⚠️ Vui lòng nhập số từ 1 đến {len(sessions)}.")
                    else:
                        print("⚠️ Nhập không hợp lệ. Vui lòng chọn lại.")

                if inner_break:
                    if use_saved or ans == "n":
                        break

            if not use_saved:
                if SELECTED_LEVELS == [0]:
                    mode_input = quiz_input("Chọn chế độ (N: Tên / K: STT) <⭐N>: ").strip().upper()
                    if mode_input == "..":
                        raise GoBackException()
                    if mode_input in ["N", "K"]:
                        mode = mode_input
                    else:
                        mode = "N"
                else:
                    mode_input = quiz_input("Chọn chế độ (W: Viết / S: Nói / N: Tên / K: STT) <⭐W>: ").strip().upper()
                    if mode_input == "..":
                        raise GoBackException()
                    if mode_input in ["W", "S", "N", "K"]:
                        mode = mode_input
                    else:
                        mode = "W"
                    if mode in ["N", "K"]:
                        SELECTED_LEVELS = [0]

                print("\nChọn chế độ ưu tiên câu hỏi:")
                print(" 1. 📈 Thứ tự bài học tăng dần  |  2. 📉 Thứ tự bài học giảm dần")
                print(" 3. ⬆️ Ưu tiên từ thấp điểm     |  4. ⬇️ Ưu tiên từ cao điểm")
                print(" 5. 📏 Ưu tiên từ dài           |  6. ✂️ Ưu tiên từ ngắn")
                print(" 7. 🟢 Ưu tiên từ dễ            |  8. 🔴 Ưu tiên từ khó")
                print(" 9. 🎲 Ngẫu nhiên")
                pri_input = quiz_input("Nhập lựa chọn (1-9) <⭐3>: ").strip()
                if pri_input == "..":
                    raise GoBackException()
                if pri_input.isdigit() and 1 <= int(pri_input) <= 9:
                    priority_mode = int(pri_input)

                # Prompt for sound/mute mode
                default_mute = (mode in ["N", "K"])
                default_char = "n" if default_mute else "y"
                sound_input = quiz_input(f"Phát âm (y: Bật, n: Tắt) <⭐{default_char}>: ").strip().lower()
                if sound_input == "..":
                    raise GoBackException()
                if sound_input in ["n", "no", "t", "tat", "tắt", "0"]:
                    session_mute = True
                elif sound_input in ["y", "yes", "b", "bat", "bật", "1"]:
                    session_mute = False
                else:
                    session_mute = default_mute

                # Prompt for STT range (sel_range)
                session_sel_range = None
                if 0 in SELECTED_LEVELS or mode in ["N", "K"]:
                    range_in = quiz_input("Khoảng câu STT học (vd: 1 10, Enter = Tất cả) <⭐Tất cả>: ").strip()
                    if range_in == "..":
                        raise GoBackException()
                    if range_in and range_in not in ["-", "all", "tatca", "tất cả"]:
                        rng_parts = re.findall(r'\d+', range_in)
                        if len(rng_parts) >= 2:
                            s_start = int(rng_parts[0])
                            s_end = int(rng_parts[1])
                            if s_start > s_end:
                                s_start, s_end = s_end, s_start
                            session_sel_range = [s_start, s_end]

            # Update last_datetime for the selected/created session in master_sessions
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if not use_saved:
                active_session = {
                    "input_mode": mode,
                    "priority_mode": priority_mode,
                    "mute": session_mute,
                    "sel_range": session_sel_range,
                    "last_datetime": now_str,
                    "levels": SELECTED_LEVELS
                }
                master_sessions.append(active_session)
            else:
                active_session["last_datetime"] = now_str
            save_sessions(master_sessions)

            # Re-resolve LESSON_FILE based on finalized SELECTED_LEVELS
            if len(SELECTED_LEVELS) == 1:
                lvl_dir = os.path.join(USER_DIR, f"lv{SELECTED_LEVELS[0]}")
                os.makedirs(lvl_dir, exist_ok=True)
                lesson_file = os.path.join(lvl_dir, "bold.md")
                if not os.path.exists(lesson_file):
                    target_md_files = [f for f in os.listdir(LESSON_DIR) if f.endswith(".md") and not f.startswith(".") and f not in {"scwr.md", "scsp.md"} and os.path.isfile(os.path.join(LESSON_DIR, f))] if os.path.exists(LESSON_DIR) else []
                    lesson_file = os.path.join(LESSON_DIR, target_md_files[0]) if target_md_files else ""
                LESSON_FILE = lesson_file
            else:
                target_md_files = [f for f in os.listdir(LESSON_DIR) if f.endswith(".md") and not f.startswith(".") and f not in {"scwr.md", "scsp.md"} and os.path.isfile(os.path.join(LESSON_DIR, f))] if os.path.exists(LESSON_DIR) else []
                LESSON_FILE = os.path.join(LESSON_DIR, target_md_files[0]) if target_md_files else ""

            if not bypass_setup:
                # Load the questions database dynamically from the finalized selected levels
                import uuid
                words_db = []
                for lv in SELECTED_LEVELS:
                    lv_json = os.path.join(USER_DIR, f"lv{lv}", "preq.json")
                    if os.path.exists(lv_json):
                        try:
                            with open(lv_json, "r", encoding="utf-8") as f:
                                lv_data = json.load(f)
                        except Exception:
                            continue

                        lv_words = lv_data.get("words", [])
                        updated_questions = False
                        for word_item in lv_words:
                            if "uuid" in word_item:
                                word_item["id"] = word_item.pop("uuid")
                                updated_questions = True
                            if "id" not in word_item:
                                word_item["id"] = str(uuid.uuid4())
                                updated_questions = True

                        # Ensure lesson ID and question reference key (lid)
                        lid_updated = ensure_lesson_id_and_reference(LESSON_FILE, lv_json, lv_data)
                        if lid_updated:
                            updated_questions = True

                        if updated_questions:
                            try:
                                with open(lv_json, "w", encoding="utf-8") as f:
                                    json.dump(lv_data, f, ensure_ascii=False, indent=2)
                            except Exception:
                                pass
                        words_db.extend(lv_words)

                sel_r = active_session.get("sel_range")
                if sel_r and len(sel_r) == 2:
                    s_start, s_end = sel_r[0], sel_r[1]
                    filtered_words = []
                    for w_item in words_db:
                        s_no = w_item.get("stt", w_item.get("sentence_no"))
                        if s_no is not None:
                            try:
                                s_no = int(s_no)
                                if s_start <= s_no <= s_end:
                                    filtered_words.append(w_item)
                            except ValueError:
                                filtered_words.append(w_item)
                        else:
                            filtered_words.append(w_item)
                    words_db = filtered_words

                # Load current scores
                scores_db = load_all_scores()

                # Filter scores to only keep words present in words_db (strict level partitioning)
                valid_words = {w["word"] for w in words_db}
                filtered_scores = {}
                for w_name, val in scores_db.items():
                    if w_name in valid_words:
                        filtered_scores[w_name] = val

                updated_scores = False
                if len(filtered_scores) != len(scores_db):
                    updated_scores = True
                scores_db = filtered_scores

                # Initialize any words from words_db not present in scores_db
                for idx, word_item in enumerate(words_db, 1):
                    w_name = word_item["word"]
                    if w_name not in scores_db:
                        scores_db[w_name] = [0, 0, 0, 0, word_item.get("stt", idx)]
                        updated_scores = True

                if updated_scores:
                    save_all_scores(scores_db)

                mode_index = 0 if mode == "W" else (1 if mode == "S" else (2 if mode == "N" else 3))

                # Calculate Target level T
                active_words = []
                for word_item in words_db:
                    w_name = word_item["word"]
                    score = scores_db.get(w_name, [0, 0, 0, 0, 0])[mode_index]
                    if score < 200:
                        active_words.append(word_item)

                if not active_words:
                    print("\n==================================================")
                    print("☆ Tất cả từ vựng trong bài học này đã đạt điểm tối đa (200)!")
                    print("==================================================")
                    if 0 in SELECTED_LEVELS and mode in ["N", "K"]:
                        print("\033[93m💡 Gợi ý: Gõ '.sel [bắt đầu] [kết thúc]' (vd: .sel 1 10) để chọn khoảng câu học khác.\033[0m")
                        ans = quiz_input("Nhập phím tắt hoặc Enter để thoát: ").strip()
                        if ans.lower().startswith(".sel"):
                            if handle_sel_command(ans):
                                raise RestartException()
                    sys.exit(0)

                M = max(scores_db.get(w["word"], [0,0,0,0,0])[mode_index] for w in active_words)
                min_active_score = min(scores_db.get(w["word"], [0,0,0,0,0])[mode_index] for w in active_words)

                saved_target = active_session.get("target_level")
                if saved_target is not None and saved_target > min_active_score:
                    target_level = saved_target
                else:
                    target_level = min(200, M + 1)
                    active_session["target_level"] = target_level
                    save_sessions(master_sessions)

                # Filter words to only those < target_level
                session_words = [w for w in active_words if scores_db.get(w["word"], [0,0,0,0,0])[mode_index] < target_level]

                if not session_words:
                    print("\n==================================================")
                    print(f"☆ Buổi học đã hoàn thành! Tất cả từ vựng đã đạt {target_level} điểm.")
                    print("==================================================")
                    if 0 in SELECTED_LEVELS and mode in ["N", "K"]:
                        print("\033[93m💡 Gợi ý: Gõ '.sel [bắt đầu] [kết thúc]' (vd: .sel 1 10) để chọn khoảng câu học khác.\033[0m")
                        ans = quiz_input("Nhập phím tắt hoặc Enter để thoát: ").strip()
                        if ans.lower().startswith(".sel"):
                            if handle_sel_command(ans):
                                raise RestartException()
                    sys.exit(0)

                # Sort words
                session_words = sort_words(session_words, priority_mode, scores_db, mode_index)

                # Group sentences to avoid repeats
                sentences_map = {}
                for word_item in session_words:
                    s_no = word_item["sentence_no"]
                    if s_no not in sentences_map:
                        sentences_map[s_no] = {
                            "sentence_no": s_no,
                            "sentence_original": word_item["sentence_original"],
                            "masked_sentence": word_item["masked_sentence"],
                            "translation": word_item["translation"],
                            "ipa": word_item["ipa"],
                            "targets": word_item.get("targets", []),
                            "name": word_item.get("name"),
                            "words_info": []
                        }
                    sentences_map[s_no]["words_info"].append(word_item)

                tested_sentences = []
                seen_s_no = set()
                for word_item in session_words:
                    s_no = word_item["sentence_no"]
                    if s_no not in seen_s_no:
                        tested_sentences.append(sentences_map[s_no])
                        seen_s_no.add(s_no)

                total_questions = len(tested_sentences)

                distinct_scores = sorted(list(set(scores_db.get(w["word"], [0,0,0,0,0])[mode_index] for w in session_words)))
                range_str = str(distinct_scores)

                print("\n==================================================")
                all_scores = [scores_db.get(w["word"], [0,0,0,0,0])[mode_index] for w in active_words]
                if len(set(all_scores)) == 1 and all_scores[0] > 0:
                    print(f"🎉 Tuyệt vời! Tất cả từ vựng đã đồng đều đạt {all_scores[0]} điểm.")
                db_questions_count = len(set(q["sentence_no"] for q in words_db))
                print(f"🎯 Mục tiêu: {range_str} => {target_level} điểm ({total_questions}/{db_questions_count} câu)")
                sound_label = "🔇" if is_session_muted(active_session) else "🔊"
                sound_status = "Tắt (Muted)" if is_session_muted(active_session) else "Bật"
                print(f"{sound_label} Phát âm: {sound_status}")
                if 0 in SELECTED_LEVELS and mode in ["N", "K"]:
                    print(f"💡 Chọn khoảng câu học: Gõ '.sel [bắt đầu] [kết thúc]'")
                print("==================================================")


                while True:
                    start_ans = quiz_input("Enter để học hoặc nhập số đổi mục tiêu: ").strip()
                    if start_ans.lower().startswith(".sel"):
                        if handle_sel_command(start_ans):
                            raise RestartException()
                        continue
                    elif start_ans == "...":
                        print_progress_table(scores_db, mode)
                        continue
                    elif start_ans == ".h":
                        print_shortcuts_guide("session_select")
                        continue
                    elif start_ans == ".m":
                        is_muted = not is_session_muted(active_session)
                        active_session["mute"] = is_muted
                        save_sessions(master_sessions)
                        sound_label = "🔇" if is_muted else "🔊"
                        sound_status = "Tắt (Muted)" if is_muted else "Bật"
                        print(f"\n{sound_label} Phát âm: {sound_status}\n")
                        continue
                    elif start_ans == ".":
                        sys.exit(0)
                    elif start_ans.isdigit():
                        new_target = int(start_ans)
                        temp_session_words = [w for w in active_words if scores_db.get(w["word"], [0,0,0,0,0])[mode_index] < new_target]
                        if not temp_session_words:
                            min_active_score = min(scores_db.get(w["word"], [0,0,0,0,0])[mode_index] for w in active_words)
                            suggested_target = min(200, min_active_score + 1)
                            confirm_ans = quiz_input(f"⚠️ Tất cả từ vựng đã đạt {new_target} điểm.\nBạn có muốn dùng {suggested_target} làm mục tiêu? (⭐y/n): ").strip().lower()
                            if confirm_ans in ["", "y", "yes", "c", "có"]:
                                new_target = suggested_target
                            else:
                                continue

                        target_level = min(200, new_target)
                        active_session["target_level"] = target_level
                        save_sessions(master_sessions)

                        # Re-filter words to only those < target_level
                        session_words = [w for w in active_words if scores_db.get(w["word"], [0,0,0,0,0])[mode_index] < target_level]
                        if not session_words:
                            print(f"⚠️ Không có từ vựng nào có điểm dưới {target_level}.")
                            continue

                        # Re-sort and re-group
                        session_words = sort_words(session_words, priority_mode, scores_db, mode_index)

                        sentences_map = {}
                        for word_item in session_words:
                            s_no = word_item["sentence_no"]
                            if s_no not in sentences_map:
                                sentences_map[s_no] = {
                                    "sentence_no": s_no,
                                    "sentence_original": word_item["sentence_original"],
                                    "masked_sentence": word_item["masked_sentence"],
                                    "translation": word_item["translation"],
                                    "ipa": word_item["ipa"],
                                    "targets": word_item.get("targets", []),
                                    "name": word_item.get("name"),
                                    "words_info": []
                                }
                            sentences_map[s_no]["words_info"].append(word_item)

                        tested_sentences = []
                        seen_s_no = set()
                        for word_item in session_words:
                            s_no = word_item["sentence_no"]
                            if s_no not in seen_s_no:
                                tested_sentences.append(sentences_map[s_no])
                                seen_s_no.add(s_no)

                        total_questions = len(tested_sentences)

                        distinct_scores = sorted(list(set(scores_db.get(w["word"], [0,0,0,0,0])[mode_index] for w in session_words)))
                        range_str = str(distinct_scores)
                        print("\n==================================================")
                        db_questions_count = len(set(q["sentence_no"] for q in words_db))
                        print(f"🎯 Mục tiêu mới: {range_str} => {target_level} điểm ({total_questions}/{db_questions_count} câu)")
                        sound_label = "🔇" if is_session_muted(active_session) else "🔊"
                        sound_status = "Tắt (Muted)" if is_session_muted(active_session) else "Bật"
                        print(f"{sound_label} Phát âm: {sound_status}")
                        print("==================================================")
                        continue
                    else:
                        break

            # Clear console before starting the quiz
            os.system('clear' if os.name != 'nt' else 'cls')

            if not bypass_setup:
                # Calculate ideal total questions (Z) based on initial scores
                unique_count = len(tested_sentences)
                ideal_total = 0
                for q in tested_sentences:
                    max_deficit = 0
                    for target_item in q["words_info"]:
                        word_name = target_item["word"]
                        current_score = scores_db.get(word_name, [0,0,0,0,0])[mode_index]
                        deficit = max(0, target_level - current_score)
                        if deficit > max_deficit:
                            max_deficit = deficit
                    ideal_total += max_deficit

                session_state = {
                    "mode": mode,
                    "mode_index": mode_index,
                    "target_level": target_level,
                    "initial_tested_sentences": list(tested_sentences),
                    "active_words": active_words,
                    "master_sessions": master_sessions,
                    "active_session": active_session,
                    "scores_db": scores_db,
                    "words_db": words_db,
                    "unique_count": unique_count,
                    "ideal_total": ideal_total
                }

            def show_header(q_idx):
                sound_emoji = "🔇" if is_session_muted(active_session) else "🔊"
                header_text = f" [{sound_emoji} CH {q_idx + 1} / {unique_count} / {ideal_total}] "
                print(f"\n\033[90m{visual_center(header_text, 50, '-')}\033[0m\n")

            def show_question(q_data):
                if mode == "N":
                    clean_name = clean_terminal_output(q_data.get("name") or "")
                    if not clean_name:
                        words = [w["word"] for w in q_data.get("words_info", [])]
                        clean_name = ", ".join(words)
                    if not clean_name:
                        clean_name = clean_terminal_output(q_data.get("translation") or "")
                    if clean_name:
                        print(f"📌  {clean_name}\n")
                    else:
                        print(f"📌  (Không có Tên/Từ vựng)\n")
                    print("\033[2;90m--------------------------------------------------\033[0m\n")
                    return
                elif mode == "K":
                    stt_val = q_data.get("stt")
                    if stt_val is None:
                        stt_val = q_data.get("sentence_no", "?")
                    print(f"📌  STT: {stt_val}\n")
                    print("\033[2;90m--------------------------------------------------\033[0m\n")
                    return

                clean_masked = clean_terminal_output(q_data["masked_sentence"])
                clean_masked = re.sub(r'\s*\(\d+\)', '', clean_masked)
                clean_translation = clean_terminal_output(q_data["translation"])
                if "name" in q_data and q_data["name"]:
                    print(f"📌  {clean_terminal_output(q_data['name'])}\n")
                print(f"👉  {clean_masked}\n")
                print(f"\033[90m💬  {clean_translation}\033[0m\n")
                print("\033[2;90m--------------------------------------------------\033[0m\n")

            q_index = 0
            while q_index < len(tested_sentences):
                q_data = tested_sentences[q_index]
                show_header(q_index)
                show_question(q_data)

                original_sentence = clean_terminal_output(q_data["sentence_original"])
                original_sentence = re.sub(r'^\d+\.\s*', '', original_sentence).strip()

                correct_count = 0
                aborted = False
                redo_question = False
                targets_list = q_data.get("targets", [])
                has_used_hint = False

                if mode in ["N", "K"]:
                    while True:
                        raw_ans = quiz_input("👁️  Nhẩm: ")
                        ans = raw_ans.strip()
                        if ans == ".":
                            os.system('clear' if os.name != 'nt' else 'cls')
                            redo_question = True
                            break
                        elif ans == "..":
                            save_all_scores(scores_db)
                            show_header(q_index)
                            show_question(q_data)
                            continue
                        elif ans == "...":
                            print_progress_table(scores_db, mode)
                            show_header(q_index)
                            show_question(q_data)
                            continue
                        elif ans == ".m":
                            is_muted = not is_session_muted(active_session)
                            active_session["mute"] = is_muted
                            save_sessions(master_sessions)
                            if is_muted:
                                print("\n🔇 Đã tắt âm thanh (Muted)\n")
                            else:
                                print("\n🔊 Đã bật âm thanh (Unmuted)\n")
                            show_header(q_index)
                            show_question(q_data)
                            continue
                        elif ans == ".h":
                            print_shortcuts_guide("quiz_input")
                            show_header(q_index)
                            show_question(q_data)
                            continue
                        else:
                            break

                    if redo_question:
                        continue

                    # Show English and Translation
                    if mode == "K" and q_data.get("name"):
                        print(f"📌  Tên: {clean_terminal_output(q_data['name'])}\n")
                    print(f"👉  {original_sentence}\n")
                    print(f"\033[90m💬  {clean_terminal_output(q_data['translation'])}\033[0m\n")

                    if not is_session_muted(active_session):
                        speak_sentence(original_sentence)

                    if q_data["ipa"]:
                        clean_ipa = clean_terminal_output(q_data["ipa"])
                        print(f"\033[90m🗣️  /{clean_ipa}/\033[0m")
                    print()

                    # Ask if they remembered correctly
                    is_passed = True
                    redo_question = False
                    while True:
                        confirm = quiz_input("🤔 Nhớ đúng? (⭐y/n): ")
                        confirm_clean = confirm.strip().lower()
                        if confirm_clean == ".":
                            is_passed = False
                            redo_question = True
                            break
                        elif confirm_clean == "..":
                            save_all_scores(scores_db)
                            print("\n💾 Đã lưu tạm tiến độ!\n")
                            continue
                        elif confirm_clean == "...":
                            print_progress_table(scores_db, mode)
                            continue
                        elif confirm_clean == ".m":
                            is_muted = not is_session_muted(active_session)
                            active_session["mute"] = is_muted
                            save_sessions(master_sessions)
                            if is_muted:
                                print("\n🔇 Đã tắt âm thanh (Muted)\n")
                            else:
                                print("\n🔊 Đã bật âm thanh (Unmuted)\n")
                            continue
                        elif confirm_clean == ".h":
                            print_shortcuts_guide("quiz_input")
                            continue
                        elif confirm_clean.startswith(".w") or confirm_clean.startswith(".p") or confirm_clean.startswith(".s"):
                            handle_audio_shortcut(confirm_clean, targets_list, original_sentence)
                            continue
                        elif confirm_clean in ["n", "no", "k", "khong", "không"]:
                            is_passed = False
                            break
                        elif confirm_clean in ["", "y", "yes", "c", "có"]:
                            is_passed = True
                            break
                        else:
                            print("⚠️ Lệnh không hợp lệ. Vui lòng nhập y (đúng), n (sai) hoặc lệnh phím tắt.\n")
                            continue

                    status_label = "✅" if is_passed else "❌"
                    print(f"\n\033[90m{status_label}  {original_sentence}\033[0m\n")
                else:
                    prompt_label = "✍️  Đáp án: " if mode == "W" else "🗣️  Phát âm: "
                    while True:
                        raw_ans = quiz_input(prompt_label)

                        # Check for single space hint
                        if raw_ans == " ":
                            has_used_hint = True
                            hints = []
                            for idx, expected_target in enumerate(targets_list):
                                clean_target = expected_target.replace("**", "").lower().strip()
                                matched_item = None
                                for item in q_data["words_info"]:
                                    if item["word"].lower() in clean_target or clean_target in item["word"].lower():
                                        matched_item = item
                                        break
                                if not matched_item and q_data["words_info"]:
                                    matched_item = q_data["words_info"][min(idx, len(q_data["words_info"])-1)]
                                clean_hint = clean_terminal_output(matched_item["meaning"]) if matched_item else "gợi ý"
                                hints.append(f"{clean_target}: {clean_hint}")
                            print("\033[90m", end="")
                            for h in hints:
                                print(f"• {h}")
                            print("\033[0m\n")
                            continue

                        ans = raw_ans.strip()
                        if ans == ".":
                            os.system('clear' if os.name != 'nt' else 'cls')
                            redo_question = True
                            break
                        elif ans == "..":
                            save_all_scores(scores_db)
                            show_header(q_index)
                            show_question(q_data)
                            continue
                        elif ans == "...":
                            print_progress_table(scores_db, mode)
                            show_header(q_index)
                            show_question(q_data)
                            continue
                        elif ans == ".m":
                            is_muted = not is_session_muted(active_session)
                            active_session["mute"] = is_muted
                            save_sessions(master_sessions)
                            if is_muted:
                                print("\n🔇 Đã tắt âm thanh (Muted)\n")
                            else:
                                print("\n🔊 Đã bật âm thanh (Unmuted)\n")
                            show_header(q_index)
                            show_question(q_data)
                            continue
                        elif ans == ".h":
                            print_shortcuts_guide("quiz_input")
                            show_header(q_index)
                            show_question(q_data)
                            continue
                        elif ans == "?":
                            has_used_hint = True
                            hints = []
                            for idx, expected_target in enumerate(targets_list):
                                clean_target = expected_target.replace("**", "").lower().strip()
                                matched_item = None
                                for item in q_data["words_info"]:
                                    if item["word"].lower() in clean_target or clean_target in item["word"].lower():
                                        matched_item = item
                                        break
                                if not matched_item and q_data["words_info"]:
                                    matched_item = q_data["words_info"][min(idx, len(q_data["words_info"])-1)]
                                clean_hint = clean_terminal_output(matched_item["meaning"]) if matched_item else "gợi ý"
                                hints.append(f"{clean_target}: {clean_hint}")
                            print("\033[90m", end="")
                            for h in hints:
                                print(f"• {h}")
                            print("\033[0m\n")
                            continue
                        else:
                            provided_answers = parse_answers(ans, targets_list)
                            for idx, expected_target in enumerate(targets_list):
                                expected = expected_target.lower().strip()
                                provided = ""
                                if idx < len(provided_answers):
                                    provided = provided_answers[idx].lower().strip()
                                if provided == expected:
                                    correct_count += 1
                            break

                    if aborted:
                        break
                    if redo_question:
                        continue
                    is_sentence_correct = (correct_count == len(targets_list))
                    is_passed = is_sentence_correct and not has_used_hint

                    if is_sentence_correct:
                        status_label = "🔄" if has_used_hint else "✅"
                    else:
                        status_label = "❌"

                    print(f"\n\033[90m{status_label}  {original_sentence}\033[0m\n")

                    if not is_sentence_correct and targets_list:
                        print(f"\033[93m⚠️  Chi tiết kết quả ({len(provided_answers)}/{len(targets_list)} ô):\033[0m")
                        for idx, expected_target in enumerate(targets_list, 1):
                            expected = expected_target.replace("**", "").strip()
                            provided = provided_answers[idx - 1].strip() if (idx - 1) < len(provided_answers) else ""
                            if provided.lower() == expected.lower():
                                print(f"  \033[90m• Ô [{idx}]: \033[92m{provided}\033[90m ✅\033[0m")
                            else:
                                if not provided:
                                    print(f"  \033[90m• Ô [{idx}]: (Chưa nhập) ❌ ➔ Đáp án đúng: \033[92m{expected}\033[0m")
                                else:
                                    print(f"  \033[90m• Ô [{idx}]: Bạn nhập '\033[91m{provided}\033[90m' ❌ ➔ Đáp án đúng: \033[92m{expected}\033[0m")
                        print()

                    if not is_session_muted(active_session):
                        speak_sentence(original_sentence)

                    if q_data["ipa"]:
                        clean_ipa = clean_terminal_output(q_data["ipa"])
                        print(f"\033[90m🗣️  /{clean_ipa}/\033[0m")

                # Store old scores for comparison
                old_scores = {}
                for target_item in q_data["words_info"]:
                    w_name = target_item["word"]
                    old_scores[w_name] = scores_db[w_name][mode_index]

                if not redo_question:
                    # Update local scores database (cap at target_level)
                    for target_item in q_data["words_info"]:
                        word_name = target_item["word"]
                        if is_passed:
                            scores_db[word_name][mode_index] = min(target_level, scores_db[word_name][mode_index] + 1)

                    # Repeat question if it was not passed, or if any of its words are still below target_level
                    should_repeat = not is_passed
                    if is_passed:
                        for target_item in q_data["words_info"]:
                            word_name = target_item["word"]
                            if scores_db[word_name][mode_index] < target_level:
                                should_repeat = True
                                break

                    if should_repeat:
                        tested_sentences.append(q_data)

                if mode in ["N", "K"]:
                    os.system('clear' if os.name != 'nt' else 'cls')
                    if redo_question:
                        continue
                    else:
                        q_index += 1
                        continue

                if mode not in ["N", "K"]:
                    # Display scores
                    print()
                    for target_item in q_data["words_info"]:
                        word_name = target_item["word"]
                        w_val, s_val, n_val = scores_db[word_name][0], scores_db[word_name][1], scores_db[word_name][2]
                        new_val = w_val if mode == "W" else (s_val if mode == "S" else n_val)
                        op = "+=" if (is_passed and new_val > old_scores[word_name]) else "=="
                        if mode == "W":
                            print(f"\033[90m• {word_name}: W{op}{w_val}\033[0m")
                        elif mode == "S":
                            print(f"\033[90m• {word_name}: S{op}{s_val}\033[0m")

                # Wait for user confirmation to continue before moving to the next question
                print()
                redo_question = False
                while True:
                    next_action = quiz_input("👉 Tiếp tục: ").strip()
                    if next_action == "":
                        # Clear console for the next question
                        os.system('clear' if os.name != 'nt' else 'cls')
                        break
                    elif next_action == ".":
                        # Restore old scores
                        for target_item in q_data["words_info"]:
                            word_name = target_item["word"]
                            scores_db[word_name][mode_index] = old_scores[word_name]
                        # Remove from repeat queue if it was appended
                        if should_repeat:
                            tested_sentences.pop()
                        # Clear console
                        os.system('clear' if os.name != 'nt' else 'cls')
                        redo_question = True
                        break
                    elif next_action == "..":
                        save_all_scores(scores_db)
                        print("\n💾 Đã lưu tạm tiến độ!\n")
                        continue
                    elif next_action == "...":
                        print_progress_table(scores_db, mode)
                        continue
                    elif next_action == ".m":
                        is_muted = not is_session_muted(active_session)
                        active_session["mute"] = is_muted
                        save_sessions(master_sessions)
                        if is_muted:
                            print("\n🔇 Đã tắt âm thanh (Muted)\n")
                        else:
                            print("\n🔊 Đã bật âm thanh (Unmuted)\n")
                        continue
                    elif next_action == ".h":
                        print_shortcuts_guide("quiz_pause")
                        continue
                    elif next_action.startswith(".w") or next_action.startswith(".p") or next_action.startswith(".s"):
                        handle_audio_shortcut(next_action, targets_list, original_sentence)
                        continue
                    else:
                        print("⚠️ Lệnh không hợp lệ. Gõ Enter để tiếp tục, hoặc gõ .h để xem phím tắt.\n")
                        continue

                if redo_question:
                    continue

                q_index += 1

            # Save final results on completion or exit
            save_all_scores(scores_db)
            session_state = None

            # Calculate words left below T
            words_under_T = []
            for word_item in words_db:
                w_name = word_item["word"]
                if scores_db.get(w_name, [0,0,0,0,0])[mode_index] < target_level:
                    words_under_T.append(w_name)

            print("\n==================================================")
            if not words_under_T:
                print(f"🏆 Hoàn thành buổi học! Tất cả từ vựng đã đạt {target_level} điểm.")
            else:
                print("👋 Đã kết thúc buổi học.")
            print("==================================================")

            # Prompt for final actions
            while True:
                try:
                    choice = quiz_input("\n📊 Xem bảng điểm? (y: Xem, .r: Học lại, Enter: Thoát): ").strip().lower()
                except (KeyboardInterrupt, EOFError):
                    print("\n👋 Hẹn gặp lại bạn lần sau!")
                    sys.exit(0)

                if choice in ["...", "y", "c"]:
                    print_progress_table(scores_db, mode)
                    try:
                        choice2 = quiz_input(".r: Học lại, Enter: Thoát: ").strip().lower()
                    except (KeyboardInterrupt, EOFError):
                        print("\n👋 Hẹn gặp lại bạn lần sau!")
                        sys.exit(0)
                    if choice2 == ".r":
                        os.execv(sys.executable, [sys.executable] + sys.argv)
                    else:
                        print("👋 Hẹn gặp lại bạn lần sau!")
                        sys.exit(0)
                elif choice == ".r":
                    os.execv(sys.executable, [sys.executable] + sys.argv)
                elif choice == "":
                    print("👋 Hẹn gặp lại bạn lần sau!")
                    sys.exit(0)
                else:
                    print("⚠️ Lựa chọn không hợp lệ. Vui lòng nhập lại.")


            # If everything completes normally, return
            return

        except GoBackException:
            if in_quiz_phase:
                # Clear screen and loop back to session selection
                os.system('clear' if os.name != 'nt' else 'cls')
                print(f"📖 Bài học: {lesson_title}")
                print(f"👤 Học viên: {username}\n")
                print_shortcuts_guide("session_select")
                continue
            else:
                # If .b was typed during session selection/creation, bubble up to level selection
                raise
        except QuitException:
            if 'scores_db' in locals():
                try:
                    save_all_scores(scores_db)
                except:
                    pass
            print("\n👋 Tạm biệt!")
            sys.exit(0)
        except RestartException:
            if 'scores_db' in locals():
                try:
                    save_all_scores(scores_db)
                except:
                    pass
            restart_quiz()
        except RestartSessionException:
            os.system('clear' if os.name != 'nt' else 'cls')
            print("🔄 Đang khởi động lại phiên học từ CH 1...")
            time.sleep(0.5)
            continue
def main():
    while True:
        try:
            run_session()
            break
        except GoBackException:
            os.system('clear' if os.name != 'nt' else 'cls')
            continue
        except RestartException:
            restart_quiz()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n==================================================")
        print("👋 Đã thoát buổi học bằng phím tắt. Hẹn gặp lại!")
        print("==================================================")
        sys.exit(0)
