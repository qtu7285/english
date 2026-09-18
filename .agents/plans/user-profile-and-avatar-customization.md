# Kế hoạch Hồ sơ Người học & Cá nhân hóa Avatar

Tài liệu đặc tả và kế hoạch triển khai thư mục `USERS/`, cấu hình hồ sơ người học và tính năng chọn Avatar cho User & AI trên giao diện English Tutor.

---

## 1. Bối cảnh & Mục tiêu

- Giao diện chat trước đây hiển thị chữ "YOU" và "AI" trong vòng tròn đơn sắc, thiếu tính sinh động và cá nhân hóa.
- Hệ thống hỗ trợ đa người học theo định danh `#username` (mặc định: `qtu`). Cần một nơi lưu trữ cấu hình riêng cho từng người học mà không làm xáo trộn kho từ vựng chuẩn trong `WORDS/`.
- Thư mục `USERS/` (viết hoa toàn bộ theo chuẩn repo) cùng các thư mục con `USERS/<username>/` (viết thường) cung cấp không gian lưu trữ file `profile.json` chứa avatar, model, giọng đọc và thiết lập cá nhân.

---

## 2. Danh mục Công việc (Work Breakdown Checklist)

- [x] **Bước 1: Khởi tạo Thư mục Chuẩn `USERS/` và Tài liệu Đặc tả**
  - [x] Tạo `USERS/qtu/profile.json` với cấu hình mặc định.
  - [x] Tạo đặc tả kiến trúc [`USERS/README.md`](file:///data/data/com.termux/files/home/storage/shared/LANGUAGE/english/USERS/README.md).

- [x] **Bước 2: Triển khai API Quản lý Hồ sơ Người học trong Golang**
  - [x] Thêm endpoint `/api/user/profile` (GET, POST) trong [`app/api/main.go`](file:///data/data/com.termux/files/home/storage/shared/LANGUAGE/english/app/api/main.go).
  - [x] Validate định dạng username theo regex `^[a-z0-9][a-z0-9_-]*$`.
  - [x] Đọc và lưu file `profile.json` vào `USERS/<username>/`.
  - [x] Biên dịch lại nhị phân `english-server` bằng `app/build.sh`.

- [x] **Bước 3: Bổ sung Giao diện Chọn Avatar & Người học trong Modal Cài đặt**
  - [x] Thêm mục nhập Username và chọn Avatar Người học (User) & Trợ lý (AI) trong [`index.html`](file:///data/data/com.termux/files/home/storage/shared/LANGUAGE/english/app/web/index.html).
  - [x] Cung cấp các bộ avatar sinh động (🧑‍🎓, 🦊, 🦉, 🚀, 🐱, 🦁, 🧑‍💻 / 🤖, 🧙‍♂️, 🧠, 🦉, ⚡, 💎) kèm ô nhập tùy chọn.
  - [x] Bổ sung kiểu dáng avatar grid picker trong [`style.css`](file:///data/data/com.termux/files/home/storage/shared/LANGUAGE/english/app/web/style.css).

- [x] **Bước 4: Đồng bộ Dữ liệu & Cập nhật Bong bóng Chat trong `app.js`**
  - [x] Nạp cấu hình từ `/api/user/profile` hoặc localStorage khi khởi động app.
  - [x] Lưu hồ sơ lên server khi bấm "Lưu Cài đặt".
  - [x] Hiển thị avatar đã chọn trên các tin nhắn chat người dùng và trợ lý.
  - [x] Cập nhật tin nhắn chào đầu tiên với avatar AI đã chọn.
  - [x] Tự động chuyển đổi người học khi gõ lệnh `#username` trong chat.

- [x] **Bước 5: Nâng cấp Cache Service Worker & Kiểm thử Đồng bộ**
  - [x] Nâng cấp cache lên `engtutor-v6` trong [`sw.js`](file:///data/data/com.termux/files/home/storage/shared/LANGUAGE/english/app/web/sw.js).
  - [x] Khởi động lại daemon `english-server` và kiểm tra phản hồi API thành công.

---

## 3. Tiêu chuẩn Nghiệm thu

1. [x] Thư mục `USERS/` và `USERS/qtu/profile.json` tồn tại trên đĩa, tuân thủ đúng chuẩn định danh của repo.
2. [x] API `/api/user/profile?username=qtu` trả về thông tin profile định dạng JSON hợp lệ.
3. [x] Trong modal Cài đặt, người dùng có thể đổi username và chọn avatar cho mình cũng như cho AI.
4. [x] Khung chat hiển thị avatar sinh động thay cho chữ "YOU" và "AI" đơn điệu.
5. [x] Cài đặt được lưu đồng thời vào cả localStorage và `USERS/<username>/profile.json`.
