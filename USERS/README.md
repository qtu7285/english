# USERS — Hồ sơ & Cá nhân hóa Người học

Thư mục `USERS` lưu trữ thông tin hồ sơ, cấu hình giao diện (avatar, trợ lý AI, giọng đọc) và tài sản cá nhân cho từng người học trong hệ thống English Tutor.

---

## 1. Cấu trúc Thư mục

```text
USERS/
├── README.md               # Tài liệu đặc tả chuẩn của USERS
└── <username>/             # Thư mục riêng của từng người học (ví dụ: qtu, minh...)
    ├── profile.json        # Cấu hình cá nhân hóa (avatar, model, tốc độ phát âm)
    └── avatar.png          # (Tùy chọn) File ảnh đại diện riêng tải lên
```

---

## 2. Quy tắc Định danh (Username)

- Thư mục gốc luôn viết hoa toàn bộ: `USERS/` (đồng nhất với `WORDS/`, `PLANS/`, `STRATEGIES/`).
- Tên thư mục người học bên trong luôn viết thường theo chuẩn canonical username: `^[a-z0-9][a-z0-9_-]*$`.
- Người học mặc định của hệ thống là `qtu` (`USERS/qtu/`).

---

## 3. Cấu trúc `profile.json`

File `profile.json` trong mỗi thư mục người học có định dạng JSON chuẩn:

```json
{
  "username": "qtu",
  "display_name": "qtu",
  "avatar_user": "🧑‍🎓",
  "avatar_ai": "🤖",
  "avatar_target": "🎯",
  "ai_engine": "antigravity",
  "gemini_model": "gemini-3.6-flash",
  "tts_rate": 0.9,
  "updated_at": "2026-09-19T06:03:00Z"
}
```

### Các trường dữ liệu:
- `username`: Tên định danh chuẩn của người học (chữ thường, không dấu cách).
- `display_name`: Tên hiển thị thân thiện trên giao diện.
- `avatar_user`: Biểu tượng avatar đại diện người học (emoji hoặc ký hiệu).
- `avatar_ai`: Biểu tượng avatar đại diện cho gia sư AI.
- `avatar_target`: Biểu tượng đại diện trước từ vựng mục tiêu (mặc định: `🎯`).
- `ai_engine`: Động cơ AI mặc định (`antigravity` hoặc `gemini`).
- `gemini_model`: Tên mô hình khi sử dụng Gemini REST API.
- `tts_rate`: Tốc độ phát âm Text-to-Speech (mặc định: `0.9`).
- `updated_at`: Thời điểm cập nhật hồ sơ gần nhất (chuẩn ISO 8601 UTC).

---

## 4. Mối quan hệ với `WORDS/`

- **Tách biệt ranh giới dữ liệu**: `USERS/` quản lý hồ sơ và trải nghiệm hiển thị cá nhân. Kho từ vựng, lịch sử làm bài và thống kê học tập vẫn được lưu trữ chuẩn tắc tại `WORDS/<prefix>/<headword>/<headword>-<username>.csv` theo đúng quy định của `WORDS/AGENTS.md`.
- Khi người dùng đổi `#username` trên giao diện, hệ thống tự động tải đúng `USERS/<username>/profile.json` để áp dụng avatar và cài đặt tương ứng của người dùng đó.
