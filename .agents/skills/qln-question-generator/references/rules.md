# Quy định chi tiết khi sinh câu hỏi (QLN Question Rules)

Tài liệu này quy định chi tiết các tiêu chuẩn kỹ thuật và sư phạm khi AI sinh câu hỏi trong hệ thống **qln**.

---

## 1. Tiêu chuẩn tạo chỗ trống (`___`) cho dạng điền từ (`fb`)

### 1.1. Nguyên tắc 2 chỗ trống (Dual Blanks)
* Khi từ mục tiêu đi liền với một collocation/partner word quan trọng, phải đặt **2 chỗ trống**:
  * Chỗ trống 1: Động từ/Tính từ dẫn dắt hoặc từ chính.
  * Chỗ trống 2: Danh từ kết hợp hoặc giới từ đi kèm.
* **Ví dụ tốt:**
  * `We need to ___ effective ___ to prevent data leaks.` (`take; measures`)
  * `She ___ the ___ to buy unnecessary gadgets.` (`controlled; urge` hoặc `resisted; urge`)
* **Trường hợp dùng 1 chỗ trống:**
  * Chỉ dùng 1 chỗ trống khi câu ngắn ở cấp độ `[D1]`, hoặc khi từ mục tiêu đứng độc lập với vai trò ngữ pháp không có collocation cố định trực tiếp.
  * *Ví dụ:* `Can you ___ the length of this table?` (`measure`)

### 1.2. Định dạng ký hiệu chỗ trống
* Sử dụng chính xác 3 dấu gạch dưới `___` cho mỗi chỗ trống.
* Giữa 2 chỗ trống liên tiếp phải có khoảng trắng: `___ ___`.
* Giữ nguyên dấu câu gốc (dấu phẩy, chấm, hỏi) ở cuối câu hoặc giữa các mệnh đề.

---

## 2. Tiêu chuẩn bản dịch tiếng Việt (`[VI]`)

* **Không dịch thô word-by-word:** Dịch theo văn phong tiếng Việt tự nhiên, truyền tải đúng sắc thái và tình huống.
* **Không làm lộ từ tiếng Anh:**
  * *Tránh:* "Chúng ta phải *thực hiện* các *biện pháp*..." nếu câu tiếng Anh là `We must ___ ___...` (dễ đoán `take measures`).
  * *Nên:* "Chúng ta cần có giải pháp hành động để ngăn chặn sự cố rò rỉ dữ liệu." (Người học phải nhớ collocation `take measures` thay vì chỉ dịch thô từ sang từ).
* Đảm bảo bản dịch đủ dữ kiện để phân biệt nếu từ có nhiều nghĩa khác nhau.

---

## 3. Quy chuẩn đáp án và phương án thay thế (Alternatives)

### 3.1. Đáp án gốc (Original Target Answer)
* Thứ tự các từ trong `correct_answer` phải khớp chính xác với thứ tự các chỗ trống `___`.
* Các từ điền cách nhau bằng dấu chấm phẩy và khoảng trắng: `; `.
* Luôn chia đúng thì/dạng ngữ pháp (ví dụ: quá khứ `took; measures`, số nhiều `strong; preferences`).

### 3.2. Quản lý phương án thay thế hợp lệ (Valid Alternatives)
* Khi người học đưa ra đáp án khác nhưng đúng ngữ pháp và tự nhiên (ví dụ câu hỏi mong đợi `take; measures` nhưng người học trả lời `adopt; measures` hoặc `implement; measures`):
  * **Không báo sai `[X]`.**
  * Ghi nhận bằng trạng thái `[~]` (Gần đúng / Cách này dùng được).
  * Giải thích ngắn gọn sắc thái của từ thay thế.
  * Yêu cầu nhập lại đáp án gốc để củng cố mục tiêu học ban đầu:
    ```text
    [~] Cách này dùng được; hãy luyện lại đáp án gốc.
    Giải thích: "implement measures" cũng rất tự nhiên, nhưng từ trọng tâm của bài là "take".
    [RETRY] Mời bạn nhập lại đáp án gốc: take; measures
    ```

---

## 4. Kiểm tra trước khi xuất câu hỏi (Checklist)

Mỗi khi sinh câu hỏi mới, AI phải tự động rà soát 5 tiêu chí sau:
1. [ ] Câu tiếng Anh có tự nhiên, không gượng gạo, không lỗi ngữ pháp không?
2. [ ] Các chỗ trống `___` có kiểm tra đúng từ mục tiêu và collocation không?
3. [ ] Bản dịch tiếng Việt `[VI]` có tự nhiên và không để lộ đáp án không?
4. [ ] Nhãn độ khó `[D1]`, `[D2]`, hay `[D3]` đã phản ánh đúng độ phức tạp của câu chưa?
5. [ ] Đã chuẩn bị sẵn câu hoàn chỉnh để ghi vào clipboard thiết bị chưa?
