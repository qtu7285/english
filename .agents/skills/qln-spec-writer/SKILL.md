---
name: qln-spec-writer
description: >-
  Standardize the authoring and maintenance of technical specifications, workflows, and pedagogical documents in qln.
  Use when writing, drafting, refining, or evaluating system specifications, and always finish by asking the learner to confirm git commit and push.
---

# QLN Spec Writer

Skill chuyên dụng định chuẩn phong cách viết đặc tả kỹ thuật, quy trình (workflows) và tài liệu sư phạm cho hệ thống **qln**.

---

## 1. Phong cách & Tiêu chuẩn viết Spec (Style Guide)

1. **Rõ ràng, trực diện (Concise & Direct):**
   - Viết ngắn gọn, súc tích, đi thẳng vào vấn đề; tránh các câu từ hoa mỹ, dẫn dắt rườm rà.
   - Sử dụng tiếng Việt chuẩn mực, mạch lạc cho phần giải thích; thuật ngữ kỹ thuật giữ nguyên dạng chuẩn tiếng Anh khi cần thiết.
2. **Tuân thủ quy chuẩn hiển thị CLI (CLI-Safe):**
   - **Tuyệt đối không dùng emoji.**
   - Sử dụng các nhãn trạng thái ASCII trong ngoặc vuông: `[OK]`, `[~]`, `[X]`, `[CONFIRM]`, `[SAVE]`, `[EN]`, `[VI]`, `[D1]`, `[D2]`, `[D3]`.
3. **Liên kết tệp tuyệt đối (Clickable File Links):**
   - Mọi tệp và thư mục được đề cập phải có link markdown dạng `[tên_file](file:///đường_dẫn_tuyệt_đối)`.
4. **Bất biến và Nhất quán (Invariants & Consistency):**
   - Mọi quy định mới phải nhất quán với các tài liệu cốt lõi hiện có: `AGENTS.md`, `WORDS/README.md`, `WORDS/TEST-WORKFLOW.md`.

---

## 2. Cấu trúc chuẩn của một bản Spec

Khi tạo một tài liệu đặc tả mới, bám sát cấu trúc trong [Mẫu Spec chuẩn](./resources/spec-template.md):

1. **Tiêu đề & Định danh (Title & Metadata):** Tên spec, mục đích, người sở hữu, ngày tạo/cập nhật.
2. **Bối cảnh & Mục tiêu (Context & Objectives):** Vấn đề cần giải quyết và kết quả mong đợi.
3. **Phạm vi & Ranh giới (Scope & Boundaries):** Những gì thuộc phạm vi giải quyết và những gì nằm ngoài phạm vi.
4. **Đặc tả kỹ thuật (Technical Specification):** Cấu trúc dữ liệu, thuật toán, định dạng file, quy trình thao tác.
5. **Ràng buộc & Bất biến (Constraints & Invariants):** Các quy tắc không được phép vi phạm.
6. **Tiêu chuẩn kiểm thử & Nghiệm thu (Verification & Acceptance Checklist):** Các tiêu chí cụ thể để xác nhận spec đã được đáp ứng.

---

## 3. Quy trình thực hiện (Workflow Steps)

1. **Nghiên cứu & Khảo sát:** Đọc các tài liệu canonical liên quan để nắm chắc hiện trạng.
2. **Soạn thảo Spec:** Viết nội dung theo cấu trúc chuẩn và tuân thủ [Style Guide chi tiết](./references/style-guide.md).
3. **Tự rà soát (Self-Verification):**
   - [ ] Đã dùng nhãn ASCII, không có emoji nào chưa?
   - [ ] Đã gắn link tệp tuyệt đối chưa?
   - [ ] Đã đồng bộ với các workflow hiện hành chưa?
4. **Báo cáo & Nhắc nhở Git (BẮT BUỘC):**
   - Tóm tắt ngắn gọn các nội dung vừa tạo hoặc cập nhật.
   - **Luôn kết thúc bằng câu hỏi xác nhận Git:**
     ```text
     [CONFIRM] Bạn có muốn commit và push các thay đổi này lên Git bằng lệnh .g không?
     ```

---

## 4. Tài liệu tham khảo

- [spec-template.md](./resources/spec-template.md): Bản mẫu khung tài liệu đặc tả sẵn sàng sử dụng.
- [style-guide.md](./references/style-guide.md): Cẩm nang chi tiết về văn phong, định dạng và quy ước kỹ thuật.
