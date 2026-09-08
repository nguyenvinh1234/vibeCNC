# AI Provider Policy — Mach3Turn vibeCNC

**Updated:** 2026-09-08

## Quyết định chính

Local AI/Ollama **không bị cấm** trong dự án.

Máy CNC hiện tại có cấu hình yếu nên cấu hình mặc định là:

```yaml
ai:
  offline: true
  allow_local: false
  mode: anthropic
```

Điều này chỉ là mặc định triển khai cho phần cứng hiện tại.

Nếu sau này dùng máy có CPU/GPU/RAM đủ mạnh, có thể bật local AI bằng:

```yaml
ai:
  offline: false
  allow_local: true
  mode: ollama
```

## Các nhóm provider mục tiêu

1. **Subscription / CLI** — Codex CLI với tài khoản ChatGPT Plus/Pro; Claude Code nếu được tích hợp sau.
2. **Cloud API** — OpenAI API, Anthropic API, sau đó OpenRouter/DeepSeek/Gemini nếu cần.
3. **Local** — Ollama hoặc backend local khác khi phần cứng đủ mạnh.

Không có provider nào được phép bỏ qua Mach3Turn Safety Validator.

## Nguyên tắc bắt buộc

- Không tự fallback sang Ollama khi provider cloud cấu hình sai.
- `offline: true` phải tắt mọi AI call.
- Local AI chỉ chạy khi người dùng chủ động đặt `allow_local: true`.
- Machine profile `MACH3TURN_XHC_MKX_ET` không được hard-code lệnh cấm local AI.
- AI chỉ review/generate/giải thích G-code; không điều khiển `NcEther.dll`, Mach3 output/input hay turret trực tiếp.
- Mọi G-code do AI tạo hoặc sửa phải đi qua deterministic parser + SafetyEngine + simulation trước production export.

## Ghi chú thay thế quyết định cũ

Mọi nội dung trước đây trong tracker/PR ghi "cấm Ollama", "hard no-local" hoặc "cloud only" được hiểu là **mặc định cho máy CNC yếu hiện tại**, không phải giới hạn vĩnh viễn của sản phẩm.

Tài liệu này là chính sách AI hiện hành cho nhánh `mach3turn`.
