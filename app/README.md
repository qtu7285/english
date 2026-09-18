# English Tutor & Vault AI Web App

Ứng dụng web cục bộ (Local Web App) chạy trên Termux, cho phép bạn học tiếng Anh qua giao diện web trực quan trên trình duyệt điện thoại thay vì phải chat trực tiếp trong cửa sổ terminal.

---

## 1. Động cơ Golang (High Performance & Ultra Lightweight)

Hệ thống được chuyển đổi hoàn toàn sang **Golang**:
* **Bộ nhớ RAM cực thấp:** Chỉ chiếm ~**10MB RAM** khi chạy nền (so với ~50MB của Python).
* **Mát máy, tiết kiệm pin:** Tận dụng đa luồng thực thụ trên ARM64, CPU gần như 0% khi chờ.
* **Thời gian build:** Chỉ mất ~2-3 giây trên Termux.
* **Tự động chuyển đổi:** Script `run.sh` tự động biên dịch và chạy Golang binary tại `$HOME/.local/bin/english-server`, có cơ chế fallback về Python nếu máy chưa cài Go.

---

## 2. Cấu trúc thư mục

```
app/
├── api/
│   ├── main.go         # Máy chủ HTTP Go, định tuyến API & phục vụ Web tĩnh
│   ├── vault.go        # Module quản lý Vault an toàn (Go)
│   ├── gemini.go       # Kết nối Gemini API với Function Calling & Auto-Retry (Go)
│   ├── server.py       # Bản sao lưu dự phòng Python
│   ├── vault.py        # Bản sao lưu dự phòng Python
│   └── gemini.py       # Bản sao lưu dự phòng Python
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
