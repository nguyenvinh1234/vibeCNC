# Mach3Turn / XHC – Implementation Plan

**Repository:** `nguyenvinh1234/vibeCNC`  
**Development branch:** `mach3turn`  
**Updated:** 2026-09-08  
**Target:** Fork vibeCNC thành ứng dụng kiểm tra, mô phỏng, chỉnh/sinh G-code cho máy tiện Mach3Turn + XHC MKX-ET, ưu tiên an toàn máy thật.

> **Quy tắc dự án:** Máy điều khiển yếu, vì vậy **KHÔNG dùng AI local / Ollama trên máy CNC**. AI chỉ dùng qua subscription/CLI chính thức hoặc API cloud. AI không được phép điều khiển Mach3/XHC trực tiếp và không được bỏ qua Safety Validator.

---

## 1. Trạng thái tổng quan

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| Fork `burnshall-ui/vibeCNC` | ✅ XONG | Repo hiện tại: `nguyenvinh1234/vibeCNC` |
| Tạo branch phát triển | ✅ XONG | `mach3turn` |
| Kiểm tra kiến trúc upstream | ✅ XONG | Python + PyQt6; parser/linter/plotter tách module |
| Xác nhận parser tiện X/Z | ✅ XONG | Parser Fanuc lathe, X mặc định là diameter |
| Xác nhận T0101/T0404 | ✅ XONG | Parser đọc tool number từ T-word |
| Xác nhận AI upstream | ✅ XONG | Upstream có Anthropic + Ollama |
| Quyết định không dùng local AI | ✅ XONG | Ollama không dùng trong profile sản xuất của dự án |
| Tài liệu kế hoạch Git | ✅ XONG | File này là tracker chính |
| AI Provider abstraction | ⬜ CHƯA XONG | Cần tách provider interface khỏi client hiện tại |
| Codex CLI / ChatGPT subscription | ⬜ CHƯA XONG | Ưu tiên số 1 cho AI subscription |
| OpenAI API provider | ⬜ CHƯA XONG | Fallback / môi trường không có Codex login |
| Anthropic API provider | ⬜ CHƯA XONG | Giữ tương thích cloud hiện có, chuẩn hóa lại interface |
| DeepSeek/OpenRouter provider | ⬜ CHƯA XONG | P2, làm sau khi core ổn định |
| Mach3Turn modal validator | ⬜ CHƯA XONG | G18/G21/G90/G91/G94/G95, Diameter/Radius |
| Tool-change safety validator | ⬜ CHƯA XONG | T0101–T0808 + safe-zone |
| Phát hiện block lỗi kiểu `G0 10.` | ⬜ CHƯA XONG | Phải là FATAL, không tự đoán X/Z |
| Test bằng `thu1.txt`/`TIEP.txt` | ⬜ CHƯA XONG | Đưa thành regression fixtures |
| Mô hình khuôn/phôi/con lăn | ⬜ CHƯA XONG | P2 |
| Collision geometry sweep | ⬜ CHƯA XONG | P2/P3 |
| Xuất `.tap/.nc` Mach3Turn | ⬜ CHƯA XONG | Chỉ sau khi validator PASS |
| Kết nối trực tiếp XHC/Mach3 | ⛔ KHÔNG LÀM Ở GIAI ĐOẠN NÀY | Không cho AI/simulator điều khiển máy trực tiếp |

---

## 2. Kiến trúc mục tiêu

```text
                    vibeCNC fork
                        │
       ┌────────────────┴────────────────┐
       │                                 │
   G-code Core                      AI Provider Manager
       │                                 │
       │                    ┌────────────┼─────────────┐
       │                    │            │             │
       │                Codex CLI    OpenAI API   Anthropic API
       │              (ChatGPT plan)  (API key)     (API key)
       │                    │            │             │
       │                    └────────────┴─────────────┘
       │                                 │
       ├── Mach3Turn Parser              │
       ├── Modal State Engine            │
       ├── Safety Validator <────────────┘
       ├── Tool-change Validator
       ├── X-Z Simulator
       ├── Collision Engine
       └── Export Gate
                │
                ▼
         SAFE / BLOCKED result
                │
        Operator xác nhận
                │
                ▼
          Export .tap/.nc
                │
                ▼
             Mach3Turn
```

### Nguyên tắc an toàn bắt buộc

1. AI chỉ **đề xuất/review** code.
2. Mọi code do AI tạo/sửa phải đi qua parser + deterministic validator.
3. AI không được tự sửa lỗi mơ hồ kiểu `G0 10.` thành `G0 X10.` hay `G0 Z10.`.
4. Có lỗi FATAL → khóa chức năng xuất file sản xuất.
5. Không gọi trực tiếp `NcEther.dll`, không điều khiển OUTPUT/INPUT từ AI.
6. API key không được lưu vào repo/config commit; chỉ dùng environment/credential store.

---

# 3. Kế hoạch triển khai theo giai đoạn

## V0.1 – Project baseline + Safety foundation (P0)

**Mục tiêu:** Có nền tảng Mach3Turn an toàn trước khi thêm AI mạnh.

- [x] Fork upstream.
- [x] Tạo branch `mach3turn`.
- [x] Audit parser/linter/config cơ bản.
- [x] Chốt không dùng local AI/Ollama trên máy CNC.
- [ ] Tạo `MachineProfile` cho `MACH3TURN_XHC_MKX_ET`.
- [ ] Tách `dialect = fanuc | mach3turn`.
- [ ] Thêm modal state:
  - [ ] G18 plane X-Z.
  - [ ] G20/G21 units.
  - [ ] G90/G91 absolute/incremental.
  - [ ] G94/G95 feed mode.
  - [ ] G40/G41/G42 compensation state.
  - [ ] Diameter/Radius X mode trong machine profile.
- [ ] Thêm severity cho linter: `INFO`, `WARNING`, `ERROR`, `FATAL`.
- [ ] FATAL khi block motion không có axis hợp lệ, ví dụ `G0 10.`.
- [ ] Không cho export khi có FATAL.
- [ ] Regression tests cho modal state.

**Definition of Done V0.1**
- `pytest` PASS.
- File G-code có modal rõ ràng được mô phỏng đúng.
- `G0 10.` bị FATAL và không được export.
- G90/G91 không bị hiểu giống nhau.
- G94/G95 được lưu đúng state và hiển thị rõ.

**Trạng thái:** ⬜ CHƯA XONG

---

## V0.2 – Mach3Turn Tool / Turret Safety (P0)

**Mục tiêu:** Hiểu đúng cách gọi dao và ngăn thay dao tại vị trí nguy hiểm.

- [ ] Parse đầy đủ `Txxxx`:
  - [ ] `T0101 → Tool 1 / Offset 1`.
  - [ ] `T0404 → Tool 4 / Offset 4`.
  - [ ] Chỉ cho phép T01…T08 trong profile turret 8 dao.
- [ ] Tạo `safe_tool_change_zone` theo X/Z cấu hình thực tế.
- [ ] Cảnh báo/FATAL nếu T-word xuất hiện ngoài safe zone.
- [ ] Rule yêu cầu spindle stop trước tool change theo policy máy.
- [ ] Không tự gọi M6/M101; simulator chỉ đánh dấu event.
- [ ] Hiển thị tool-change event trên X-Z plot.
- [ ] Thêm tool table 8 vị trí.

**Definition of Done V0.2**
- T0101–T0808 được nhận dạng đúng.
- T0909 bị chặn với profile 8 dao.
- Tool change ở vùng nguy hiểm bị BLOCKED.
- Không làm thay đổi macro M6Start/M101 đang chạy trên Mach3.

**Trạng thái:** ⬜ CHƯA XONG

---

## V0.3 – Cloud AI Provider Layer, không local (P0/P1)

**Mục tiêu:** Cho vibeCNC dùng AI mạnh mà không tải model lên máy CNC.

### 3.1 Provider interface

- [ ] Tạo `AIProvider` interface chung:
  - `review_gcode(...)`
  - `generate_gcode(...)`
  - `explain_finding(...)`
  - `health_check()`
  - timeout/cancel/error normalization
- [ ] Tách UI khỏi provider cụ thể.
- [ ] Dropdown chọn provider.
- [ ] Không hiển thị Ollama trong profile sản xuất `MACH3TURN_XHC_MKX_ET`.

### 3.2 Codex CLI / ChatGPT subscription – ưu tiên số 1

- [ ] Provider `CodexCLIProvider`.
- [ ] Dùng Codex CLI đã đăng nhập bằng tài khoản ChatGPT.
- [ ] Kiểm tra `codex` tồn tại + phiên đăng nhập trước khi bật provider.
- [ ] Chạy subprocess với timeout cứng.
- [ ] Yêu cầu output có cấu trúc JSON/schema.
- [ ] Không truyền secret/API key vào prompt.
- [ ] Không cấp quyền shell/máy CNC cho prompt review G-code.
- [ ] Khi hết quota/login lỗi → báo rõ và cho chuyển API provider.

**Ghi chú:** OpenAI chính thức hỗ trợ đăng nhập Codex bằng ChatGPT; usage được tính theo gói ChatGPT. Nếu dùng API key riêng thì tính theo API pricing. Đây là lý do provider subscription được ưu tiên.

### 3.3 OpenAI API

- [ ] `OpenAIAPIProvider`.
- [ ] Key đọc từ `OPENAI_API_KEY` hoặc credential store.
- [ ] Không ghi key vào `config.yaml`.
- [ ] Model configurable.
- [ ] Retry có giới hạn, timeout, error messages rõ ràng.

### 3.4 Anthropic API

- [ ] Refactor client Anthropic hiện có thành `AnthropicAPIProvider`.
- [ ] Key từ `ANTHROPIC_API_KEY`.
- [ ] Không lưu key trong repo.

### 3.5 Provider tùy chọn sau core

- [ ] OpenRouter – P2.
- [ ] DeepSeek API – P2.
- [ ] Gemini API – P2 nếu cần.

**Definition of Done V0.3**
- Có thể chọn Codex subscription hoặc API cloud từ UI.
- Không cần cài Ollama/model local.
- Provider timeout không làm treo GUI.
- AI output luôn đi qua Safety Validator trước khi xuất.

**Trạng thái:** ⬜ CHƯA XONG

---

## V0.4 – AI Guardrails cho G-code (P0)

**Mục tiêu:** AI hữu ích nhưng không được vượt qua luật máy.

- [ ] System prompt riêng `Mach3Turn CNC Reviewer`.
- [ ] Inject machine profile + tool table + policy vào review context.
- [ ] AI phải phân loại:
  - syntax issue
  - modal issue
  - unsafe tool change
  - feed/spindle concern
  - geometry ambiguity
- [ ] AI không được tự quyết định kích thước/khuôn/tool chưa biết.
- [ ] AI patch dạng unified diff hoặc structured changes.
- [ ] Người dùng xem diff trước khi Apply.
- [ ] Apply xong tự chạy lint/simulation lại.
- [ ] Nếu validator FATAL sau patch → rollback/không cho export.

**Definition of Done V0.4**
- AI có thể review `thu1.txt`/`TIEP.txt`.
- AI nhận ra `G0 10.` là mơ hồ và yêu cầu xác nhận, không tự đoán.
- Mọi patch đều có before/after validation.

**Trạng thái:** ⬜ CHƯA XONG

---

## V0.5 – Regression bằng G-code thực tế (P0)

**Mục tiêu:** Không phát triển bằng sample giả; dùng đúng code máy hiện có.

- [ ] Thêm `tests/fixtures/mach3turn/thu1.nc`.
- [ ] Thêm `tests/fixtures/mach3turn/tiep_invalid.nc`.
- [ ] Test T0101/T0404.
- [ ] Test S350 M4.
- [ ] Test F300/F350 theo G94/G95 profile.
- [ ] Test modal G0/G1 qua nhiều dòng.
- [ ] Test `G0 10.` phải FATAL.
- [ ] Test thiếu G18/G21/G90/G94/G95 theo policy.
- [ ] Snapshot toolpath X-Z để chống regression.

**Definition of Done V0.5**
- Hai chương trình thực tế có test tự động.
- Mọi thay đổi parser về sau không được làm test thực tế regress.

**Trạng thái:** ⬜ CHƯA XONG

---

## V0.6 – Spinning / lận: khuôn + phôi + con lăn (P1/P2)

**Mục tiêu:** Từ simulator tiện thông thường thành simulator phù hợp máy lận/miết.

- [ ] Model phôi.
- [ ] Import/khai báo profile khuôn.
- [ ] Tool geometry cho con lăn:
  - [ ] R2
  - [ ] R4
  - [ ] R6
  - [ ] đường kính con lăn
  - [ ] bề rộng
  - [ ] cán 20x20
- [ ] Hiển thị geometry thật trên X-Z.
- [ ] Collision sweep theo thân tool, không chỉ tool-tip point.
- [ ] Collision với chuck/khuôn/phôi.
- [ ] Clearance margin cấu hình được.
- [ ] Report line G-code gây va chạm.

**Definition of Done V0.6**
- Có thể nhìn trực quan khuôn + phôi + con lăn.
- Simulator báo line có nguy cơ va chạm geometry.
- Không tuyên bố simulation là chứng minh an toàn tuyệt đối.

**Trạng thái:** ⬜ CHƯA XONG

---

## V0.7 – Export Gate cho Mach3Turn (P1)

**Mục tiêu:** Xuất file sản xuất có kiểm soát.

- [ ] Export `.tap`/`.nc`.
- [ ] Trước export chạy lại toàn bộ deterministic validator.
- [ ] Hiển thị checklist:
  - [ ] Units
  - [ ] Plane
  - [ ] Distance mode
  - [ ] Feed mode
  - [ ] Diameter/Radius mode
  - [ ] Tool calls
  - [ ] Safe tool change
  - [ ] Collision warnings
  - [ ] Program end/retract
- [ ] Ghi hash/checksum file export vào report.
- [ ] Lưu validation report cạnh G-code.
- [ ] Yêu cầu operator approval nếu còn WARNING.
- [ ] Cấm export nếu còn FATAL.

**Trạng thái:** ⬜ CHƯA XONG

---

# 4. Những việc KHÔNG làm lúc này

- [x] **Không chạy AI local/Ollama trên máy CNC yếu.**
- [x] **Không để AI điều khiển XHC/Mach3 trực tiếp.**
- [x] **Không tự sửa macro M6Start/M101 trong giai đoạn parser/simulator.**
- [x] **Không tự đoán kích thước máy, khuôn, con lăn hoặc safe-zone.**
- [x] **Không tự đổi mapping I/O của máy.**
- [x] **Không merge thẳng vào `main` khi chưa có test.**

---

# 5. Thứ tự ưu tiên thực hiện

1. **P0-A:** Mach3Turn modal state + FATAL validator.
2. **P0-B:** Regression bằng `thu1` và `TIEP`.
3. **P0-C:** Tool/Turret safety.
4. **P0-D:** AI Provider interface.
5. **P0-E:** Codex CLI subscription bridge.
6. **P1:** OpenAI API + Anthropic API.
7. **P1:** AI patch review + diff + re-validation.
8. **P1/P2:** Khuôn/phôi/con lăn + collision sweep.
9. **P1:** Export gate `.tap/.nc`.
10. **P2:** OpenRouter/DeepSeek/Gemini nếu cần.

---

# 6. Cách cập nhật tracker

Sau mỗi commit/PR:

- Đổi `- [ ]` thành `- [x]` khi test/acceptance criteria đã đạt.
- Cập nhật bảng **Trạng thái tổng quan**.
- Ghi commit/PR liên quan dưới mục tương ứng.
- Không đánh dấu XONG chỉ vì đã viết code; phải có test hoặc kiểm chứng tương ứng.
- Nếu phát hiện regression trên G-code thực tế, đổi trạng thái trở lại CHƯA XONG và ghi lý do.

---

# 7. Tài liệu tham chiếu AI cloud

- OpenAI: Codex có thể đăng nhập bằng tài khoản ChatGPT; usage/limits theo gói ChatGPT. Dùng API key riêng thì theo API billing.
  - https://help.openai.com/en/articles/11369540-using-codex-with-chatgpt
  - https://help.openai.com/en/articles/20001275-chatgpt-work-and-codex

---

# 8. Mốc phát hành đề xuất

| Milestone | Nội dung | Trạng thái |
|---|---|---|
| `mach3turn-v0.1` | Parser/modal/linter Mach3Turn | ⬜ |
| `mach3turn-v0.2` | Turret/tool-change safety | ⬜ |
| `mach3turn-v0.3` | Cloud AI/Codex subscription | ⬜ |
| `mach3turn-v0.4` | AI guardrails + real G-code tests | ⬜ |
| `mach3turn-v0.5` | Spinning geometry/collision | ⬜ |
| `mach3turn-v1.0` | Export-gated production assistant | ⬜ |

---

## CURRENT NEXT ACTION

**Bắt đầu P0-A:** thêm Mach3Turn machine profile + modal state + severity/FATAL validator, sau đó đưa `thu1.txt` và `TIEP.txt` vào regression test.
