# Mach3Turn / XHC — Implementation Status

**Repository:** `nguyenvinh1234/vibeCNC`  
**Branch:** `mach3turn`  
**Tracker PR:** `#1`  
**Updated:** 2026-09-08

> Đây là bảng trạng thái vận hành ngắn gọn. Kế hoạch dài hạn vẫn nằm ở `docs/MACH3TURN_IMPLEMENTATION_PLAN.md`.

## Quy ước trạng thái

- ✅ **XONG** — đã triển khai và đã có bằng chứng kiểm chứng/CI PASS.
- 🟡 **ĐÃ CODE, CHỜ KIỂM CHỨNG** — code và test đã có nhưng chưa được phép đánh dấu XONG.
- ⬜ **CHƯA XONG** — chưa triển khai hoặc chưa đủ acceptance criteria.
- ⛔ **KHÔNG LÀM GIAI ĐOẠN NÀY** — chủ động loại khỏi scope hiện tại.

## A. Nền tảng dự án

| Hạng mục | Trạng thái | Bằng chứng / ghi chú |
|---|---|---|
| Fork upstream | ✅ XONG | `nguyenvinh1234/vibeCNC` |
| Branch phát triển | ✅ XONG | `mach3turn`; không sửa trực tiếp `main` |
| Draft PR quản lý | ✅ XONG | PR #1 `mach3turn -> main` |
| Không dùng local AI trên máy CNC yếu | ✅ XONG | Kiến trúc dự án đã chốt cloud/subscription only |
| Machine profile Mach3Turn/XHC | 🟡 ĐÃ CODE, CHỜ KIỂM CHỨNG | `vibe_cnc/machine_profile.py` |
| Config chọn profile | 🟡 ĐÃ CODE, CHỜ KIỂM CHỨNG | `config.example.yaml`: `MACH3TURN_XHC_MKX_ET`, `x_mode: diameter` |

## B. P0 — Mach3Turn Safety Foundation

| Hạng mục | Trạng thái | Bằng chứng / ghi chú |
|---|---|---|
| Modal state G18 | 🟡 | Validator + parser wrapper đã theo dõi plane |
| Modal state G20/G21 | 🟡 | Profile yêu cầu G21; sai unit tạo blocking finding |
| Modal state G90/G91 | 🟡 | `Mach3TurnGCodeParser` normalize G91 X/Z thành absolute cho geometry backend |
| Modal state G94/G95 | 🟡 | State được lưu; validator buộc khai báo rõ trước motion |
| G40/G41/G42 state | 🟡 | Parser wrapper lưu compensation state; upstream vẫn xử lý TNR geometry |
| X Diameter mode | 🟡 | Khóa trong machine profile; chưa nối UI/profile display |
| Severity INFO/WARNING/ERROR/FATAL | 🟡 | `mach3turn_validator.py` + `safety_engine.py`; linter UI path cũng đã nhận severity |
| `G0 10.` = FATAL | 🟡 | Rule `M3T-SYNTAX-001`; tuyệt đối không tự đoán X hay Z |
| Export gate deterministic | 🟡 | `SafetyEngine.blocks_export()` chặn ERROR/FATAL; chưa nối nút export UI |
| Parser compact words | 🟡 | Hỗ trợ dạng `G21G18G90G94`, `G1Z-8.5F300` |
| U/W + G91 state | 🟡 | Wrapper cập nhật U/W trước các X/Z incremental tiếp theo |
| UI nhận Mach3Turn validator qua LintEngine | 🟡 | `LintEngine` tự kích hoạt validator khi profile là `MACH3TURN_XHC_MKX_ET` |
| UI dùng Mach3Turn parser | ⬜ CHƯA XONG | Plotter hiện vẫn dùng parser upstream trực tiếp |
| UI hiển thị severity riêng biệt | ⬜ CHƯA XONG | Data đã có severity; presentation chưa phân INFO/WARNING/ERROR/FATAL |
| Nút/export production bị khóa khi blocking | ⬜ CHƯA XONG | Core gate đã có, UI integration chưa làm |

## C. Regression bằng chương trình máy thật

| Hạng mục | Trạng thái | Bằng chứng / ghi chú |
|---|---|---|
| Fixture `thu1` | 🟡 | `tests/fixtures/mach3turn/thu1.nc`; giữ nguyên `G0 T0101`, S350 M4, F300 |
| Fixture `TIEP` | 🟡 | `tests/fixtures/mach3turn/tiep_invalid.nc`; giữ nguyên dòng `G0 10.` |
| T0101 đọc thành Tool 1 | 🟡 | Test trong `tests/test_mach3turn_real_programs.py` |
| T0404 đọc thành Tool 4 | 🟡 | Test trong `tests/test_mach3turn_real_programs.py` |
| `TIEP: G0 10.` phải FATAL | 🟡 | Regression test yêu cầu đúng line 11 và severity FATAL |
| `thu1` thiếu modal header phải bị BLOCKED | 🟡 | Regression test không cho coi file hiện tại là production-safe |
| G90/G91 phải cho endpoint khác nhau | 🟡 | `tests/test_mach3turn_parser.py` |

## D. CI / kiểm chứng

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| Test Mach3Turn validator | 🟡 | `tests/test_mach3turn_validator.py` đã có trong CI |
| Test Mach3Turn parser | 🟡 | `tests/test_mach3turn_parser.py` đã có trong CI |
| Test chương trình thật | 🟡 | `tests/test_mach3turn_real_programs.py` đã có trong CI |
| Test SafetyEngine | 🟡 | `tests/test_safety_engine.py` đã có trong CI |
| Test Mach3Turn → LintEngine integration | 🟡 | `tests/test_mach3turn_lint_integration.py` đã có trong CI |
| Test cấm local AI production | 🟡 | `tests/test_ai_provider_policy.py`; offline/production Ollama/unknown-provider đều phải không tạo local/network fallback |
| Workflow chạy trên `mach3turn` push | 🟡 | `ci.yml` đã thêm `mach3turn` vào trigger |
| GitHub Actions CI PASS | ⬜ CHƯA XONG | GitHub vẫn chưa tạo workflow run/status cho branch; chưa được phép đổi các mục 🟡 thành ✅ |
| Ruff PASS | ⬜ CHƯA XONG | Chờ GitHub Actions chạy |

## E. AI Cloud / Subscription

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| Hard no-local guard trong `AIClient` | 🟡 ĐÃ CODE, CHỜ KIỂM CHỨNG | `offline: true` dừng ngay; profile production chặn Ollama; unknown mode không còn fallback Ollama |
| Alias `anthropic`/`claude` → cloud Anthropic | 🟡 ĐÃ CODE, CHỜ KIỂM CHỨNG | Vá lỗi upstream: trước đây mọi mode khác `claude` đều rơi xuống Ollama |
| AI mặc định production | 🟡 ĐÃ CODE, CHỜ KIỂM CHỨNG | `config.example.yaml` để `offline: true`; không tự gọi AI khi mới cài |
| AI Provider abstraction | ⬜ CHƯA XONG | Làm sau khi P0 safety core được CI xác nhận |
| Codex CLI / ChatGPT Plus-Pro | ⬜ CHƯA XONG | Provider ưu tiên số 1 |
| OpenAI API key | ⬜ CHƯA XONG | Key chỉ từ env/credential store; không commit secret |
| Anthropic API provider chuẩn hóa | ⬜ CHƯA XONG | Client cloud hiện có đã được khóa policy; interface provider chung chưa tách |
| Ollama/local model production | ⛔ KHÔNG LÀM | Máy CNC yếu; hard guard chặn local AI ở production profile |
| DeepSeek/OpenRouter | ⬜ P2 | Sau core |

## F. Tool/Turret và máy lận

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| T0101–T0808 validation đầy đủ | ⬜ CHƯA XONG | V0.2 |
| T0909 bị chặn | ⬜ CHƯA XONG | V0.2 |
| Safe tool-change X/Z zone | ⬜ CHƯA XONG | Cần lấy giới hạn thực tế trước khi code |
| Spindle stop trước tool change | ⬜ CHƯA XONG | Policy deterministic, không tự gọi M6/M101 |
| Khuôn/phôi/con lăn R2/R4/R6 | ⬜ CHƯA XONG | V0.6 |
| Collision sweep thân con lăn/cán | ⬜ CHƯA XONG | Không chỉ kiểm tool-tip |
| Gọi trực tiếp NcEther.dll/XHC từ AI | ⛔ KHÔNG LÀM | AI không được điều khiển I/O máy |

## Checkpoint hiện tại

**P0 safety core đã được viết ở mức module + regression tests, nhưng CHƯA công nhận V0.1 là XONG.** Hai điểm còn thiếu để chốt V0.1: (1) GitHub Actions/CI phải chạy và PASS toàn bộ upstream + test mới; (2) production export/UI phải thực sự dùng blocking gate, không chỉ có core function.

### Việc tiếp theo theo đúng thứ tự

1. Bật/khôi phục GitHub Actions cho fork và lấy kết quả Core + GUI/runtime + Ruff.
2. Nếu CI đỏ: sửa đến khi toàn bộ PASS.
3. Nối `Mach3TurnGCodeParser` vào X-Z plotter khi profile là `MACH3TURN_XHC_MKX_ET`.
4. Hiển thị severity rõ trong UI: INFO/WARNING/ERROR/FATAL.
5. Thêm production Export Gate: ERROR/FATAL = không cho xuất `.tap/.nc`.
6. Sau khi P0 PASS mới chuyển sang V0.2 tool/turret safety.
