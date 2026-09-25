---
type: spec
stage: 05
title: "Đặc Tả Kỹ Thuật: Plugin Trợ Lý AI (React UI Assistant Plugin Specification)"
id: "FSP-PLUGIN-ASSISTANT-05"
status: draft
tags: [spec, plugin-assistant, assistant, agentic-loop, tool-calling, react, fsp, stage-05, okf]
---

# Đặc Tả Kỹ Thuật: Plugin Trợ Lý AI (React UI Assistant Plugin Specification)

> **Định dạng tệp mục tiêu**: `specs/plugin-assistant/05-spec.md` (Metadata ID: `FSP-PLUGIN-ASSISTANT-05`)  
> **Loại tài liệu**: `spec`  
> **Trạng thái**: `draft`  
> **Chặng 5**: Hợp đồng kỹ thuật thi công cho phân hệ Plugin Trợ lý AI (`plugin-assistant`) đính lên React UI Harness — nhận thức ngữ cảnh (`PageContext` phẳng), hợp đồng tác vụ client (`assistant:client-action`), giao thức luồng SSE bán phi trạng thái, và chốt chặn hành động lúc thực thi.
> **Ba mô-đun chuyên sâu**: [`modules/01-plugin-contract.md`](modules/01-plugin-contract.md) (hợp đồng plugin & ba khe) · [`modules/02-conversation-node-registry.md`](modules/02-conversation-node-registry.md) (sổ thẻ C1–C16 & phép chiếu) · [`modules/03-workbench-assistant-port-map.md`](modules/03-workbench-assistant-port-map.md) (bản đồ port).
> **Sổ quyết định**: [`03-decisions.md`](03-decisions.md) — 17 mã `QĐ-ASSISTANT-001..017`.  
> **Kiến trúc khung nền tảng ("Kiến Trúc Như Thế Nào?")**: Xem [`../multi-flavor-architecture/05-spec.md`](../multi-flavor-architecture/05-spec.md)  
> **Đặc tả UI Harness chi tiết**: Xem [`../multi-flavor-architecture/modules/01-react-assistant-harness.md`](../multi-flavor-architecture/modules/01-react-assistant-harness.md)  
> **Khảo sát kỹ thuật (Chặng 1)**: [`01-research.md`](01-research.md)  
> **Tài liệu tổng quan**: [`README.md`](README.md)

---

## 1. Bất Biến Nghiệp Vụ & An Toàn (Business & Safety Invariants)

**Nguồn sự thật của 12 bất biến `[INV-ASSISTANT-01..12]` là [`README.md §6`](README.md).** Tài liệu này không chép lại nội dung chúng — chép lại là dựng ra một nguồn thứ hai và nó sẽ lệch ngay lần đầu có người sửa. Bảng dưới đây chỉ nói **mỗi bất biến được thi hành ở đâu trong đặc tả này**, và mục nào của tài liệu giữ chi tiết.

| Mã bất biến | Điểm thi hành kỹ thuật | Chi tiết tại |
|---|---|---|
| `INV-ASSISTANT-01` Chốt chặn lúc thực thi | `AssistantActionGateway` của Angular Host, chạy **sau** khi nhận `assistant:client-action` và **trước** khi chạm Router | §4.5 |
| `INV-ASSISTANT-02` Không có trong danh mục = không làm được | Kết quả từ chối quay ngược thành `client-results` với `isError: true` kèm lý do | §4.5 · §7 |
| `INV-ASSISTANT-03` Kiểm quyền lúc thực thi | `PermissionService.hasPermission()` gọi trong cùng lượt xử lý `assistant:client-action` | §4.5 |
| `INV-ASSISTANT-04` Vòng lặp có chờ đợi | Mỗi `callId` nhận **đúng một** `POST runs/{runId}/client-results/stream` | §4.2 · §6.1 |
| `INV-ASSISTANT-05` Kiểm soát đột biến | `approval.requested` ➔ thẻ C4 ➔ `decide` ➔ `resume/stream` | §5.1 · §6 |
| `INV-ASSISTANT-06` Zero unauthorized persistence | Token và ngữ cảnh chỉ sống trong bộ nhớ; xóa khi nhận `host:auth-revoked` | §3.3 · §5.3 |
| `INV-ASSISTANT-07` Vòng lặp thuộc backend | Guest không có đường gọi LLM: `bridge/` chỉ biết sáu điểm cuối của §5.1 | §5 · §6 |
| `INV-ASSISTANT-08` Mở rộng theo khe cắm | Ba khe `slot:header.actions` · `slot:main.view` · `slot:chat.widget` | [`modules/01`](modules/01-plugin-contract.md) |
| `INV-ASSISTANT-09` Ngữ cảnh trên dây là chuỗi phẳng | Phép làm phẳng chạy **một lần** tại `bridge/workspace-event.bridge.ts` | §3.1 · §3.2 |
| `INV-ASSISTANT-10` Sự kiện lạ không gây lỗi | Nhánh mặc định của bảng chiếu: `debug` một dòng, không sinh nút | [`modules/02 §4.2`](modules/02-conversation-node-registry.md) |
| `INV-ASSISTANT-11` Plugin không chạm biên | Plugin gọi facade hook; mọi `fetch` nằm trong `bridge/` | §5.3 · [`modules/01 §6.3`](modules/01-plugin-contract.md) |
| `INV-ASSISTANT-12` Port chứ không phụ thuộc | Mỗi tệp kế thừa mang khối chú thích nguồn gốc | [`modules/03 §4.6`](modules/03-workbench-assistant-port-map.md) |

Thêm một bất biến **chỉ thuộc về tài liệu này**, vì nó nói về bố cục chứ không nói về nghiệp vụ:

* **`[INV-ASSISTANT-SPEC-01]` Chiếu Modal Toàn Màn Hình Không Co Cụm (Full-Screen Modal Projection)**: Giao diện cấu hình hoặc tiện ích mở rộng phức tạp (Cài đặt, Thư viện câu lệnh, So sánh văn bản) khi kích hoạt từ hàng nút Header hoặc từ một thẻ hội thoại **bắt buộc mở qua `ctx.openModal()`** để hiện dạng Modal 800–1000px trên tầng Modal Portal của Shadow Root. Tuyệt đối không nhồi nhét, co cụm hoặc làm vỡ bố cục 420px của ngăn kéo chat.

---

## 2. Giao Diện & Giải Phẫu Trợ Lý AI (UI Anatomy Inside Shadow Root)

Trợ lý AI ngự trị trong Shadow Root của `<ai-assistant-host>`, hiển thị dạng **Ngăn kéo trượt (Slide-out Drawer rộng 420px)** hoặc **Floating Button**:

```
┌────────────────────────────────────────────────────────┐
│ [🤖 Header Slot: slot:header.actions]     [⚙] [—] [✕]  │
│ Trợ lý AI DCS LV_Platform                              │
├────────────────────────────────────────────────────────┤
│ [Context Banner]: 📄 Văn bản đến: 125/TTr-VP           │
├────────────────────────────────────────────────────────┤
│ [Main View Slot: slot:main.view]                       │
│ ConversationList (Non-virtualized, native Ctrl+F)      │
│                                                        │
│ 👤 UserBubble (C1): "Lập hồ sơ trình ký tờ trình này"  │
│                                                        │
│ 🤖 AssistantBubble:                                    │
│ "Em đang tiến hành các bước lập hồ sơ trình ký..."     │
│                                                        │
│ ┌────────────────────────────────────────────────────┐ │
│ │ 📋 LiveTaskChecklist (NetClaw ui.widget):          │ │
│ │ [✓] 1. Chuyển sang phân hệ Trình ký số (mfe-tks)   │ │
│ │ [✓] 2. Điền thông tin trích yếu và người ký duyệt  │ │
│ │ [⏳] 3. Chờ xác nhận kích hoạt hộp ký số           │ │
│ └────────────────────────────────────────────────────┘ │
│                                                        │
│ ┌────────────────────────────────────────────────────┐ │
│ │ 🛡️ ToolApprovalCard (approval.requested):          │ │
│ │ • Hành động: Mở hộp thoại ký số điện tử            │ │
│ │ • Người ký: Nguyễn Văn A (Trưởng phòng)            │ │
│ │                                                    │ │
│ │   [✓ Xác nhận mở ký]          [✕ Hủy bỏ]           │ │
│ └────────────────────────────────────────────────────┘ │
├────────────────────────────────────────────────────────┤
│ [AssistantComposer (2-Tier Layout)]:                   │
│ ┌────────────────────────────────────────────────────┐ │
│ │ [Tầng 1]: Gợi ý: [Tóm tắt] [Trình ký] [Tìm quy chế]│ │
│ ├────────────────────────────────────────────────────┤ │
│ │ [Tầng 2]: [ Nhập yêu cầu tại đây...        ][ ⮞ ]  │ │
│ └────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────┘
```

### 2.1 Sổ Thẻ Hội Thoại C1–C16 (Conversation Node Registry)

Mỗi sự kiện từ luồng SSE của `LV.NetClaw` được chiếu thành một **nút** rồi tra sổ ra một thẻ hiển thị. Sổ chốt **16 thẻ C1–C16** mang đúng tên linh kiện của mã kế thừa — [`QĐ-ASSISTANT-005`](03-decisions.md).

> **Bảng đầy đủ 16 thẻ, ma trận `$kind` ➔ `nodeType` và luật chọn thẻ cho một nút tool: [`modules/02-conversation-node-registry.md §3.1`](modules/02-conversation-node-registry.md).** Tài liệu này không chép lại bảng đó.

Ba điều cần nhớ ngay tại đây vì chúng hay bị làm sai:

1. **Không có thẻ lỗi riêng.** Lỗi là một **trạng thái** của thẻ (`status: 'error'`), không phải một loại thẻ. Lỗi cấp kết nối/phiên không thuộc hội thoại — nó hiện ở `AssistantBanner` của khung.
2. **`client.requested` không có thẻ riêng.** Nó dùng chung thẻ C5 `ToolCardGeneric` ở trạng thái "đang chờ màn hình thực hiện", vì với người dùng thì một tool chạy ở server và một tool chạy ở trình duyệt là cùng một việc.
3. **Widget không phải thẻ.** `ui.widget` đi đường riêng qua sổ `widgetKind → component`, xen vào dòng hội thoại tại vị trí lần `upsert` **đầu tiên** — xem [`modules/02 §4.3`](modules/02-conversation-node-registry.md).

### 2.2 Cơ Chế Chiếu Modal Toàn Màn Hình Cho Plugin (Full-Screen Modal Projection)

Để các view mở rộng (Cài đặt, Thư viện câu lệnh, So sánh văn bản) không bị co cụm trong ngăn kéo 420px, plugin gọi `ctx.openModal()` — bề mặt duy nhất, do khung cấp:

* **Không nhồi nhét vào Drawer**: plugin không can thiệp DOM của ngăn kéo.
* **Chiếu thẳng lên Tầng Modal Portal**: `ctx.openModal({ title, size: 'lg', content: <SettingsView /> })`, trả về disposer đóng modal.
* **Trải nghiệm toàn màn hình thống nhất**:
  - Modal 800–1000px hiện chính giữa màn hình trên phông nền mờ.
  - Toàn bộ giao diện Angular MFE và ngăn kéo đều mờ đồng bộ.
  - **Khóa cuộn nền là việc của Angular Shell**: Guest phát `assistant:request-scroll-lock { locked: true }` chứ **không** tự đặt `document.body.style.overflow` — bất biến #2 của Guest Flavor cấm chạm DOM ngoài Shadow Root.
  - 100% định kiểu kế thừa từ Shadow Root, không rò một class nào ra ngoài.
  - `Escape` và click ra ngoài backdrop đóng modal và trả quyền cuộn cho trang nền (phát `{ locked: false }`).
  - Bộ nghe `Escape` gắn vào **Shadow Root**, không gắn vào `document`.

---

## 3. Cơ Chế Nhận Thức Ngữ Cảnh (Context Awareness Protocol)

Khi người dùng thao tác, chuyển trang hoặc chọn tài liệu trong Angular, Angular tự động phát thông điệp cập nhật ngữ cảnh:

### 3.1 Hợp Đồng Dữ Liệu Ngữ Cảnh — Hai Hình Dạng, Một Nguồn

> [!IMPORTANT]
> **Ngữ cảnh trên dây là chuỗi phẳng** — `[INV-ASSISTANT-09]`, [`QĐ-ASSISTANT-007`](03-decisions.md). Backend nhận `Dictionary<string, string>`: **không object lồng, không mảng**. Một `formSummary` dạng object gửi lên là mất dữ liệu im lặng hoặc hỏng giải tuần tự, tùy cấu hình — và không có lỗi nào trên console để lần ra.

**Hình dạng trong bộ nhớ Guest** (giàu kiểu, tiện dùng ở tầng hiển thị):

```typescript
export interface PageContext {
  readonly module: string;            // 'QLVB' · 'TKS' · 'TVDT' · 'LEGAL'
  readonly route: string;             // '/qlvb/document/detail/DOC-2026-99'
  readonly entityType?: string;       // 'Document' · 'Task' · 'Folder'
  readonly entityId?: string;         // 'DOC-2026-99'
  readonly entityTitle?: string;      // 'Chi tiết Văn bản đến: 125/TTr-VP'
  readonly selection?: string;        // Đoạn văn bản người dùng đang bôi đen
  readonly lang?: string;             // 'vi-VN'
  /** Dữ liệu tóm tắt trên form. Bị LÀM PHẲNG thành `form.<khóa>` trước khi gửi. */
  readonly formSummary?: Readonly<Record<string, string | number | boolean | null>>;
}
```

**Hình dạng trên dây** (thứ thật sự gửi đi):

```typescript
/** Đúng hình dạng `Dictionary<string,string>` mà backend khai. */
export type WireContext = Readonly<Record<string, string>>;

/**
 * Phép làm phẳng — chạy MỘT LẦN tại `bridge/workspace-event.bridge.ts`.
 * Guest không bao giờ nhìn thấy hai dạng cùng lúc, nên chúng không có chỗ để phân kỳ.
 */
export function flattenContext(ctx: PageContext): WireContext;
```

**Bốn luật của phép làm phẳng:**

1. `formSummary` trải thành khóa `form.<khóa>`; giá trị ép về chuỗi (`null` ⇒ bỏ hẳn khóa, không gửi chuỗi `"null"`).
2. Trường vắng mặt hoặc rỗng ⇒ **bỏ hẳn khóa**, không gửi chuỗi rỗng — một khóa rỗng vẫn tốn token trong prompt.
3. Khóa mở đầu bằng `_` dành cho dữ liệu nội bộ và **không được đưa vào prompt** — đây là hợp đồng backend, không phải quy ước của Guest.
4. `selection` cắt ở **2.000 ký tự**. Người dùng bôi đen cả trang văn bản là ca thường gặp, và một `selection` không giới hạn sẽ đẩy trọn ngữ cảnh ra khỏi cửa sổ token.

### 3.2 Luồng Đồng Bộ Ngữ Cảnh Vào Luồng NetClaw Run

1. **Lắng nghe sự kiện biên.** Tên sự kiện chốt theo [`React_Assistant/CLAUDE.md §3`](../../React_Assistant/CLAUDE.md) — [`QĐ-ASSISTANT-008`](03-decisions.md). Bộ nghe đăng ký **một lần** trong `bridge/`, không đăng ký trong component:

   ```typescript
   // src/bridge/workspace-event.bridge.ts
   window.addEventListener('host:page-context-changed', ((e: CustomEvent<PageContext>) => {
     useAssistantStore.getState().setActiveContext(flattenContext(e.detail));
   }) as EventListener, { signal: abortController.signal });
   ```

   `{ signal }` chứ không phải `removeEventListener` thủ công: một `AbortController` duy nhất gỡ sạch mọi bộ nghe khi `unmountFlavor()` chạy, và không có cách nào bỏ sót một cái.

2. **Đính kèm vào Request.** Mỗi lượt gửi, ngữ cảnh **đã phẳng** đi kèm payload tới `POST runs/stream`:

   ```json
   {
     "agentKey": "tro-ly-ca-nhan",
     "message": "Lập hồ sơ trình ký văn bản này giúp anh",
     "runId": "run-2026-001",
     "context": {
       "module": "QLVB",
       "route": "/qlvb/document/detail/DOC-2026-99",
       "entityType": "Document",
       "entityId": "DOC-2026-99",
       "entityTitle": "Chi tiết Văn bản đến: 125/TTr-VP",
       "lang": "vi-VN",
       "form.documentNumber": "125/TTr-VP",
       "form.summary": "Tờ trình mua sắm máy chủ 2026",
       "form.sender": "Phòng CNTT"
     }
   }
   ```

3. **Tiêm vào Prompt của NetClaw Backend.** Lõi .NET 10 nạp khối ngữ cảnh vào System Instruction của lượt chạy. **Nội dung và định dạng khối này thuộc backend**; Guest không giả định gì về nó ngoài việc mọi khóa đã gửi đều có thể xuất hiện:

   ```text
   [NGỮ CẢNH HIỆN HÀNH CỦA NGƯỜI DÙNG]:
   - Phân hệ: QLVB (Route: /qlvb/document/detail/DOC-2026-99)
   - Thực thể: Document (Mã: DOC-2026-99)
   - Tiêu đề: Chi tiết Văn bản đến: 125/TTr-VP
   - form.documentNumber: 125/TTr-VP
   - form.summary: Tờ trình mua sắm máy chủ 2026
   - form.sender: Phòng CNTT
   ```

### 3.3 Vòng Đời Ngữ Cảnh & Danh Tính

| Sự kiện từ Host | Guest làm gì |
|---|---|
| `FLAVOR_INIT_HANDSHAKE` | Nhận `sessionId`, người dùng, `accessToken`, `expiresAt`, `apiBaseUrl`, ngữ cảnh ban đầu. Giữ **trong bộ nhớ**, không ghi kho bền vững nào |
| `host:page-context-changed` | Làm phẳng rồi thay toàn bộ ngữ cảnh hiện hành. Lượt chat **đang chạy** không bị ảnh hưởng — ngữ cảnh chỉ đính vào lượt kế tiếp |
| `host:auth-token-refreshed` | Thay token trong bộ nhớ. Luồng SSE đang mở giữ nguyên; token mới áp cho request kế tiếp |
| `host:auth-revoked` | **Hủy ngay** mọi `AbortController`, xóa token, xóa hội thoại khỏi bộ nhớ, chạy `disposeAll()` của sổ plugin |

---

## 4. Hợp Đồng Tác Vụ Client & Cầu Nối Workspace (Workspace Client Action Contract)

Để thực thi tác vụ trên giao diện người dùng Angular (điều hướng, mở popup, điền form), `LV.NetClaw` phát sự kiện SSE `client.requested`. UI Plugin phối hợp cùng UI Harness thực thi qua EventBus:

### 4.1 Cấu Trúc Yêu Cầu Tác Vụ Client (`IWorkspaceClientActionRequest`)
```typescript
export interface IWorkspaceClientActionRequest {
  readonly callId: string;       // Định danh duy nhất của lệnh gọi, do backend sinh
  readonly toolName: string;     // CHỈ 'ui.navigate' hoặc 'ui.open_form' — xem §4.3
  readonly argumentsJson: string; // '{"route": "/tks/create", "prefill": {"sourceDocId": "DOC-99"}}'
}
```

### 4.2 Cấu Trúc Phản Hồi Kết Quả Tác Vụ Client (`IWorkspaceClientActionResult`)
```typescript
export interface IWorkspaceClientActionResult {
  callId: string;
  content: string;               // vd: "Đã mở form /tks/create với dữ liệu điền sẵn"
  isError?: boolean;             // false nếu thành công, true nếu người dùng hủy/lỗi
}
```

### 4.3 Danh Mục Client Tool — Đúng Hai Tool Tĩnh

> [!IMPORTANT]
> Chốt tại [`QĐ-ASSISTANT-009`](03-decisions.md). `LV.NetClaw` khai **đúng hai** client tool, và trong cả hai thì `route` là **chuỗi tự do do model sinh ra**. Không có danh bạ tool nào do Angular đăng ký, vì model không bao giờ nhìn thấy một danh bạ như vậy. Bốn nhóm `router.*` · `modal.*` · `form.*` · `data.*` từng đề xuất ở [`02-rfc.md §3`](02-rfc.md) **không thuộc trạng thái đích**.

| `toolName` | `argumentsJson` | Angular Host làm gì | `content` trả về |
|---|---|---|---|
| `ui.navigate` | `{"route": "/qlvb/inbox"}` | Điều hướng Router, nạp chunk MFE nếu cần | `"Đã mở màn hình Văn bản đến"` |
| `ui.open_form` | `{"route": "/tks/create", "prefill": {"title": "…", "signers": ["…"]}}` | Điều hướng tới route, điền sẵn các trường. **Người dùng tự bấm Gửi/Lưu** | `"Đã mở form /tks/create với 3 trường điền sẵn"` |

**Hai hệ quả phải hiện thực đúng, không được bỏ qua:**

* Mọi thao tác nghiệp vụ khác — mở hộp ký số, chuyển tiếp văn bản, đọc dòng đang chọn — đều biểu diễn qua `ui.navigate` hoặc `ui.open_form` tới một route tương ứng. Không phát minh `toolName` mới ở phía Guest: backend sẽ không bao giờ gửi nó, và một nhánh xử lý không bao giờ chạy là mã chết.
* Một `toolName` **lạ** đến từ backend ⇒ Guest trả thẳng `isError: true` kèm `content` nói rõ "Trợ lý chưa hỗ trợ thao tác này trên giao diện", **không** ném và **không** nuốt `callId`.

### 4.4 Quy Trình Cầu Nối Client Action Phía React

```typescript
// src/bridge/workspace-event.bridge.ts — BIÊN DUY NHẤT, không nằm trong plugin hay component

const CLIENT_ACTION_TIMEOUT_MS = 30_000;

export function requestClientAction(
  request: IWorkspaceClientActionRequest,
  signal: AbortSignal,
): Promise<IWorkspaceClientActionResult> {
  const { callId, toolName, argumentsJson } = request;

  let args: unknown;
  try {
    args = JSON.parse(argumentsJson || '{}');
  } catch {
    // Tham số hỏng là một KẾT QUẢ, không phải một ngoại lệ: mỗi callId luôn phải
    // có đúng một kết quả, nếu không run treo ở `WaitingClient` tới khi người dùng huỷ.
    return Promise.resolve({ callId, content: 'Tham số không phải JSON hợp lệ', isError: true });
  }

  return new Promise<IWorkspaceClientActionResult>((resolve) => {
    const settle = (result: IWorkspaceClientActionResult) => {
      clearTimeout(timer);
      controller.abort();          // gỡ bộ nghe qua `signal`, không cần removeEventListener
      resolve(result);
    };

    const controller = new AbortController();
    // Hủy lượt mount ⇒ hủy luôn lượt chờ này; không có listener nào sống sót.
    signal.addEventListener('abort', () => settle({ callId, content: 'Phiên đã đóng', isError: true }),
      { signal: controller.signal });

    window.addEventListener('assistant:client-action-result', ((e: CustomEvent<IWorkspaceClientActionResult>) => {
      if (e.detail.callId === callId) settle(e.detail);
    }) as EventListener, { signal: controller.signal });

    // Angular Host không trả lời trong hạn ⇒ vẫn phải có kết quả. Im lặng là treo hội thoại.
    const timer = setTimeout(
      () => settle({ callId, content: `Màn hình không phản hồi sau ${CLIENT_ACTION_TIMEOUT_MS / 1000}s`, isError: true }),
      CLIENT_ACTION_TIMEOUT_MS,
    );

    window.dispatchEvent(new CustomEvent('assistant:client-action', {
      detail: { callId, toolName, arguments: args },
    }));
  });
}
```

**Ba luật của cầu nối này, cả ba đều bắt nguồn từ `[INV-ASSISTANT-04]`:**

1. **Mỗi `callId` nhận đúng một kết quả** — `settle()` gọi `controller.abort()` ngay, nên lần phát thứ hai không tới được ai.
2. **Mỗi `callId` luôn phải có kết quả.** Tham số hỏng, hết hạn chờ, phiên đóng: cả ba đều là `isError: true` có nội dung, không phải một lời hứa không bao giờ giải quyết.
3. **Bộ nghe gỡ bằng `AbortSignal`, không bằng `removeEventListener`.** Một `AbortController` duy nhất cho cả bộ nghe, timer và lượt hủy — không có đường nào bỏ sót.

### 4.5 Chốt Chặn Phía Angular Host (`AssistantActionGateway`)

Guest **xin**, Shell **làm**, Shell **trả kết quả**. Toàn bộ phép kiểm nằm ở Angular, chạy trong cùng lượt xử lý `assistant:client-action`:

```text
Nhận assistant:client-action { callId, toolName, arguments }
  │
  ├─ 1. toolName có trong { ui.navigate, ui.open_form }?     ✗ ➔ isError, "thao tác chưa hỗ trợ"
  ├─ 2. route khớp một mục của AssistantActionCatalog?        ✗ ➔ isError, "route không nằm trong danh mục"
  ├─ 3. PermissionService.hasPermission(policy của mục đó)?   ✗ ➔ isError, "bạn không có quyền …"
  ├─ 4. Router.navigate(route)  ·  form.patchValue(prefill)
  └─ 5. Phát assistant:client-action-result { callId, content, isError:false }
```

Bốn điểm bắt buộc:

* **Kiểm quyền ở bước 3, không ở lúc đăng ký** — quyền người dùng đổi được giữa phiên (`[INV-ASSISTANT-03]`).
* **Fail-Closed**: không khớp danh mục thì từ chối, không "đoán route gần đúng".
* **Lý do từ chối phải là văn bản đọc được cho người dùng**, vì nó quay ngược lên thành câu trả lời của agent — xem kịch bản ở [`modules/02 §5.3`](modules/02-conversation-node-registry.md).
* **Danh mục `AssistantActionCatalog` thuộc `Angular_Workspace/`**, không thuộc đặc tả này: nó phải khớp bảng route thật của từng MFE và ma trận quyền của `PermissionService`.

---

## 5. Giao Thức Luồng Sự Kiện HTTP POST + SSE (Real-Time SSE Streaming Protocol)

Khác với WebSocket yêu cầu giữ kết nối TCP nhàn rỗi (idle socket) tốn tài nguyên máy chủ, hệ sinh thái `LV_Platform` chuẩn hóa giao thức **HTTP POST + Server-Sent Events (SSE)** theo hợp đồng `AGENT_CHAT_API.md`.

### 5.1 Endpoint & Định Tuyến Luồng

Mọi đường dẫn ghép tương đối trên `apiBaseUrl` **nhận từ handshake**. Cấm nhúng `/api/modules/...`, tên host hay cổng vào mã — `apiUrl` khác nhau giữa dev, IIS và Docker.

| Việc | Lời gọi | Payload |
|---|---|---|
| Khởi tạo lượt chạy | `POST runs/stream` | `{ agentKey?, message, context?, runId?, threadId? }` |
| Gửi tin nhắn trong run hiện hành | `POST runs/{runId}/messages/stream` | `{ message, context? }` |
| Gửi kết quả tác vụ client | `POST runs/{runId}/client-results/stream` | `{ callId, content, isError? }` |
| Quyết định phê duyệt | `POST approvals/{approvalId}/decide` | `{ approve: boolean, comment? }` |
| Tiếp tục run sau khi duyệt | `POST runs/{runId}/resume/stream` | — |
| Đọc trạng thái run | `GET runs/{runId}` | — |
| Replay phục hồi lịch sử | `GET runs/{runId}/events?after={seq}` | — |
| Hủy run đang chạy | `POST runs/{runId}/cancel` | `{ reason? }` |

**Phục hồi sau mất kết nối là hai bước, không phải một.** Không có cơ chế nối lại luồng SSE cũ: `GET runs/{runId}` xem `state`, rồi `GET runs/{runId}/events?after={seq cuối đã nhận}` dựng lại phần bỏ lỡ. `state` là `WaitingClient` / `WaitingApproval` thì xử lý tiếp theo §4 / §6.

### 5.2 Danh Mục Các Sự Kiện SSE Chuẩn Hóa

Tên sự kiện `event:` **bằng đúng** `$kind` trong JSON. Bảng dưới là danh mục đủ; luật chiếu chi tiết nằm ở [`modules/02 §4.2`](modules/02-conversation-node-registry.md).

| Tên sự kiện | Payload rút gọn | Hành vi phía Guest |
|---|---|---|
| `message.user` | `{ seq, text, source }` | Thẻ **C1**. `source === 'harness'` là lời nhắc nội bộ — **bỏ qua**, không hiện |
| `model.delta` | `{ textDelta }` *(hoặc `reasoningDelta`)* | Nối chữ vào thẻ **C2**; nhánh reasoning vào thẻ **C3** |
| `model.responded` | `{ message: { text, toolCalls[] }, usage, finishReason }` | Đóng thẻ C2. `toolCalls` rỗng ⇒ đây là câu trả lời của lượt |
| `model.queued` | `{ providerKey, waitedMs }` | Thẻ **C13** "đang chờ tới lượt". **Phù du**: không có trong replay, xóa khi thấy `model.delta`/`model.responded` |
| `model.failed` | `{ errorKind, message }` | Đóng thẻ C2 với `status: 'error'`. `errorKind = 'overloaded'` ⇒ **không được tự thử lại** |
| `tool.decided` | `{ callId, toolName, decision, reason }` | Mở thẻ tool (**C5**–**C8**, **C14**, **C15**) ở trạng thái đang chạy |
| `tool.executed` | `{ result: { callId, toolName, content, isError, evidence[] } }` | Cập nhật đúng thẻ đã mở theo `callId`, nạp `evidence` cho chỉ mục `[n]` |
| `client.requested` | `{ callId, toolName, argumentsJson }` | Ủy quyền cho Angular Host theo §4; **phải** trả kết quả cho `callId` đó |
| `approval.requested` | `{ approvalId, callId, toolName, riskClass, argumentsHash, expiresAt }` | Thẻ **C4**, dừng chờ người dùng bấm |
| `approval.resolved` | `{ approvalId, outcome, bindingValid }` | Cập nhật C4. `bindingValid === false` ⇒ `status: 'error'`, "tham số đã đổi sau khi duyệt" |
| `context.compacted` · `context.pruned` | `{ tokensBefore, tokensAfter }` | Thẻ **C11** dải mỏng |
| **`ui.widget`** | `{ widgetId, widgetKind, op, title, state, source, callId }` | **Không qua sổ thẻ.** Tra sổ `widgetKind → component`; `op: upsert` thay **toàn bộ** `state`; loại lạ render JSON thu gọn |
| `run.stateChanged` | `{ from, to, reason }` | Cập nhật trạng thái run; sinh thẻ **C13** khi `to` là `WaitingClient` / `WaitingApproval` |
| `run.completed` | `{ finalText, usage, iterations }` | Đóng lượt, gắn `usage`. `finalText` **không** sinh thẻ mới — nó trùng nội dung C2 cuối |
| `run.cancelled` | `{ reason, message }` | Đóng lượt `aborted`; mọi thẻ đang chạy chuyển `aborted` |
| `run.failed` · `run.escalated` | `{ reason, message }` | Đóng lượt `error`; mọi thẻ đang chạy chuyển `error` |
| `run` | `AgentRunDto` (**PascalCase**) | **Luôn là sự kiện cuối** của một stream thành công. Dùng đối chiếu `State` và `FinalText` |
| `error` | `{ code, description }` | Đóng lượt `error`, hiện `code` để tra cứu |
| *(bất kỳ `$kind` nào khác)* | — | **Bỏ qua, ghi `debug`, không lỗi** — `[INV-ASSISTANT-10]` |

> [!IMPORTANT]
> **Hai quy ước JSON trong cùng một luồng.** Sự kiện là hợp đồng của kernel: **camelCase**, có `$kind`, `seq`, `eventId`. Hai frame cuối `run` / `error` là DTO của LV_Shell: **PascalCase** (`RunId`, `State`, `FinalText`), và trường `null` bị lược khỏi JSON. Viết bộ đọc giả định một quy ước duy nhất là hỏng đúng ở frame cuối — tức đúng lúc câu trả lời vừa xong và khó nghi ngờ nhất.

### 5.3 Bộ Đọc Luồng — Port Nguyên Trạng, Không Tự Viết Lại

> [!CAUTION]
> **Không tự viết bộ tách khung SSE.** Chốt tại [`QĐ-ASSISTANT-017`](03-decisions.md). Gói tham chiếu đã có `createSseFrameParser()` — một bộ tách `text/event-stream` chuẩn W3C đã chạy thật. Một bản tự viết bằng phép tìm `

` thô sơ **hỏng im lặng** ở ca ký tự CR đứng cuối chunk mạng, và chỉ lộ ra dưới tải thật.
>
> Căn cứ Mã nguồn: `.reference/workbench-ide/resources/plugins/workbench.assistant/frontend/src/bridge/assistant-sse.bridge.ts#L62-L169`

#### 5.3.1 Hai tệp, hai vai — cùng đến từ một tệp nguồn

| Tệp đích | Hạng port | Vai |
|---|:--:|---|
| `sdk/headless/sse-frame-parser.ts` | **A** — nguyên trạng | Tách khung. TypeScript thuần, 0 phụ thuộc, kiểm trên Node |
| `bridge/netclaw-sse.bridge.ts` | **B** — nguyên trạng + trừ | Vòng đời luồng: `fetch`, `AbortController`, `reader`, phát khung tới người nghe |

#### 5.3.2 Hợp đồng bộ tách khung (port hạng A)

```typescript
// React_Assistant/src/sdk/headless/sse-frame-parser.ts

/** Một khung đã tách xong — `event` mặc định là `message` đúng đặc tả W3C. */
export interface SseFrame {
  /** Mốc phát lại tại thời điểm phát khung. Rỗng khi máy chủ chưa gửi `id:` lần nào. */
  readonly id: string;
  readonly event: string;
  readonly data: string;
}

export interface SseFrameParser {
  /** Nạp thêm một mẩu văn bản và lấy ra mọi khung đã hoàn chỉnh trong đó. */
  push(chunk: string): SseFrame[];
  /** Nhịp chờ máy chủ đề nghị qua `retry:`; `null` khi chưa từng được gửi. */
  readonly retryMs: number | null;
  /** Mốc phát lại gần nhất — bền qua các khung không mang `id:`. */
  readonly lastEventId: string;
}

export function createSseFrameParser(): SseFrameParser;
```

**Sáu luật bộ tách đã xử đúng — port về là có ngay, tự viết là phải tự nghĩ ra đủ sáu:**

| # | Luật | Không có thì hỏng thế nào |
|:-:|---|---|
| 1 | Chỉ nhả một dòng khi **đã thấy dấu kết dòng** của nó | Khung bị cắt giữa chunk ⇒ đọc nhầm nửa dòng |
| 2 | **Giữ lại ký tự CR đứng cuối bộ đệm** — nó có thể là nửa đầu cặp CRLF mà nửa sau ở chunk kế | Đẻ ra một dòng rỗng giả ⇒ **phát khung sớm giữa chừng dữ liệu**, mất phần đuôi |
| 3 | Bỏ qua dòng mở đầu `:` | Nhịp tim 15 giây thành khung rác; `JSON.parse` ném đều đặn |
| 4 | Gom `data:` nhiều dòng rồi cắt đúng một `
` cuối | Câu trả lời nhiều dòng bị nối sai hoặc thừa xuống dòng |
| 5 | Chốt `lastEventId` **ngay lúc đọc dòng `id:`**, kể cả khung không sinh sự kiện | Mốc replay lệch ⇒ `events?after=` bỏ sót hoặc lặp sự kiện |
| 6 | Bỏ cả dòng `id:` nếu giá trị chứa ký tự NUL | Header `Last-Event-ID` của lượt bám lại hỏng |

#### 5.3.3 Vòng đời luồng (port hạng B)

Giữ nguyên bộ khung `#openStream` / `#pump` / `#dispatch` của bản gốc; chỉ **trừ** các phương thức mặt phẳng điều khiển của IDE và **đổi** bảng `switch` trong `#dispatch`:

```typescript
// React_Assistant/src/bridge/netclaw-sse.bridge.ts

export class NetClawSseBridge {
  /** Gốc HTTP + token đến từ handshake. KHÔNG hardcode, KHÔNG đọc kho lưu trữ. */
  constructor(private readonly deps: { apiBaseUrl: string; getAccessToken(): string });

  /**
   * Mở một luồng và phát từng `RunEvent` tới người nghe. Trả hàm hủy.
   *
   * MỘT hàm phát dùng chung cho cả luồng trực tiếp lẫn replay — hai đường xử lý
   * khác nhau sẽ dựng ra hai giao diện khác nhau cho cùng một lượt chạy, và sai
   * lệch ấy chỉ lộ ra sau khi người dùng bấm F5.
   */
  openStream(path: string, body: unknown, onEvent: (e: RunEvent) => void): () => void;

  /** Mốc `seq` cuối đã nhận của một run — đầu vào của `GET runs/{id}/events?after=`. */
  lastSeqOf(runId: string): number;
}
```

**Năm nếp của bản gốc phải giữ nguyên khi port:**

| # | Nếp | Vì sao |
|:-:|---|---|
| 1 | Sổ `AbortController` theo từng run, hủy là `controller.abort()` | `host:auth-revoked` phải cắt được **mọi** luồng đang mở trong một nhịp |
| 2 | **Hủy không phải lỗi** — `isAbortError()` ⇒ không gọi `onError` | Người dùng bấm Dừng mà hiện thẻ lỗi đỏ là báo động giả |
| 3 | `reader.cancel()` trong `finally` | Trả socket về trình duyệt ngay thay vì đợi GC; trình duyệt giới hạn 6 kết nối mỗi domain |
| 4 | Khung hỏng ⇒ báo một lỗi khung, **đọc tiếp khung sau** | Một byte lỗi không được làm mất trọn phần còn lại của câu trả lời |
| 5 | `!response.ok` ⇒ đọc thân lỗi rồi phát `onError`, không ném | Mã lỗi `x-error-code` phải tới được thẻ để người dùng đọc |

**Ba điểm phải đổi:**

1. `switch (frame.event)` trong `#dispatch` đổi sang `$kind` của NetClaw — bảng đủ 20 dòng tại [`modules/02 §4.2`](modules/02-conversation-node-registry.md).
2. Danh sách endpoint đổi sang §5.1; **trừ** mọi phương thức MCP, worktree, skill, subagent, schedule, OCR của IDE.
3. Bỏ `Last-Event-ID` làm cơ chế nối lại — NetClaw **không** nối lại luồng cũ. `lastEventId` vẫn giữ, nhưng dùng làm `after=` cho `GET runs/{id}/events`.

#### 5.3.4 Facade hook — bề mặt mà khung chat và plugin nhìn thấy

```typescript
// React_Assistant/src/store/use-assistant-run.ts
// Không fetch, không token, không URL. Dữ liệu đã đi qua phép chiếu ba tầng của modules/02.

export function useAssistantRun(): {
  readonly state: 'idle' | 'streaming' | 'waitingClient' | 'waitingApproval' | 'completed' | 'failed';
  readonly turns: readonly TurnGroup[];
  readonly widgets: ReadonlyMap<string, WidgetEntry>;
  readonly send: (message: string) => void;
  readonly cancel: () => void;
  readonly decideApproval: (approvalId: string, approve: boolean, comment?: string) => void;
};
```

---

## 6. Cơ Chế Vòng Lặp Tác Vụ Phối Hợp (Backend ReAct Coordination & Human-in-the-Loop)

Toàn bộ logic chu trình ReAct (Reason ➔ Act ➔ Observe ➔ Repeat) được quản trị 100% tại `LV.NetClaw` trên backend .NET 10. UI Plugin đóng vai trò là giao diện tương tác và cầu nối thực thi.

```
                    ┌────────────────────────────────────────┐
                    │    Yêu cầu phức tạp của Người dùng    │
                    └───────────────────┬────────────────────┘
                                        │
                                        ▼
               ┌──────────────────────────────────────────────────┐
               │    BƯỚC 1: SUY LUẬN TẠI NETCLAW BACKEND (.NET)   │
               │  Phân tích mục tiêu, RAG ngữ cảnh & tool của mình│
               └────────────────────────┬─────────────────────────┘
                                        │
                       Cần gọi Tool hay Trả lời ngay?
                                        │
                        ┌───────────────┴───────────────┐
                        ▼                               ▼
                   [Trả lời]                       [Gọi Tool]
                        │                               │
                        │                               ▼
                        │              ┌──────────────────────────────────┐
                        │              │ BƯỚC 2: HÀNH ĐỘNG (SSE Event)    │
                        │              │ Phát client.requested            │
                        │              └────────────────┬─────────────────┘
                        │                               │
                        │                               ▼
                        │              ┌──────────────────────────────────┐
                        │              │ BƯỚC 3: THỰC THI & QUAN SÁT      │
                        │              │ Angular chạy tool & gửi kết quả  │
                        │              └────────────────┬─────────────────┘
                        │                               │
                        │                               ▼
                        │              Mục tiêu đã hoàn thành chưa?
                        │                               │
                        │                     ┌─────────┴─────────┐
                        │                     ▼ Chưa              ▼ Đã xong
                        │           Quay lại BƯỚC 1           BƯỚC CUỐI:
                        │           (Vòng lặp tiếp theo)      Trả lời tổng kết
                        │                                         │
                        └───────────────────► ◄───────────────────┘
                                              │
                                              ▼
                             [Stream model.delta vào C2 Card]
```

### 6.1 Máy Trạng Thái Của Phiên Run (Run State Machine)
```
[IDLE] ──(Bấm gửi)──► [SUBMITTING] ──(Nhận luồng)──► [STREAMING]
                                                           │
                     ┌─────────────────────────────────────┴─────────────────────────────────────┐
                     ▼                                                                           ▼
           [WAITING_APPROVAL]                                                             [WAITING_CLIENT]
    (Chờ người dùng bấm xác nhận C4)                                             (Chờ Angular MFE chạy xong tool)
                     │                                                                           │
                     └─────────────────────────────► [RESUMED] ◄─────────────────────────────────┘
                                                         │
                                                         ▼
                                                    [COMPLETED]
```

---

## 7. Kịch Bản Vận Hành Thực Tế 4 Bước (End-to-End Walkthrough)

**Kịch bản**: Người dùng đang xem văn bản tại `mfe-qlvb` và nhập yêu cầu:  
> *"Hãy lập hồ sơ trình ký văn bản này cho anh, chuyển sang lãnh đạo Nguyễn Văn A và mở hộp ký số."*

* **Bước 0 (Lập kế hoạch — `plan.write` ➔ `ui.widget`)**:
  1. `LV.NetClaw` thấy việc có từ ba bước trở lên nên gọi tool `plan.write`.
  2. NetClaw phát `ui.widget` `{ widgetId: 'plan', widgetKind: 'todo-list', op: 'upsert', state: { items: [...], done: 0, total: 3 } }`.
  3. Guest tra sổ `widgetKind` ➔ thẻ **C9** `LiveTaskChecklist`, xen vào dòng hội thoại tại vị trí `seq` của lần upsert này.
* **Bước 1 (Điều hướng — `ui.navigate`)**:
  1. NetClaw phát `client.requested` `{ callId: 'call-1', toolName: 'ui.navigate', argumentsJson: '{"route":"/tks/create?sourceDocId=DOC-2026-99"}' }`.
  2. `bridge/` phát `assistant:client-action` `{ callId, toolName, arguments }` sang Angular Host.
  3. `AssistantActionGateway` chạy bốn phép kiểm của §4.5: tool hợp lệ ➔ route có trong danh mục ➔ người dùng đủ quyền ➔ `Router.navigate('/tks/create')`, nạp chunk `mfe-tks`.
  4. Angular Host phát `assistant:client-action-result` `{ callId: 'call-1', content: 'Đã mở màn hình tạo hồ sơ trình ký', isError: false }`.
  5. Guest gửi `POST runs/{runId}/client-results/stream`; NetClaw rời trạng thái `WaitingClient`.
  6. NetClaw cập nhật kế hoạch: `ui.widget` upsert lần hai với `done: 1`. Thẻ C9 tích ô đầu — **không nhảy chỗ**, vì vị trí neo theo lần upsert đầu tiên.
* **Bước 2 (Mở biểu mẫu điền sẵn — `ui.open_form`)**:
  1. NetClaw phát `client.requested` `{ callId: 'call-2', toolName: 'ui.open_form', argumentsJson: '{"route":"/tks/create","prefill":{"title":"Tờ trình mua sắm máy chủ 2026","signers":"Nguyễn Văn A"}}' }`.
  2. Angular Host điều hướng (đã ở đúng route nên không tải lại) và gọi `formGroup.patchValue(prefill)`.
  3. Angular Host phát `assistant:client-action-result` `{ callId: 'call-2', content: 'Đã điền sẵn 2 trường trên form trình ký', isError: false }`.
  4. Guest gửi kết quả về NetClaw. Kế hoạch cập nhật `done: 2`.

  > **Không có `tks.fill_form`.** Việc điền form biểu diễn bằng `prefill` của `ui.open_form` — đó là toàn bộ danh mục client tool mà backend có ([`QĐ-ASSISTANT-009`](03-decisions.md)).

* **Bước 3 (Con người bấm nút cuối cùng)**:
  1. NetClaw phát `model.delta` rồi `model.responded`: *"Em đã mở hồ sơ trình ký và điền sẵn trích yếu cùng người ký. Anh/chị kiểm tra rồi bấm **Lưu** và **Ký số** giúp em ạ."*
  2. Kế hoạch cập nhật lần cuối: `done: 3`, thẻ C9 đủ ba ô tích.
  3. NetClaw phát `run.completed`, rồi frame cuối `event: run` (`AgentRunDto`, **PascalCase**). Ô soạn mở khóa.
  4. **Người dùng** bấm Lưu và Ký số trên giao diện Angular. AI không chạm nút đó — tôn chỉ 1 của [`README.md §1`](README.md).

* **Bước 3′ (Nhánh thay thế — khi tool ghi W2 đã được mở ở vòng sau)**:
  1. NetClaw nhận định thao tác ký số là hành động đột biến (Risk Class W2), phát `approval.requested` `{ approvalId: 'appr-99', callId: 'call-3', toolName: 'ui.open_form', riskClass: 'W2', argumentsHash: '…', expiresAt: '…' }`.
  2. Guest render thẻ **C4** `ToolApprovalCard` kèm tên tool, tham số hiển thị được và hạn duyệt.
  3. Người dùng bấm **[✓ Duyệt]** ➔ `POST approvals/appr-99/decide` `{ approve: true }` ➔ `POST runs/{runId}/resume/stream`.
  4. NetClaw so hash tham số lúc duyệt với lúc chạy. Khác nhau ⇒ `approval.resolved` `{ bindingValid: false }` và thẻ C4 chuyển `status: 'error'` với lý do *"tham số đã đổi sau khi duyệt"*.

  > **Vòng 1 chưa đi qua nhánh này**: tool ghi (W1/W2) chưa được mở, nên `approval.requested` chưa được phát trên thực tế. Giao diện vẫn phải hiện thực đúng, và **không** được chặn nghiệm thu vì "chưa thấy thẻ duyệt nào".

### 7.1 Nhánh Từ Chối — Điều Bắt Buộc Phải Chạy Đúng

Người dùng yêu cầu một việc ngoài danh mục, hoặc bị Prompt Injection qua nội dung một văn bản đính kèm:

1. NetClaw phát `client.requested` `{ callId: 'call-9', toolName: 'ui.navigate', argumentsJson: '{"route":"/admin/users/delete-all"}' }`.
2. `AssistantActionGateway` kiểm bước 2 của §4.5: route không có trong `AssistantActionCatalog` ⇒ **Fail-Closed**.
3. Angular Host phát `assistant:client-action-result` `{ callId: 'call-9', isError: true, content: "Từ chối: route '/admin/users/delete-all' không nằm trong danh mục hành động hợp lệ của màn hình hiện tại." }`.
4. Guest gửi nguyên văn lý do đó về NetClaw qua `client-results/stream`.
5. NetClaw đọc lý do và trả lời người dùng: *"Em không mở được màn hình đó vì nó không nằm trong danh mục em được phép thao tác."*

**Ba điều bài kiểm phải xác nhận ở nhánh này**: `callId` vẫn nhận **đúng một** kết quả; Router **không** bị chạm; và lý do từ chối **đọc được**, vì nó trở thành câu trả lời cho người dùng.
