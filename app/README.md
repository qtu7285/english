# English Tutor & Vault AI Web App

Ứng dụng web cục bộ (Local Web App) chạy trên Termux, cho phép bạn học tiếng Anh qua giao diện web trực quan trên trình duyệt điện thoại thay vì phải chat trực tiếp trong cửa sổ terminal.

---

## 1. Động cơ Golang 100% (High Performance & Ultra Lightweight)

Hệ thống được chuyển đổi hoàn toàn sang **Golang thuần**, loại bỏ hoàn toàn Python:
* **Bộ nhớ RAM cực thấp:** Chỉ chiếm ~**9.7MB RAM** khi chạy nền (so với ~50MB của Python).
* **Mát máy, tiết kiệm pin:** Tận dụng đa luồng thực thụ trên ARM64, CPU gần như 0% khi chờ.
* **Thời gian build:** Chỉ mất ~2 giây trên Termux (`bash app/build.sh`).
* **Hỗ trợ 2 chế độ AI Engine:**
  1. **Antigravity CLI (Termux Pro):** Sử dụng trực tiếp tài khoản Pro đã đăng nhập trên Termux qua lệnh `agy`, không cần nhập API Key, không lo bị giới hạn hạn mức (Quota 429) hay 503.
  2. **Google Gemini REST API:** Kết nối trực tiếp qua API Key, phản hồi siêu tốc (~1 giây).

---

## 2. Cấu trúc thư mục

```
app/
├── api/
│   ├── main.go         # Máy chủ HTTP Go, định tuyến API & phục vụ Web tĩnh
│   ├── vault.go        # Module quản lý Vault an toàn (Go)
│   ├── antigravity.go  # Tích hợp Antigravity CLI Pro trên Termux (Go)
│   └── gemini.go       # Kết nối Gemini REST API với Function Calling & Thought Signatures (Go)
├── web/
│   ├── index.html      # Giao diện web mobile-friendly
│   ├── style.css       # Giao diện Dark theme, nút phát âm cuối câu
│   └── app.js          # Logic trò chuyện, phát âm Web Speech API, phím tắt A/B/C/D
├── build.sh            # Script biên dịch Go engine
├── run.sh              # Script khởi chạy 1 chạm
└── README.md
```

---

## 3. Cách khởi chạy trên Termux

Từ thư mục repo `english`, gõ lệnh:

```bash
bash app/run.sh
```

Hoặc chỉ định cổng khác nếu cổng 5000 đang bận:

```bash
bash app/run.sh 8080
```

Script sẽ khởi động server Go và tự động mở trình duyệt tới địa chỉ:
* Trên máy: `http://localhost:5000`
* Qua Tailscale: `http://zf3:5000` hoặc `http://100.70.156.102:5000`

---

## 4. Các tính năng nổi bật

* **Phát âm cuối câu `[🔊]`:** Bấm nút loa ở cuối từng câu ví dụ để nghe phát âm tiếng Anh chuẩn bằng Web Speech API của trình duyệt.
* **Phím tắt đáp án `[A] [B] [C] [D]`:** Trả lời trắc nghiệm 1 chạm ngay trên thanh công cụ.
* **Luyện tập từng câu một:** Khi chọn 3 câu hoặc 5 câu, hệ thống hiển thị từng câu (Câu 1/N) để bạn trả lời, chấm điểm xong mới chuyển sang câu kế tiếp.
* **Tương tác trực tiếp với Vault & WORDS:** Tự động đọc danh sách từ vựng, tìm kiếm và chèn ghi chú.
* **Hỗ trợ đa mô hình:** Gemini 3.6 Flash, 3.7 Flash, 3.8 Flash, 2.0 Flash, 1.5 Flash và tuỳ chỉnh.
