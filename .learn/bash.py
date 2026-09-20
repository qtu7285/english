#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import shutil
import time

MARKER_START = "# >>> AGY LANGUAGE ALIASES >>>"
MARKER_END = "# <<< AGY LANGUAGE ALIASES <<<"

def update_unix_config(file_path, workspace_path):
    if not os.path.exists(file_path):
        return False

    alias_block = f"""{MARKER_START}
alias .e='cd "{workspace_path}"'
alias .m='python3 "{workspace_path}/.learn/move.py"; if [ -f "$HOME/.move_cd" ]; then cd "$(cat "$HOME/.move_cd")" && rm "$HOME/.move_cd"; fi'
alias .q='python3 "{workspace_path}/.learn/quiz.py"'
alias .p='python3 "{workspace_path}/.learn/prep.py"'
alias .t='python3 "{workspace_path}/.learn/tran.py"'
alias .res='bash "{workspace_path}/app/run.sh"'
{MARKER_END}"""

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if MARKER_START in content and MARKER_END in content:
            # Replace existing block
            start_idx = content.find(MARKER_START)
            end_idx = content.find(MARKER_END) + len(MARKER_END)
            new_content = content[:start_idx] + alias_block + content[end_idx:]
        else:
            # Append block
            new_content = content.rstrip() + "\n\n" + alias_block + "\n"

        if new_content == content:
            return True
        shutil.copy2(file_path, f"{file_path}.learn-backup-{time.time_ns()}")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True
    except Exception as e:
        print(f"[X] Lỗi khi cập nhật {file_path}: {e}")
        return False

def update_windows_config(file_path, workspace_path):
    # Ensure directory exists
    dir_name = os.path.dirname(file_path)
    if not os.path.exists(dir_name):
        try:
            os.makedirs(dir_name)
        except Exception:
            pass

    alias_block = f"""{MARKER_START}
function .e {{ Set-Location "{workspace_path}" }}
function .m {{
    python "{workspace_path}\\.learn\\move.py"
    $cdFile = Join-Path $HOME ".move_cd"
    if (Test-Path $cdFile) {{
        $target = Get-Content $cdFile -Raw
        Set-Location $target.Trim()
        Remove-Item $cdFile
    }}
}}
function .q {{ python "{workspace_path}\\.learn\\quiz.py" }}
function .p {{ python "{workspace_path}\\.learn\\prep.py" }}
function .t {{ python "{workspace_path}\\.learn\\tran.py" }}
function .res {{ bash "{workspace_path}\\app\\run.sh" }}
{MARKER_END}"""

    try:
        content = ""
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

        if MARKER_START in content and MARKER_END in content:
            start_idx = content.find(MARKER_START)
            end_idx = content.find(MARKER_END) + len(MARKER_END)
            new_content = content[:start_idx] + alias_block + content[end_idx:]
        else:
            new_content = content.rstrip() + "\n\n" + alias_block + "\n"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True
    except Exception as e:
        print(f"[X] Lỗi khi cập nhật PowerShell profile {file_path}: {e}")
        return False

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_root = os.path.dirname(script_dir)
    home = os.path.expanduser("~")

    # Check if workspace is inside home
    is_inside_home = False
    try:
        real_workspace = os.path.realpath(workspace_root)
        real_home = os.path.realpath(home)
        if real_workspace == real_home or real_workspace.startswith(real_home + os.sep):
            is_inside_home = True
    except Exception:
        pass

    print("[~] Đang khởi tạo alias hệ thống...")

    is_windows = os.name == 'nt'

    if is_windows:
        # Windows PowerShell configuration
        if is_inside_home:
            rel_path = os.path.relpath(workspace_root, home)
            workspace_path = f"$HOME\\{rel_path}"
        else:
            workspace_path = workspace_root

        # Get PowerShell profile path
        try:
            ps_profile = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", "$PROFILE"],
                text=True
            ).strip()
        except Exception:
            ps_profile = os.path.join(home, "Documents", "WindowsPowerShell", "Microsoft.PowerShell_profile.ps1")

        if update_windows_config(ps_profile, workspace_path):
            print(f"[OK] Đã cấu hình alias thành công tại PowerShell profile!")
            print(f"[~] Đường dẫn profile: {ps_profile}")
            print("[NEXT] Hãy khởi động lại PowerShell hoặc chạy: . $PROFILE để áp dụng.")
        else:
            print("[X] Không thể cấu hình alias cho Windows PowerShell.")

    else:
        # Unix (Termux/Linux/macOS) configuration
        real_workspace = os.path.realpath(workspace_root)
        if "/storage/emulated/0" in real_workspace and os.path.exists(os.path.expanduser("~/storage/shared")):
            rel_to_shared = os.path.relpath(real_workspace, "/storage/emulated/0").replace(os.sep, '/')
            workspace_path = f"$HOME/storage/shared/{rel_to_shared}"
        elif is_inside_home:
            rel_path = os.path.relpath(workspace_root, home).replace(os.sep, '/')
            workspace_path = f"$HOME/{rel_path}"
        else:
            workspace_path = workspace_root.replace(os.sep, '/')

        configs = [
            os.path.join(home, ".bashrc"),
            os.path.join(home, ".zshrc")
        ]

        updated_count = 0
        for config in configs:
            if os.path.exists(config):
                if update_unix_config(config, workspace_path):
                    print(f"[OK] Đã cấu hình alias thành công tại {config}!")
                    updated_count += 1

        # If no config files existed, create .bashrc by default
        if not any(os.path.exists(config) for config in configs):
            default_bashrc = os.path.join(home, ".bashrc")
            try:
                with open(default_bashrc, "w", encoding="utf-8") as f:
                    f.write("# Bash configuration\n")
                if update_unix_config(default_bashrc, workspace_path):
                    print(f"[OK] Đã tạo mới và cấu hình alias thành công tại {default_bashrc}!")
                    updated_count += 1
            except Exception as e:
                print(f"[X] Không thể tạo default .bashrc: {e}")

        if updated_count > 0:
            print("[NEXT] Hãy chạy lệnh: source ~/.bashrc (hoặc source ~/.zshrc) để áp dụng ngay.")

if __name__ == "__main__":
    main()
