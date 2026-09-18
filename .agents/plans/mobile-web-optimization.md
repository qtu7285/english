# Kế hoạch Tối ưu Giao diện Web & API cho Màn hình Điện thoại

Tài liệu đặc tả và kế hoạch thực thi từng bước tối ưu giao diện Web UI và tương tác API của ứng dụng English Tutor AI trên thiết bị di động (Termux / Android / iOS).

---

## 1. Bối cảnh & Mục tiêu

Ứng dụng web cục bộ chạy trên Termux ([`app/`](file:///data/data/com.termux/files/home/storage/shared/LANGUAGE/english/app)) được thiết kế phục vụ việc học tiếng Anh trên điện thoại qua trình duyệt hoặc PWA. Qua khảo sát thực tế, một số điểm giao diện cần được tinh chỉnh để đạt trải nghiệm mượt mà, tiện dụng cho thao tác một tay bằng ngón cái (thumb-friendly) và tương thích hoàn toàn với các cơ chế đặc thù của trình duyệt di động.

---

## 2. Danh mục Cải tiến (Work Breakdown Checklist)

- [x] **Bước 1: Tối ưu Thẻ Viewport & Vùng an toàn (Safe Area Insets)**
  - [x] Thêm `interactive-widget=resizes-content` và `viewport-fit=cover` vào `<meta name="viewport">` trong [`index.html`](file:///data/data/com.termux/files/home/storage/shared/LANGUAGE/english/app/web/index.html).
  - [x] Bổ sung `env(safe-area-inset-bottom)` và `env(safe-area-inset-top)` trong [`style.css`](file:///data/data/com.termux/files/home/storage/shared/LANGUAGE/english/app/web/style.css) để tránh xung đột với thanh điều hướng cử chỉ (Android/iOS gesture bar) và tai thỏ.

- [x] **Bước 2: Tối ưu Thanh Header trên Màn hình Hẹp (< 600px)**
  - [x] Tự động ẩn nhãn chữ `.btn-label` trên các nút header (Cài đặt, Vault) trên mobile để không làm tràn chiều ngang.
  - [x] Tinh chỉnh khoảng cách padding và cỡ chữ tiêu đề gọn gàng.

- [x] **Bước 3: Khắc phục và Nâng cấp Trình duyệt Vault trên Di động**
  - [x] Sửa lỗi `.vault-preview` bị ẩn hoàn toàn (`display: none`) trên màn hình `< 600px`.
  - [x] Bổ sung cơ chế chuyển đổi Master-Detail: khi người dùng chọn file trên điện thoại, giao diện hiển thị khung xem trước kèm nút **[← Quay lại danh sách]** để người học dễ dàng đọc nội dung file trước khi chèn vào chat.

- [x] **Bước 4: Tăng kích thước Vùng chạm (Touch Targets)**
  - [x] Mở rộng vùng chạm của nút phát âm inline [🔊] (`.inline-audio-btn`) để ngón cái chạm dễ dàng, không bị chạm nhầm vào văn bản xung quanh.
  - [x] Tăng độ cao và padding của các nút gợi ý nhanh (`.chip`) trong thanh Quick Chips lên chuẩn cảm ứng (chiều cao 34-36px, padding rộng rãi).
  - [x] Tối ưu kích thước các nút trắc nghiệm [A], [B], [C], [D] (`.btn-bubble-choice`) và nút hành động dưới bong bóng chat (`.btn-action`).

- [x] **Bước 5: Tối ưu Trải nghiệm Nhập liệu & Bàn phím ảo**
  - [x] Đặt `font-size: 16px;` cho khung soạn thảo tin nhắn trên di động nhằm ngăn chặn trình duyệt Safari/iOS tự động zoom trang khi chạm vào ô gõ.
  - [x] Xử lý bộ gõ tiếng Việt (IME Composition): kiểm tra `e.isComposing` trước khi gửi bằng phím Enter để không ngắt từ khi người học đang gõ dấu tiếng Việt.

- [x] **Bước 6: Tối ưu Web Speech API & Phản hồi Rung (Haptic Feedback)**
  - [x] Đăng ký sự kiện `speechSynthesis.onvoiceschanged` trong [`app.js`](file:///data/data/com.termux/files/home/storage/shared/LANGUAGE/english/app/web/app.js) để nạp voice tiếng Anh chất lượng cao ngay khi trình duyệt khởi động.
  - [x] Bổ sung phản hồi rung nhẹ (`navigator.vibrate`) khi bấm chọn đáp án trắc nghiệm hoặc khi sao chép câu thành công trên thiết bị hỗ trợ.

- [x] **Bước 7: Tối ưu Placeholder & Tự động thêm dấu chấm `.` cho Từ vựng**
  - [x] Đặt placeholder ngắn gọn: `Nhập từ cần học...` trong [`index.html`](file:///data/data/com.termux/files/home/storage/shared/LANGUAGE/english/app/web/index.html).
  - [x] Trong [`app.js`](file:///data/data/com.termux/files/home/storage/shared/LANGUAGE/english/app/web/app.js), tự động chèn tiền tố `.` trước từ đơn tiếng Anh (ví dụ gõ `urge` tự động gửi `.urge`) mà người dùng không cần phải gõ dấu chấm thủ công.
  - [x] Kiểm tra thông minh: không chèn `.` nếu là số câu (`3`, `5`), lệnh (`.s`, `.g`, `.help`), đáp án trắc nghiệm (`A`, `B`, `C`, `D`), hoặc khi bài tập đang chờ câu trả lời.

- [x] **Bước 8: Tích hợp Live-Reload tự động bằng Golang thuần (Thay thế Vite)**
  - [x] Bổ sung module `LiveReloader` trong [`main.go`](file:///data/data/com.termux/files/home/storage/shared/LANGUAGE/english/app/api/main.go) với Server-Sent Events (SSE) `/api/live-reload`.
  - [x] Tự động theo dõi các tệp trong `app/web/` và gửi tín hiệu cho trình duyệt tải lại ngay lập tức khi phát hiện thay đổi.
  - [x] Không cần Node.js, không cần `node_modules`, giữ nguyên 100% Golang siêu nhẹ và mát máy trên Termux.

---

## 3. Tiêu chuẩn Nghiệm thu

1. [x] Giao diện hiển thị trọn vẹn, không bị tràn ngang ở mọi độ phân giải màn hình từ 360px trở lên.
2. [x] Khi bật bàn phím ảo, khung chat co giãn chuẩn xác, không che khuất ô nhập liệu.
3. [x] Thanh điều hướng cử chỉ đáy màn hình không đè lên thanh nhập liệu.
4. [x] Mở được nội dung file trong Vault trên điện thoại và quay lại danh sách bình thường.
5. [x] Chạm vào ô nhập liệu không bị phóng to màn hình trên iOS.
6. [x] Nhập một từ (ví dụ `urge`) tự động gửi `.urge` mà không cần người dùng gõ dấu chấm.
7. [x] Khi chỉnh sửa file CSS/JS/HTML, trình duyệt tự động cập nhật ngay lập tức nhờ Go Live-Reload.
