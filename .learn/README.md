# Công cụ Termux

Vị trí chung trên hai máy: `/storage/emulated/0/LANGUAGE/english/.learn`.

Cài hoặc cập nhật alias sau khi clone/pull:

```sh
cd /storage/emulated/0/LANGUAGE/english
python3 .learn/bash.py
source ~/.bashrc
```

- `.e`: vào repo english.
- `.m`: mở trình duyệt thư mục từ thư mục hiện tại; `@en` vào repo, `.cd` thoát và chuyển thư mục shell.
- `.q`, `.p`, `.t`: chạy quiz, chuẩn bị bài, dịch tại thư mục bài học hiện tại.

`bash.py` tự xác định đường dẫn từ vị trí script và sao lưu cấu hình shell trước khi sửa.
Máy mới mặc định có bookmark và alias `@en` trỏ đến repo.
Bookmark (`working_dirs.json`), alias thư mục (`path_aliases.json`), cache và trạng thái chạy là dữ liệu từng máy, được Git bỏ qua.
Các bài học cũ ngoài repo chưa được di chuyển; bookmark của chúng vẫn trỏ tới vị trí thật trên máy có dữ liệu.
Các công cụ bài học JSON cũ không thay thế workflow CSV trong `WORDS`.

Cập nhật mã trên máy còn lại bằng `git pull --ff-only`. Chạy lại `bash.py` nếu vị trí repo hoặc alias thay đổi.
