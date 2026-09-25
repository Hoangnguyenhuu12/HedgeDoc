---
type: rfc
stage: 02
title: "RFC: Đề Xuất Thiết Kế Plugin Trợ Lý AI (React UI Assistant Plugin)"
id: "FSP-PLUGIN-ASSISTANT-02"
status: in_review
tags: [rfc, plugin-assistant, assistant, agentic-loop, tool-calling, react, fsp, stage-02, okf]
---

# RFC: Đề Xuất Thiết Kế Plugin Trợ Lý AI (React UI Assistant Plugin)

> **Định dạng tệp mục tiêu**: `specs/plugin-assistant/02-rfc.md` (Metadata ID: `FSP-PLUGIN-ASSISTANT-02`)  
> **Loại tài liệu**: `rfc`  
> **Trạng thái**: `in_review`  
> **Chặng 2**: Đề xuất thiết kế giải quyết câu hỏi **"AI HOẠT ĐỘNG RA SAO?"** cho phân hệ Plugin Trợ lý AI (`plugin-assistant`) đính lên React UI Harness — Cơ chế nhận thức ngữ cảnh tự động, vòng lặp tác vụ liên hoàn Agentic ReAct đa bước (> 3 bước), nguyên lý bảo mật Whitelist Tool-by-Design, và chính sách kiểm soát an toàn Human-in-the-Loop.  
> **Kiến trúc khung nền tảng ("Kiến Trúc Như Thế Nào?")**: Xem [`../multi-flavor-architecture/02-rfc.md`](../multi-flavor-architecture/02-rfc.md)  
> **Khảo sát kỹ thuật (Chặng 1)**: [`01-research.md`](01-research.md)  
> **Tài liệu tổng quan**: [`README.md`](README.md)

> [!CAUTION]
> **Ba đề xuất trong tài liệu này đã bị thay thế ở Chặng 3.** RFC ghi lại phương án *được cân nhắc*; [`03-decisions.md`](03-decisions.md) ghi lại phương án *được chọn*. Khi hai bên khác nhau, **sổ quyết định thắng**.
>
> | Đề xuất ở RFC này | Thay bằng | Mã quyết định |
> |---|---|---|
> | §3 — bốn nhóm tool `router.*` · `modal.*` · `form.*` · `data.*` do Angular MFE đăng ký | Đúng **hai** client tool tĩnh `ui.navigate` · `ui.open_form`; chốt chặn ở `AssistantActionGateway` **lúc thực thi** | [`QĐ-ASSISTANT-009`](03-decisions.md) |
> | §1.1 — sự kiện `assistant:page-context:changed` | `host:page-context-changed` theo hợp đồng biên của Guest Flavor | [`QĐ-ASSISTANT-008`](03-decisions.md) |
> | §4 — ba quy tắc phê duyệt phân theo nhóm tool | Chính sách phê duyệt do backend quyết bằng `riskClass`; Guest chỉ hiện thẻ C4 và gửi `decide` | [`QĐ-ASSISTANT-009`](03-decisions.md) |

---

## 1. Tóm Tắt Đề Xuất Thiết Kế Nghiệp Vụ AI (Proposal Summary)

Phân hệ `plugin-assistant` được thiết kế dưới dạng **UI Plugin** đính lên khung giao diện React Harness (`React_Assistant/`), phối hợp nhịp nhàng với lõi điều phối `LV.NetClaw` trên backend .NET 10 để vận hành như một **Thư ký số thông minh** với 3 năng lực cốt lõi:

1. **Nhận Thức Ngữ Cảnh Thời Gian Thực (Active Context Awareness)**:
   - Thay vì để AI quét DOM thụ động, Angular MFE chủ động phát các sự kiện ngữ cảnh (`assistant:page-context:changed`) mỗi khi người dùng chuyển trang hoặc mở một văn bản.
   - Ngữ cảnh được nạp vào payload `POST /api/modules/ai/agent/runs/stream` và đưa thẳng vào System Instruction của `LV.NetClaw`.
2. **Vòng Lặp Tác Vụ Liên Hoàn Đa Bước (Multi-step Agentic ReAct Loop)**:
   - Hỗ trợ chuỗi hành động phức tạp hơn 3 bước liên tiếp thông qua chu trình **ReAct (Reason ➔ Act ➔ Observe ➔ Repeat)** được thực thi 100% tại `LV.NetClaw` backend.
   - Giải quyết triệt để vấn đề lệch pha tool khi đổi route bằng cơ chế **SSE Stream + Workspace Client Action Bridge**: NetClaw phát `client.requested`, UI Harness phát `assistant:client-action` sang Angular Host, Angular hoàn tất điều hướng/thao tác và trả về `assistant:client-action-result`. Kết quả được stream ngược lại NetClaw qua `POST /runs/{runId}/client-results/stream` để tiếp tục bước suy luận tiếp theo.
3. **Bảo Mật Bằng Thiết Kế (Whitelist Tool-by-Design & Human-in-the-Loop)**:
   - AI chỉ có thể gọi các tool được Angular MFE đăng ký vào Whitelist.
   - Tích hợp với `PermissionService`: Không có quyền ➔ Không đăng ký tool.
   - Phân loại rõ ràng: Thao tác an toàn (tự động chạy) vs Thao tác đột biến (bắt buộc Action Card / Approval Card người dùng bấm xác nhận).

---

## 2. Thiết Kế Giao Thức Vòng Lặp Agentic Tool Loop

```
[Người Dùng]        [UI Plugin / Harness]          [LV.NetClaw Backend]         [Angular Shell / MFE]
     │                       │                             │                             │
     │ 1. "Tạo hồ sơ ký X"   │                             │                             │
     │ ────────────────────► │                             │                             │
     │                       │ 2. POST /runs/stream        │                             │
     │                       │ ──────────────────────────► │ [VÒNG LẶP BƯỚC 1: SUY LUẬN] │
     │                       │                             │ Cần sang màn hình Trình ký  │
     │                       │ 3. SSE: client.requested    │                             │
     │                       │ ◄────────────────────────── │                             │
     │                       │ 4. dispatch assistant:client-action (navigate_to)         │
     │                       │ ────────────────────────────────────────────────────────► │ Chuyển router sang
     │                       │                                                           │ mfe-tks, nạp MFE
     │                       │ 5. assistant:client-action-result (success)               │
     │                       │ ◄──────────────────────────────────────────────────────── │
     │                       │ 6. POST /client-results/stream                            │
     │                       │ ──────────────────────────► │ [VÒNG LẶP BƯỚC 2: SUY LUẬN] │
     │                       │                             │ Cần điền dữ liệu biểu mẫu   │
     │                       │ 7. SSE: client.requested    │                             │
     │                       │ ◄────────────────────────── │                             │
     │                       │ 8. dispatch assistant:client-action (tks.fill_form)       │
     │                       │ ────────────────────────────────────────────────────────► │ Điền dữ liệu nháp
     │                       │ 9. assistant:client-action-result (success)               │
     │                       │ ◄──────────────────────────────────────────────────────── │
     │                       │ 10. POST /client-results/stream                           │
     │                       │ ──────────────────────────► │ [VÒNG LẶP BƯỚC 3: XÁC NHẬN] │
     │                       │ 11. SSE: approval.requested │                             │
     │                       │ ◄────────────────────────── │                             │
     │ 12. Render Approval   │                             │                             │
     │     Action Card       │                             │                             │
     │ ◄──────────────────── │                             │                             │
     │ 13. [✓ Xác nhận]      │                             │                             │
     │ ────────────────────► │ 14. dispatch assistant:client-action (tks.open_sign_modal)│
     │                       │ ────────────────────────────────────────────────────────► │ Mở Modal ký số
     │                       │ 15. SSE: model.delta + run.completed                      │
     │                       │ ◄────────────────────────── │                             │
     │ 16. "Đã tạo xong và   │                             │                             │
     │     mở modal ký số!"  │                             │                             │
     │ ◄──────────────────── │                             │                             │
```

---

## 3. Thiết Kế Chuẩn Hóa 4 Nhóm Tool Nghiệp Vụ

Mỗi Angular MFE chỉ cần đăng ký các tool thuộc 4 nhóm nghiệp vụ:

1. **Nhóm Router (`router.*`)**:
   - `shell.navigate_to`: Chuyển router sang phân hệ khác.
   - `router.switch_tab`: Chuyển tab trong cùng một trang (ví dụ tab Đính kèm, tab Ý kiến xử lý).
2. **Nhóm Modal (`modal.*`)**:
   - `modal.open_signature`: Mở hộp thoại ký số điện tử.
   - `modal.open_forward`: Mở hộp thoại chuyển tiếp văn bản cho lãnh đạo/phòng ban khác.
3. **Nhóm Form (`form.*`)**:
   - `form.patch_opinion`: Điền ý kiến đề xuất xử lý vào form phê duyệt.
   - `form.set_signer_list`: Cập nhật danh sách người ký duyệt vào form trình ký.
4. **Nhóm Data (`data.*`)**:
   - `data.read_active_document`: Đọc chi tiết các trường của văn bản đang mở.
   - `data.read_selected_table_rows`: Đọc các dòng đang được tích chọn trên bảng dữ liệu.

---

## 4. Chính Sách Phê Duyệt An Toàn (Human-in-the-Loop Policy)

Để bảo đảm an toàn dữ liệu doanh nghiệp:
* **Quy tắc 1 (Safe-Auto)**: Các tool loại `data.*` và `router.*` được tự động thực thi ngay lập tức.
* **Quy tắc 2 (Form-Preview)**: Các tool loại `form.*` điền dữ liệu dưới dạng bản nháp (draft), người dùng nhìn thấy dữ liệu được điền trực quan trên màn hình trước khi quyết định lưu.
* **Quy tắc 3 (Mutation-Confirmation)**: Các tool loại `modal.*` nhạy cảm (ký số, gửi duyệt) bắt buộc AI phải render Action Card trên khung chat; lệnh chỉ phát sang Angular khi người dùng nhấp nút **[Xác nhận]**.

---

## 5. Bảng Đánh Giá Đánh Đổi Kỹ Thuật

| Hạng mục thiết kế | Lợi ích đạt được | Đánh đổi / Rủi ro |
|---|---|---|
| **Agentic Tool Loop đa bước** | Tự động hóa hoàn toàn các kịch bản phức tạp thay vì người dùng phải bấm tay từng bước | Cần kiểm soát số bước tối đa (`MAX_STEPS = 8`) để tránh vòng lặp vô tận |
| **Whitelist Tool-by-Design** | Đảm bảo an toàn tuyệt đối, chống Prompt Injection 100% | AI không thể tự nghĩ ra hành động ngoài danh bạ đăng ký sẵn |
| **Action Card Confirmation** | Người dùng luôn giữ quyền kiểm soát tối cao trước các hành động nhạy cảm | Thêm 1 lần nhấp chuột xác nhận của người dùng |
