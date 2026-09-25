---
type: index
title: "Chỉ Mục Đặc Tả: Plugin Trợ Lý AI (React UI Assistant Plugin)"
id: "FSP-PLUGIN-ASSISTANT-INDEX"
status: draft
tags: [spec-index, plugin-assistant, assistant, react-plugin, slot, fsp, okf]
---

# Feature Index: Plugin Trợ Lý AI (React UI Assistant Plugin)

> **Định dạng tệp**: `specs/plugin-assistant/index.md` (Metadata ID: `FSP-PLUGIN-ASSISTANT-INDEX`)
> **Loại tài liệu**: `index`
> **Trạng thái**: `draft`
> **Tài liệu tổng quan**: [`README.md`](README.md)
> **Kiến trúc khung nền tảng ("Kiến Trúc Như Thế Nào?")**: [`../multi-flavor-architecture/index.md`](../multi-flavor-architecture/index.md)

---

## 1. Bảng Điều Khiển Tiến Độ Các Chặng (Feature Lifecycle Dashboard)

| Chặng | Tệp đặc tả | Trạng thái | Tóm tắt Vai trò & Mục tiêu Kỹ thuật |
|:---:|---|:---:|---|
| **1** | [`01-research.md`](01-research.md) | `in_review` | Khảo sát kỹ thuật: cơ chế nhận thức ngữ cảnh, giao thức Dynamic Tool Calling, vòng lặp Agentic ReAct liên hoàn, nguyên lý Whitelist Tool-by-Design. |
| **2** | [`02-rfc.md`](02-rfc.md) | `in_review` | Đề xuất thiết kế: giao thức điều phối chuỗi tác vụ và chính sách Human-in-the-Loop. |
| **3** | [`03-decisions.md`](03-decisions.md) | `draft` | **17 quyết định `QĐ-ASSISTANT-001..017`** chốt mô hình plugin, sổ thẻ, hợp đồng ngữ cảnh, nguồn kế thừa và nguyên tắc port bằng phép trừ. |
| **4** | [`04-plan.md`](04-plan.md) | `draft` | Phân kỳ bốn pha (28 nhiệm vụ), quy ước nhiệm vụ port bốn phần, sáu rủi ro đã nhận diện, DoD cấp feature. |
| **5** | [`05-spec.md`](05-spec.md) | `draft` | Đặc tả thi công: `PageContext` phẳng, Workspace Client Action, giao thức SSE, máy trạng thái run. Ba mô-đun chuyên sâu tại §2 bên dưới. |
| **6** | [`06-verification.md`](06-verification.md) | `draft` | Phần (a) ma trận kiểm thử bốn tầng T1–T4; phần (b) nhật ký cạm bẫy — đã ghi 3 cạm bẫy của chặng đặc tả và 7 ca biên dự đoán. |

---

## 2. Danh Bạ Mô-đun Chuyên Sâu (`modules/`)

| # | Mô-đun | Trạng thái | Trả lời câu hỏi | Mã QĐ neo vào |
|:-:|---|:-:|---|---|
| **01** | [`01-plugin-contract.md`](modules/01-plugin-contract.md) | `draft` | Tôi cắm năng lực mới vào đâu, trả về gì, gỡ ra sao? Hợp đồng `IUiPlugin`, `IPluginContext`, ba khe, vòng đời 4 trạng thái, luật đặt tên đóng góp, ranh giới chặn lỗi ba tầng. | `001` `002` `003` `004` `011` `012` `013` |
| **02** | [`02-conversation-node-registry.md`](modules/02-conversation-node-registry.md) | `draft` | Sự kiện nào ra thẻ nào, và luật đó kiểm ở đâu? Sổ 16 thẻ C1–C16, sổ widget theo `widgetKind`, ba tầng phép chiếu headless, ma trận 20 dòng `$kind`. | `005` `006` `015` `016` |
| **03** | [`03-workbench-assistant-port-map.md`](modules/03-workbench-assistant-port-map.md) | `draft` | Kéo mã về từ đâu, hạng nào, phải chỉnh chỗ nào? Phân hạng A/B/C/D cho 116 tệp nguồn (55 port về, **0 viết mới**), thứ tự port sáu đợt, ngân sách bundle. | `017` `014` `001` `005` `013` `015` |

> **Tổng số mô-đun**: 3.

---

## 3. Bảng Ánh Xạ Mã Quyết Định (`QĐ-ASSISTANT-xxx` ➔ Vị trí đặc tả)

| Mã QĐ | Chủ đề | Đặc tả thi công tại |
|---|---|---|
| `QĐ-ASSISTANT-001` | Plugin là đơn vị tổ chức mã, không phải đơn vị phân phối | [`modules/01 §1`](modules/01-plugin-contract.md) |
| `QĐ-ASSISTANT-002` | Ba khe tĩnh thay cho `SlotCore` 4 hạng | [`modules/01 §3`](modules/01-plugin-contract.md) |
| `QĐ-ASSISTANT-003` | Sổ đăng ký tĩnh, không microkernel fiber | [`modules/01 §2`](modules/01-plugin-contract.md) |
| `QĐ-ASSISTANT-004` | Ranh giới sở hữu Khung ↔ Plugin | [`modules/01 §1.3`](modules/01-plugin-contract.md) |
| `QĐ-ASSISTANT-005` | Sổ 16 thẻ C1–C16 theo tên linh kiện mã tham chiếu | [`modules/02 §3.1`](modules/02-conversation-node-registry.md) |
| `QĐ-ASSISTANT-006` | `ui.widget` là sự kiện hạng nhất | [`modules/02 §4.3`](modules/02-conversation-node-registry.md) |
| `QĐ-ASSISTANT-007` | `PageContext` trên dây là chuỗi phẳng | [`05-spec.md §3`](05-spec.md) · [`modules/01 §6.2`](modules/01-plugin-contract.md) |
| `QĐ-ASSISTANT-008` | Tên sự kiện biên chốt theo `React_Assistant/CLAUDE.md §3` | [`05-spec.md §3.2`](05-spec.md) |
| `QĐ-ASSISTANT-009` | Chỉ hai client tool tĩnh `ui.navigate` · `ui.open_form` | [`README.md §6`](README.md) · [`05-spec.md §4`](05-spec.md) |
| `QĐ-ASSISTANT-010` | Mọi lượt ra biên nằm trong `bridge/` | [`05-spec.md §5.3`](05-spec.md) · [`modules/01 §6`](modules/01-plugin-contract.md) |
| `QĐ-ASSISTANT-011` | Quy ước tên đóng góp mang tiền tố plugin | [`modules/01 §4.4`](modules/01-plugin-contract.md) |
| `QĐ-ASSISTANT-012` | Không sổ dịch vụ chéo plugin | [`modules/01 §3.2`](modules/01-plugin-contract.md) |
| `QĐ-ASSISTANT-013` | Ngân sách bundle khởi động ≤ 100 KB gzip | [`modules/03 §5.2`](modules/03-workbench-assistant-port-map.md) |
| `QĐ-ASSISTANT-014` | Nguồn kế thừa là gói `workbench.assistant`, port 4 hạng | [`modules/03`](modules/03-workbench-assistant-port-map.md) |
| `QĐ-ASSISTANT-015` | Phép chiếu ba tầng headless, kiểm trên Node | [`modules/02 §4`](modules/02-conversation-node-registry.md) |
| `QĐ-ASSISTANT-016` | Bỏ qua `$kind` lạ, không được lỗi | [`modules/02 §4.5`](modules/02-conversation-node-registry.md) |
| `QĐ-ASSISTANT-017` | Port bằng phép TRỪ, không bằng phép viết lại | [`modules/03 §2.2`](modules/03-workbench-assistant-port-map.md) · [`§2.3`](modules/03-workbench-assistant-port-map.md) |

---

## 4. Sai Lệch Đã Phát Hiện & Đã Hàn Gắn

Sáu sai lệch phát hiện khi rà soát chéo, **đã sửa xong trong cùng lượt**. Chi tiết: [`03-decisions.md §3`](03-decisions.md).

| # | Tệp đã sửa | Sai lệch | Trạng thái |
|:-:|---|---|:-:|
| **V1** | `multi-flavor/modules/01` §3 | Cây thư mục thiếu `slots/` và `plugins/`, đặt nhầm hợp đồng plugin vào `sdk/` | ✅ đã sửa |
| **V2** | `multi-flavor/modules/01` §5 | Ma trận sự kiện ➔ thẻ thiếu `ui.widget`, `model.queued`, nhóm `run.*` thất bại và `error` | ✅ đã sửa |
| **V3** | `multi-flavor/modules/01` §3, §4 | `useNetClawRun.ts` đặt trong `sdk/`, phá luật `sdk/` không phụ thuộc `bridge/` | ✅ đã sửa |
| **V4** | `React_Assistant/src/plugins/assistant/README.md` §1 | Câu chữ ranh giới khung ↔ plugin lệch với vị trí thật của sổ thẻ hội thoại | ✅ đã sửa |
| **V5** | `React_Assistant/src/plugins/README.md` · `ARCHITECTURE.md` | Tệp khai báo plugin ghi đuôi `.ts` nhưng mang JSX ⇒ phải là `.tsx` | ✅ đã sửa |
| **V6** | `05-spec.md` §5.3 · `multi-flavor/modules/01` §4 | **Đặc tả một bộ đọc SSE tự viết** bỏ sót bốn ca mà bản trong kho tham chiếu đã xử đúng — trong đó ca CR cuối chunk làm mất phần đuôi câu trả lời, hỏng im lặng | ✅ đã sửa — chuyển sang port nguyên trạng |


## 5. Liên Kết Nhanh & Điều Hướng

- 📌 **Tổng quan feature**: [`README.md`](README.md)
- ⚖️ **Sổ quyết định kiến trúc**: [`03-decisions.md`](03-decisions.md)
- 🧩 **Hợp đồng plugin & ba khe**: [`modules/01-plugin-contract.md`](modules/01-plugin-contract.md)
- 🃏 **Sổ thẻ hội thoại & phép chiếu**: [`modules/02-conversation-node-registry.md`](modules/02-conversation-node-registry.md)
- 🧬 **Bản đồ port gói `workbench.assistant`**: [`modules/03-workbench-assistant-port-map.md`](modules/03-workbench-assistant-port-map.md)
- 🗺️ **Kế hoạch phân kỳ**: [`04-plan.md`](04-plan.md)
- 📐 **Đặc tả thi công**: [`05-spec.md`](05-spec.md)
- ✅ **Ma trận kiểm thử & cạm bẫy**: [`06-verification.md`](06-verification.md)
- 🏛️ **Kiến trúc khung nền tảng**: [`../multi-flavor-architecture/`](../multi-flavor-architecture/index.md)
- 🧠 **Hợp đồng API backend**: [`AGENT_CHAT_API.md`](../../LV_Shell/src/NetClaw/docs/host-lv-shell/AGENT_CHAT_API.md)
