# Cẩm nang phong cách viết tài liệu QLN (QLN Style Guide)

Tài liệu này quy định chi tiết về phong cách diễn đạt, định dạng văn bản và quy ước kỹ thuật khi viết spec trong hệ thống **qln**.

---

## 1. Phong cách ngôn ngữ

* **Ngôn ngữ:** Sử dụng tiếng Việt chuẩn mực, rõ ràng, gãy gọn cho phần diễn giải; giữ nguyên thuật ngữ kỹ thuật tiếng Anh khi chúng phổ biến hoặc liên quan đến API/CLI (ví dụ: `headword`, `collocation`, `subagent`, `diff`, `commit`).
* **Văn phong:**
  * Khách quan, trung thực, chính xác; không dùng đại từ cảm thán hoặc từ ngữ văn hoa.
  * Các câu chỉ dẫn (instructions) phải ở thể mệnh lệnh hoặc điều kiện rõ ràng (Ví dụ: "Phải đọc X trước khi ghi Y", "Nếu Z thì...").
* **Không dùng Emoji:** Môi trường hiển thị là terminal CLI (Termux), do đó tuyệt đối không dùng emoji vì có thể gây lỗi hiển thị ký tự (font missing/misalignment). Dùng các nhãn ASCII như `[OK]`, `[~]`, `[X]`, `[CONFIRM]`, `[SAVE]`, `[D1]`, `[D2]`, `[D3]`.

---

## 2. Định dạng Markdown & Liên kết

* **Định dạng bảng và danh sách:**
  * Dùng bảng Markdown nhỏ gọn, căn lề rõ ràng.
  * Danh sách phân cấp rõ ràng bằng thụt lề 2 hoặc 4 dấu cách.
* **Liên kết tệp tuyệt đối:**
  * Luôn sử dụng cú pháp: `[tên_hiển_thị](file:///đường_dẫn_tuyệt_đối)`.
  * Tên hiển thị nên là đường dẫn tương đối hoặc tên ngắn gọn của file, ví dụ: `[WORDS/README.md](file:///storage/emulated/0/LANGUAGE/english/WORDS/README.md)`.

---

## 3. Quy ước cấu trúc tài liệu

* **Định danh nhất quán:** Mọi file hoặc định danh tính năng nên có tiền tố `qln-` (ví dụ: `qln-question-generator`, `qln-spec-writer`).
* **Phân định rõ ranh giới (Boundaries):**
  * Luôn chỉ rõ khi nào tài liệu này được nạp vào context, tránh tải bừa bãi làm tràn bộ nhớ ngữ cảnh (context window).
  * Ví dụ: "Tài liệu này chỉ được nạp khi cần soạn thảo hoặc đánh giá đặc tả kỹ thuật."

---

## 4. Quy định xác nhận Git cuối mỗi tác vụ

Mỗi khi AI thực hiện xong các chỉnh sửa code, file spec, hoặc cấu hình hệ thống, AI **bắt buộc** phải thực hiện 2 bước:
1. Tóm tắt ngắn gọn các file đã tạo hoặc cập nhật.
2. Đặt câu hỏi xác nhận Git chuẩn:
   ```text
   [CONFIRM] Bạn có muốn commit và push các thay đổi này lên Git bằng lệnh .git không?
   ```
*(Lưu ý: Không tự ý commit khi người học chưa đồng ý hoặc chưa gõ `.git`).*
