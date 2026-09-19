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

- [x] **Bước 9: Chuyển đổi Nút chọn số câu sang Cơ chế Ngữ cảnh Động (Context-Aware Chips)**
  - [x] Bỏ các nút `3 câu luyện`, `5 câu luyện` cố định ở thanh đáy trong [`index.html`](file:///data/data/com.termux/files/home/storage/shared/LANGUAGE/english/app/web/index.html).
  - [x] Trong [`app.js`](file:///data/data/com.termux/files/home/storage/shared/LANGUAGE/english/app/web/app.js), chỉ tự động hiện các nút chọn số câu (`3 câu luyện`, `5 câu luyện`, `10 câu`) sau khi AI giải nghĩa xong từ vựng (khi xuất hiện `[NEXT]`).
  - [x] Khi đang trong bài test (`Câu 1/N`, `Câu 2/N`...): ẩn hoàn toàn các nút chọn số câu, chỉ hiện các phím trắc nghiệm `[A] [B] [C] [D]` để người học tập trung trả lời và tuyệt đối không thể bấm nhầm làm hỏng bài test.

- [x] **Bước 10: Tích hợp Cử chỉ Vuốt xuống để Làm mới (Pull-to-Refresh)**
  - [x] Thêm thành phần hiển thị loading `#ptrIndicator`, `#ptrSpinner`, `#ptrLabel` trong [`index.html`](file:///data/data/com.termux/files/home/storage/shared/LANGUAGE/english/app/web/index.html).
  - [x] Định dạng hiệu ứng chuyển động mượt mà và biểu tượng xoay trong [`style.css`](file:///data/data/com.termux/files/home/storage/shared/LANGUAGE/english/app/web/style.css).
  - [x] Xử lý cảm ứng `touchstart`, `touchmove`, `touchend` với hiệu ứng co giãn đàn hồi (rubber-band) và phản hồi rung haptic khi đạt ngưỡng kích hoạt trong [`app.js`](file:///data/data/com.termux/files/home/storage/shared/LANGUAGE/english/app/web/app.js).

- [x] **Bước 11: Ẩn các nút lệnh `.` ban đầu & Khóa cố định Viewport chống che ô nhập liệu**
  - [x] Loại bỏ các nút lệnh cố định `.help`, `.s`, `.g` trong [`index.html`](file:///data/data/com.termux/files/home/storage/shared/LANGUAGE/english/app/web/index.html) và nút `.urge` ban đầu trong [`app.js`](file:///data/data/com.termux/files/home/storage/shared/LANGUAGE/english/app/web/app.js).
  - [x] Thanh Quick Chips tự động ẩn hoàn toàn khi không có chip nào để giao diện tối giản, thoáng mắt.
  - [x] Cố định `html`, `body` với `position: fixed; inset: 0; overscroll-behavior: none;`, `history.scrollRestoration = 'manual'`, và `flex-shrink: 0` trên `.app-footer`, `.app-header` cùng `min-height: 0` trên `.chat-viewport` nhằm triệt tiêu hoàn toàn hiện tượng lệch viewport hay che khuất ô gõ văn bản sau khi refresh.

- [x] **Bước 12: Tối giản Thanh Header - Gỡ bỏ Nút Vault và Modal Duyệt File khỏi Giao diện Học viên**
  - [x] Xóa nút `#vaultBtn` trên thanh Header trong [`index.html`](file:///data/data/com.termux/files/home/storage/shared/LANGUAGE/english/app/web/index.html).
  - [x] Xóa modal `#vaultModal` khỏi DOM, bọc an toàn các sự kiện trong [`app.js`](file:///data/data/com.termux/files/home/storage/shared/LANGUAGE/english/app/web/app.js).
  - [x] Nâng cấp Service Worker lên `engtutor-v6` trong [`sw.js`](file:///data/data/com.termux/files/home/storage/shared/LANGUAGE/english/app/web/sw.js).
  - [x] Thanh Header trên điện thoại giờ chỉ còn logo, nút Cài đặt và nút Xóa cuộc trò chuyện, cực kỳ thoáng mắt và tập trung 100% vào học tiếng Anh.

- [x] **Bước 13: Trực quan hóa nhãn ngôn ngữ và trạng thái bằng Emoji trên Web UI**
  - [x] Chuyển đổi nhãn ngôn ngữ văn bản thô `[EN]` thành cờ 🇬🇧 và `[VI]` thành cờ 🇻🇳 sắc nét, gọn gàng, bỏ hẳn chữ `[EN]` / `[VI]` rườm rà.
  - [x] Chuyển đổi các nhãn trạng thái khác thành emoji trực quan: `[OK]` -> ✅, `[X]` -> ❌, `[~]` -> ⚠️, `[RETRY]` -> 🔄, `[SAVE]` -> 💾, `[NEXT]` -> ⏩, `[CONFIRM]` -> 💬, `[D1]/[D2]/[D3]` -> 🟢/🟡/🔴.
  - [x] Tối ưu CSS badge với viền mờ, kích thước chữ 15px cho cờ và 13px cho biểu tượng trạng thái, tự động căn giữa dòng.
  - [x] Bổ sung nhận diện câu tiếng Anh bắt đầu bằng `[EN]` trong `extractEnglishElements` và hỗ trợ nút phát âm 🔊 cho dòng có nhãn cờ 🇬🇧 trong `processLineForAudio`.
  - [x] Nâng cấp Service Worker lên `engtutor-v7` trong [`sw.js`](file:///data/data/com.termux/files/home/storage/shared/LANGUAGE/english/app/web/sw.js).

- [x] **Bước 14: Tab cấu hình Emoji chuyên biệt & Hiển thị từ mục tiêu `🎯 capable` trong khung chat**
  - [x] Tái cấu trúc Cài đặt thành hệ thống 3 Tab rõ ràng, khoa học: `🎨 Emoji & Hồ sơ`, `🤖 Động cơ AI`, `🔊 Giọng đọc`.
  - [x] Thêm bộ chọn biểu tượng từ mục tiêu (Target Word Emoji: 🎯, 📖, 💡, 💎, 🚀, 🔍, 📌, ✨ hoặc tự nhập) trong tab Emoji.
  - [x] Lưu trường `avatar_target` vào `USERS/<username>/profile.json` qua API Golang `/api/user/profile`.
  - [x] Khi người học nhập từ cần học (ví dụ: `capable` hoặc `.capable`), bong bóng chat của người học hiển thị trực quan dạng `🎯 capable` (với badge emoji mục tiêu và từ in đậm) thay vì hiển thị dấu chấm `.capable` thô.
  - [x] Nâng cấp Service Worker lên `engtutor-v8` trong [`sw.js`](file:///data/data/com.termux/files/home/storage/shared/LANGUAGE/english/app/web/sw.js).

- [x] **Bước 15: Sửa triệt để lỗi vỡ HTML nhãn Emoji do bộ lọc âm thanh chèn nhầm vào thuộc tính thẻ**
  - [x] Phát hiện nguyên nhân: Biểu thức chính quy Pattern 3 trong `processLineForAudio` trước đó quét các chuỗi trong dấu ngoặc kép `"(...)"` để tìm câu tiếng Anh cần phát âm, vô tình khớp nhầm vào các thuộc tính HTML như `class="badge badge-vi"` hay `class="badge badge-next"`. Việc này chèn thẻ `<button>` vào giữa thẻ `<span class=...`, làm vỡ cú pháp thẻ HTML và khiến trình duyệt hiển thị rác `🔊 title="Tiếng Việt">🇻🇳` ra màn hình.
  - [x] Khắc phục:
    1. Bỏ qua hoàn toàn việc quét âm thanh trên các dòng nhãn trạng thái, định nghĩa tiếng Việt (`badge-vi`, `badge-next`, `badge-ok`, `badge-confirm`, `badge-error`, `badge-warn`, `badge-diff`).
    2. Siết chặt Pattern 3 chỉ nhận diện câu trích dẫn tiếng Anh có khoảng trắng/đầu dòng phía trước `(?:^|[\s(])["“]...`, tuyệt đối không bao giờ khớp vào thuộc tính HTML sau dấu `=` (`class="..."`, `title="..."`).
  - [x] Nâng cấp Service Worker lên `engtutor-v9` trong [`sw.js`](file:///data/data/com.termux/files/home/storage/shared/LANGUAGE/english/app/web/sw.js).

- [x] **Bước 16: Tối ưu thanh điều hướng Drawer và nút Đoạn chat mới chuẩn UX di động**
  - [x] Thay thế nút thùng rác xóa dữ liệu bằng nút cây bút ✏️ ("Đoạn chat mới"), khởi tạo phiên học với câu khẩu hiệu đầy cảm hứng và tự động focus ô nhập liệu.
  - [x] Thêm nút Hamburger `☰` góc trên bên trái mở Navigation Drawer trượt mượt mà.
  - [x] Chuyển các mục Cài đặt và Thẻ người học (User card với Avatar & Username) xuống đáy Drawer.
  - [x] Tích hợp các lối tắt thao tác nhanh (`.s`, `.g`, `.help`) bên trong Drawer.
  - [x] Khắc phục triệt để lỗi hiển thị vỡ layout do cache CSS cũ: di dời markup Drawer xuống đáy trang, bổ sung critical inline CSS bảo vệ trong `<head>`, thêm cache-buster `?v=11`, cập nhật Service Worker `engtutor-v11` và cấu hình HTTP `Cache-Control: no-cache` trên máy chủ Go.

---

## 3. Tiêu chuẩn Nghiệm thu

1. [x] Giao diện hiển thị trọn vẹn, không bị tràn ngang ở mọi độ phân giải màn hình từ 360px trở lên.
2. [x] Khi bật bàn phím ảo, khung chat co giãn chuẩn xác, không che khuất ô nhập liệu.
3. [x] Thanh điều hướng cử chỉ đáy màn hình không đè lên thanh nhập liệu.
4. [x] Thanh Header được tinh giản tối đa, loại bỏ nút Vault không cần thiết cho học viên.
5. [x] Chạm vào ô nhập liệu không bị phóng to màn hình trên iOS.
6. [x] Nhập một từ (ví dụ `urge`) tự động gửi `.urge` mà không cần người dùng gõ dấu chấm.
7. [x] Khi chỉnh sửa file CSS/JS/HTML, trình duyệt tự động cập nhật ngay lập tức nhờ Go Live-Reload.
8. [x] Nút `3 câu luyện`, `5 câu luyện` chỉ xuất hiện đúng lúc (sau khi giải nghĩa từ), và ẩn hoàn toàn khi đang làm bài test.
9. [x] Thao tác vuốt xuống khi đang ở đỉnh trang chat kích hoạt hiệu ứng loading, rung nhẹ và tự động làm mới ứng dụng (tiện dụng trên PWA).
10. [x] Không còn các nút lệnh `.` cố định ban đầu; ô gõ tin nhắn luôn hiển thị trọn vẹn, không bị đẩy trôi hoặc che khuất sau khi refresh trang.
11. [x] Giao diện người học tinh gọn, tập trung hoàn toàn vào hội thoại học tập, tra từ và làm bài tập.
12. [x] Nhãn ngôn ngữ và trạng thái được tự động hiển thị dưới dạng emoji sinh động (🇬🇧, 🇻🇳, ✅, ❌, ⏩...) trên Web UI mà vẫn bảo toàn định dạng văn bản thô an toàn cho CLI Termux.
13. [x] Cài đặt chia thành các tab chuyên biệt với tab cấu hình Emoji đầy đủ (User, AI, Target Word) và hiển thị từ vựng trong chat dưới dạng `🎯 <từ>` thay vì `.<từ>`.
14. [x] Triệt tiêu hoàn toàn hiện tượng vỡ mã thẻ HTML `🔊 title="Tiếng Việt">...`; tất cả các huy hiệu emoji và nút phát âm hiển thị nguyên vẹn, chuẩn xác.
15. [x] Nút cây bút ở góc phải khởi tạo đoạn chat mới mượt mà, thân thiện, không gây cảm giác phá hủy như nút thùng rác.
16. [x] Menu Hamburger bên trái trượt mượt mà, đầy đủ lối tắt, cài đặt và hồ sơ người học; miễn nhiễm hoàn toàn với lỗi vỡ layout do cache CSS cũ.
