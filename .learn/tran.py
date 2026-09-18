#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import re
import json
import urllib.request
import urllib.parse

# ANSI Colors
GREY = "\033[90m"
RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"

def print_divider():
    print(f"{GREY}--------------------------------------------------{RESET}")

def fetch_translation_online(text):
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=vi&dt=t&q={urllib.parse.quote(text)}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                translated_parts = [part[0] for part in data[0] if part[0]]
                translated_text = "".join(translated_parts).strip()
                return translated_text
    except Exception:
        pass
    return None

def fetch_word_ipa_online(word):
    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(word)}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
            if isinstance(data, list) and len(data) > 0:
                entry = data[0]
                phonetics = entry.get("phonetics", [])
                for ph in phonetics:
                    text = ph.get("text", "")
                    if text:
                        return text.strip("/").strip("[").strip("]")
    except Exception:
        pass
    return None

def load_ipa_cache(cache_file):
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {}

def save_ipa_cache(cache_file, cache):
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def clean_english_sentence(sentence):
    # Remove leading emojis and numbering
    cleaned = re.sub(r'^[0-9.\s]+', '', sentence) # remove numbering
    cleaned = re.sub(r'^[\U00010000-\U0010ffff\u2600-\u27ff\u2190-\u21ff]\s*', '', cleaned) # remove lead emoji
    cleaned = cleaned.strip()
    return cleaned

class GoBackException(Exception): pass
class QuitException(Exception): pass
class RestartException(Exception): pass

def tran_input(prompt):
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
        return val

def run_main():
    os.system('clear' if os.name != 'nt' else 'cls')
    target_dir = os.getcwd()
    clean_mode = False

    for arg in sys.argv[1:]:
        if arg in ["--clean", "-c", "--reset", "-r"]:
            clean_mode = True
        elif os.path.isdir(arg):
            target_dir = os.path.abspath(arg)

    prepare_file = os.path.join(target_dir, "🪺 prepare.md")
    legacy_prep = os.path.join(target_dir, "prepare.md")
    existing_file = prepare_file if os.path.exists(prepare_file) else (legacy_prep if os.path.exists(legacy_prep) else None)

    if clean_mode:
        deleted_any = False
        for f in [prepare_file, legacy_prep]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                    print(f"  🗑️  Đã xóa bản dịch: {os.path.basename(f)}")
                    deleted_any = True
                except Exception as e:
                    print(f"{RED}❌ Không thể xóa {os.path.basename(f)}: {e}{RESET}")
        if deleted_any:
            print(f"{GREEN}✅ Đã reset bài học về trạng thái chưa dịch!{RESET}\n")
        else:
            print(f"{YELLOW}⚠️  Bài học này hiện chưa có bản dịch nào để xóa.{RESET}\n")
        sys.exit(0)

    # Check if translation already exists
    if existing_file:
        print(f"\n{YELLOW}📊 Bản dịch '{os.path.basename(existing_file)}' đã tồn tại.{RESET}\n")
        print("  [1] Dịch lại / Ghi đè bản dịch cũ (⭐)")
        print("  [2] Xóa bản dịch (Dọn dẹp)")
        print("  [3] Hủy bỏ")
        print()

        choice = tran_input(f"{GREY}Chọn (1-3): {RESET}").strip()

        if choice in ["", "1"]:
            print(f"\n🔄 Đang dịch đè lên bản dịch cũ...\n")
        elif choice == "2":
            try:
                os.remove(existing_file)
                print(f"\n{GREEN}🗑️  Đã xóa bản dịch thành công!{RESET}\n")
            except Exception as e:
                print(f"\n{RED}❌ Lỗi khi xóa file: {e}{RESET}\n")
            sys.exit(0)
        else:
            print(f"\n{GREY}Hủy bỏ thao tác.{RESET}\n")
            sys.exit(0)

    # Find lesson file
    lesson_file = os.path.join(target_dir, "💧 lesson.md")
    if not os.path.exists(lesson_file):
        lesson_file = os.path.join(target_dir, "lesson.md")
        if not os.path.exists(lesson_file):
            print(f"{RED}❌ Lỗi: Không tìm thấy tệp '💧 lesson.md' hoặc 'lesson.md' tại {target_dir}.{RESET}")
            sys.exit(1)

    # Parse lesson sentences
    sentences = []
    lesson_title = os.path.basename(target_dir)

    with open(lesson_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    in_fm = False
    for line in lines:
        line_str = line.strip()
        if line_str == "---":
            in_fm = not in_fm
            continue
        if in_fm:
            continue
        if line_str.startswith("#"):
            lesson_title = line_str.lstrip("#").strip()
            continue

        # Match numbered sentences
        match = re.match(r"^(\d+)\.\s*(.*)$", line_str)
        if match:
            stt = int(match.group(1))
            eng_raw = match.group(2).strip()
            sentences.append((stt, eng_raw))

    if not sentences:
        print(f"{RED}❌ Lỗi: Không tìm thấy danh sách câu có đánh số trong {os.path.basename(lesson_file)}.{RESET}")
        sys.exit(1)

    print(f"\n{GREEN}🏁 BẮT ĐẦU DỊCH & TẠO PHIÊN ÂM THÔ:{RESET}")
    print(f"  - Bài học: {lesson_title}")
    print(f"  - Số lượng câu: {len(sentences)}")
    print_divider()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    cache_file = os.path.join(script_dir, "ipa-cache.json")
    ipa_cache = load_ipa_cache(cache_file)

    prepare_rows = []
    cache_updated = False

    for idx, (stt, eng_raw) in enumerate(sentences, 1):
        eng_clean = clean_english_sentence(eng_raw)
        print(f"[{stt}/{len(sentences)}] Processing: {eng_clean}...")

        # 1. Translation
        vi_trans = fetch_translation_online(eng_clean)
        if not vi_trans:
            vi_trans = f"[Dịch: {eng_clean}]"
            print(f"  {YELLOW}⚠️  Mất kết nối/Không thể dịch, dùng placeholder.{RESET}")
        else:
            print(f"  {GREY}💬  Dịch: {vi_trans}{RESET}")

        # 2. IPA Generation
        words_in_sentence = re.findall(r"[a-zA-Z']+", eng_clean)
        ipa_list = []
        for word in words_in_sentence:
            w_lower = word.lower()
            if w_lower in ipa_cache:
                ipa_list.append(ipa_cache[w_lower])
            else:
                print(f"   - Tra từ '{w_lower}'...", end="", flush=True)
                ipa_val = fetch_word_ipa_online(w_lower)
                if ipa_val:
                    ipa_cache[w_lower] = ipa_val
                    cache_updated = True
                    ipa_list.append(ipa_val)
                    print(f" {GREEN}{ipa_val}{RESET}")
                else:
                    ipa_list.append(word)
                    print(f" {YELLOW}(Không tìm thấy){RESET}")

        sentence_ipa = " ".join(ipa_list)
        print(f"  {GREY}🔊  IPA: {sentence_ipa}{RESET}")
        print_divider()

        prepare_rows.append((stt, eng_clean, vi_trans, sentence_ipa))

    if cache_updated:
        save_ipa_cache(cache_file, ipa_cache)

    # Write to prepare.md
    with open(prepare_file, "w", encoding="utf-8") as f:
        f.write("| STT | English | Vietnamese | IPA |\n")
        f.write("| :---: | :--- | :--- | :--- |\n")
        for stt, eng, vi, ipa in prepare_rows:
            eng = eng.replace("|", "\\|")
            vi = vi.replace("|", "\\|")
            ipa = ipa.replace("|", "\\|")
            f.write(f"| {stt} | {eng} | {vi} | {ipa} |\n")

    print(f"\n{GREEN}✅ Đã tạo thành công tệp '{os.path.basename(prepare_file)}'!{RESET}")
    print(f"{GREY}💡 Mẹo: Khi có Internet hoặc sử dụng AI Pro, bạn có thể gọi @pre duyệt lại file để chỉnh sửa các lỗi phát âm/dịch nghĩa thô.{RESET}\n")

def main():
    try:
        run_main()
    except GoBackException:
        print(f"\n{GREY}Quay lại bước trước.{RESET}\n")
        sys.exit(0)
    except QuitException:
        print(f"\n{YELLOW}👋 Tạm biệt! Hẹn gặp lại.{RESET}\n")
        sys.exit(0)
    except RestartException:
        print("🔄 Đang khởi động lại tran.py...")
        import time
        time.sleep(0.5)
        os.execv(sys.executable, [sys.executable] + sys.argv)

if __name__ == "__main__":
    main()
