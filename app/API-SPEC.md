# English Tutor API Specification & Data Contract

Tài liệu đặc tả hợp đồng dữ liệu (Data Contract) giữa Backend (Go / AI) và Frontend (Web / CLI).

---

## 1. Nguyên tắc cốt lõi: Tách biệt Dữ liệu và Hiển thị (Separation of Concerns)

1. **Backend & AI lo Dữ liệu có cấu trúc (Structured Data):**
   * Backend xác định loại phản hồi (`type`) và các trường dữ liệu ngữ nghĩa (`target_word`, `audio_sentence`).
   * Không phụ thuộc vào các thẻ HTML giao diện cứng nhắc trong câu trả lời thô.
2. **Frontend lo Hiển thị & Tương tác (Smart Presentation):**
   * Frontend dựa vào trường `type` để chuyển đổi trạng thái giao diện chính xác 100% (placeholder ô nhập liệu, cụm nút chọn số câu, nút trắc nghiệm).
   * Tự động nhận diện và bố trí các thành phần (tự động chèn đường kẻ `<hr>` trước phần ví dụ, tạo nút phát âm và sao chép).
3. **Bảo toàn khả năng tương thích CLI (CLI-Safe):**
   * Trường `text` luôn chứa nội dung Markdown tự nhiên, sạch sẽ, chuẩn ASCII bracketed labels, giúp người học trên Termux CLI đọc mượt mà không bị vỡ định dạng.

---

## 2. Đặc tả API Endpoint `/api/chat`

* **Phương thức:** `POST`
* **Đường dẫn:** `/api/chat`
* **Content-Type:** `application/json`

### Yêu cầu (Request Payload)

```json
{
  "engine": "antigravity",
  "message": ".capable",
  "history": [
    { "role": "user", "text": ".capable" },
    { "role": "assistant", "text": "..." }
  ],
  "apiKey": "",
  "model": "gemini-3.6-flash",
  "enableVaultTools": true
}
```

### Phản hồi (Response Payload)

```json
{
  "type": "word_explanation",
  "target_word": "capable",
  "audio_sentence": "She is capable of handling the project on her own.",
  "text": "**capable** /'keɪpəbl/\n- [VI] Nghĩa: Có năng lực...\n\nVí dụ:\n- She is capable...",
  "tool_logs": [],
  "engine": "antigravity"
}
```

---

## 3. Danh mục các loại phản hồi (`type`)

| `type` | Ý nghĩa | Hành vi Frontend |
| :--- | :--- | :--- |
| **`word_explanation`** | Giải nghĩa từ/cụm từ mới | • Placeholder: `"Nhập số câu cần luyện hoặc yêu cầu khác..."`<br>• Nút nhanh: *"Luyện 3 câu"*, *"Luyện 5 câu"*, *"Luyện 10 câu"*<br>• Tự động chèn `<hr class="bubble-divider">` trước phần ví dụ<br>• Gắn nút phát âm từ mục tiêu & câu ví dụ |
| **`test_question`** | Câu hỏi bài tập (trắc nghiệm / điền từ) | • Placeholder: `"Nhập đáp án (A, B, C, D hoặc từ điền)..."`<br>• Ẩn các nút chọn số câu để tránh bấm nhầm<br>• Tạo nút bấm trắc nghiệm A, B, C, D |
| **`test_evaluation`** | Chấm điểm câu trả lời (`[OK]`, `[X]`, `[~]`) | • Hiển thị huy hiệu kết quả<br>• Tự động phát âm và sao chép câu đúng vào clipboard |
| **`round_completed`** | Hoàn thành vòng luyện tập (`Hoàn thành N/N câu`) | • Placeholder: `"Nhập số câu luyện tiếp hoặc từ mới..."`<br>• Nút nhanh: *"Luyện tiếp 3 câu"*, *"Luyện tiếp 5 câu"* |
| **`chat`** | Thảo luận, hỏi đáp ngữ pháp thông thường | • Placeholder mặc định: `"Nhập từ cần học..."`<br>• Ẩn thanh nút nhanh |

---

## 4. Hợp đồng khối ngữ nghĩa trong `text` (Semantic Markdown Contract)

Khi giải thích từ vựng, nội dung trong `text` tuân thủ 5 khối ngữ nghĩa chuẩn:
1. **Khối Headword:** `**<từ>** /<ipa>/`
2. **Khối Định nghĩa & Từ loại:**
   * `- [VI] Nghĩa: ...`
   * `- [EN] Từ loại: ...`
3. **Khối Cấu trúc & Cụm từ:** `Cấu trúc & Cụm từ thông dụng:`
4. **Khối Phân cách & Ví dụ:** `---` và `Ví dụ:`
5. **Khối Điều hướng:** `[NEXT] Nhập số câu để luyện (ví dụ 5), hoặc nhập từ mới để chuyển từ.`
