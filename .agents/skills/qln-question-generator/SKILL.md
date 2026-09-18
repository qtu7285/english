---
name: qln-question-generator
description: >-
  Generate high-quality English test questions and practice rounds adhering to qln pedagogical rules.
  Use when generating new questions, fill-in-the-blank (fb) exercises with dual blanks, multiple-choice (mc),
  selecting collocations, assigning difficulty levels [D1]-[D3], and formatting test output for the learner.
---

# QLN Question Generator

Skill chuyên dụng cho việc sinh câu hỏi luyện tập tiếng Anh chuẩn hóa theo quy chuẩn sư phạm của hệ thống **qln**.

## 1. Mục tiêu và Nguyên tắc cốt lõi

1. **Kiểm tra theo ngữ cảnh thực tế (Contextual Learning):** Không kiểm tra từ vựng đơn lẻ, cô lập. Mọi câu hỏi phải nằm trong một ngữ cảnh giao tiếp, công việc hoặc đời sống tự nhiên.
2. **Ưu tiên Collocation & Cụm từ:** Tập trung vào sự kết hợp từ tự nhiên (ví dụ: `take measures`, `reach a consensus`, `raise objections`).
3. **Quy tắc 2 chỗ trống (`fb` - Dual Blanks):** Với câu hỏi điền từ (`fb`), ưu tiên tạo ít nhất **2 chỗ trống có ý nghĩa** khi tự nhiên:
   - 1 chỗ trống cho từ mục tiêu (target headword/form).
   - 1 chỗ trống cho từ kết hợp quan trọng (collocation partner: verb, adjective, preposition, noun).
   - *Ví dụ:* `She ___ the ___ to reply immediately.` -> `resisted; urge`
4. **Không lộ đáp án qua ngữ cảnh tiếng Việt:** Bản dịch tiếng Việt `[VI]` phải tự nhiên, sát nghĩa nhưng **không được dịch thô/máy móc để lộ trực tiếp đáp án tiếng Anh**.
5. **Đa dạng hóa biến thể (Inflection & Variety):** Kiểm tra linh hoạt các dạng chia thì/thể của từ (`base`, `past`, `past_participle`, `-ing`, `plural`), tránh lặp lại nguyên văn các câu ví dụ cũ.

---

## 2. Phân loại độ khó ([D1], [D2], [D3])

Mỗi câu hỏi phải được gắn nhãn độ khó rõ ràng:
- **`[D1]` (Cơ bản):** Ngữ cảnh ngắn gọn, quen thuộc; cấu trúc câu đơn giản (SVO); cụm từ đi liền kề (ví dụ: `take ___`); từ đối tác phổ biến.
- **`[D2]` (Trung bình):** Ngữ cảnh công việc/xã hội thực tế; có mệnh đề phụ hoặc chia thì phức tạp (hoàn thành, bị động); có từ chèn giữa cụm collocation (ví dụ: `take [stricter] measures`).
- **`[D3]` (Khó):** Ngữ cảnh học thuật, đàm phán, quản lý hoặc chuyên sâu; ngữ pháp nâng cao; cụm collocation mang tính thành ngữ hoặc sắc thái tinh tế; bẫy ngữ pháp/từ loại dễ nhầm lẫn.

---

## 3. Quy trình sinh câu hỏi từng bước

### Bước 1: Xác định mục tiêu và dạng từ (Target & Form)
- Xác định từ khóa (Headword) và dạng từ cần rèn luyện (`base`, `past`, `gerund`, v.v.).
- Chọn cụm từ/collocation mục tiêu từ danh sách `PHRASES` hoặc kiến thức ngôn ngữ học chuẩn mực.

### Bước 2: Soạn câu tiếng Anh hoàn chỉnh (Master Sentence)
- Viết một câu tiếng Anh tự nhiên, chuẩn bản ngữ, văn phong tự nhiên.
- Đảm bảo câu có ngữ cảnh rõ ràng, đủ dữ kiện để người học suy luận được từ cần điền.

### Bước 3: Đặt chỗ trống và xác định đáp án
- Đặt `___` tại vị trí từ mục tiêu và từ kết hợp (partner word).
- Lưu đáp án gốc theo thứ tự xuất hiện, ngăn cách bởi `; ` (ví dụ: `take; measures` hoặc `resisted; urge`).
- Chuẩn bị sẵn các phương án thay thế hợp lệ (valid alternatives, ví dụ: `took; steps`) để sẵn sàng chấm điểm theo quy tắc `[~]`.

### Bước 4: Soạn ngữ cảnh tiếng Việt (`[VI]`)
- Dịch câu tiếng Anh sang tiếng Việt tự nhiên, gãy gọn.
- Kiểm tra lại: Câu tiếng Việt có bị lộ đáp án theo kiểu "nhìn là đoán được từ tiếng Anh" không? Nếu có, hãy diễn đạt lại cho thuần Việt hơn.

### Bước 5: Trình bày câu hỏi chuẩn CLI
Hiển thị câu hỏi theo đúng mẫu (không dùng emoji, dùng nhãn ASCII):

```text
Câu <số>/<tổng> [D1]

[EN] <Câu tiếng Anh với các dấu ___>
[VI] <Câu dịch tiếng Việt tự nhiên>
```

---

## 4. Tích hợp Clipboard và Audio (Termux)

Theo quy định của hệ thống:
1. **Trước khi người học trả lời:** Hệ thống tự động copy **câu tiếng Anh hoàn chỉnh (đã điền đủ từ đúng)** vào bộ nhớ tạm (clipboard) để người học có thể tra Tap to Translate nếu cần:
   ```bash
   printf '%s' '<Complete correct sentence>' | termux-clipboard-set
   ```
2. **Sau khi người học trả lời đúng hoàn toàn `[OK]`:** Hệ thống tự động phát âm câu đúng:
   ```bash
   printf '%s' '<Complete correct sentence>' | termux-tts-speak -l en -n US -r 0.9 -s MUSIC
   ```

---

## 5. Tài liệu tham khảo chi tiết

- [Quy định chi tiết và tiêu chí sinh câu hỏi](./references/rules.md)
- [Các ví dụ mẫu cho từng từ loại và độ khó](./examples/tests.md)
