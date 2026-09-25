---
type: verification
stage: 06
title: "Plugin Trợ Lý AI — Ma Trận Kiểm Thử & Nhật Ký Cạm Bẫy Triển Khai"
id: "FSP-PLUGIN-ASSISTANT-06"
status: draft
tags: [verification, testing, dod, plugin-assistant, assistant, react, fsp, stage-06, okf]
---

# Plugin Trợ Lý AI — Ma Trận Kiểm Thử & Nhật Ký Cạm Bẫy Triển Khai

> **Định dạng tệp**: `specs/plugin-assistant/06-verification.md` (Metadata ID: `FSP-PLUGIN-ASSISTANT-06`)
> **Loại tài liệu**: `verification`
> **Trạng thái**: `draft`
> **Chặng 6**: Hai phần tách bạch — **(a)** ma trận kiểm thử và tiêu chí nghiệm thu, xác định **trước** khi viết mã; **(b)** nhật ký cạm bẫy triển khai thực tế, ghi **sau** khi thi công thật.
> **Kế hoạch**: [`04-plan.md`](04-plan.md) · **Đặc tả**: [`05-spec.md`](05-spec.md) · **Sổ quyết định**: [`03-decisions.md`](03-decisions.md)

---

## PHẦN (A) — MA TRẬN KIỂM THỬ & TIÊU CHÍ NGHIỆM THU

### 1. Bốn Tầng Kiểm Thử & Ranh Giới Giữa Chúng

| Tầng | Chạy ở đâu | Phủ cái gì | Vì sao đặt ở tầng này |
|---|---|---|---|
| **T1 — Headless** | Vitest trên Node | `sdk/headless/`, `store/projection/`, luật đặt tên đóng góp | 0% React, 0% DOM ⇒ chạy mili-giây, không giòn. Đây là nơi **luật hiển thị** được kiểm, không phải ở trình duyệt |
| **T2 — Component** | Vitest + jsdom | 16 thẻ, ô soạn, sổ khe, `SlotBoundary` | Cần cây React nhưng không cần backend |
| **T3 — Tích hợp biên** | Vitest + máy chủ SSE giả | `bridge/`, vòng đời mount ⇄ dispose, hủy luồng | Cần một luồng thật để kiểm ca đứt nối và hủy |
| **T4 — Đầu-cuối** | Playwright trên Angular Shell thật | Handshake, `assistant:client-action`, chốt chặn của Host | Chỉ ở đây mới có Shadow Root thật và Router thật |

> [!IMPORTANT]
> **Luật đặt tầng**: một ca kiểm được ở tầng thấp hơn thì **cấm** đẩy lên tầng cao hơn. Kiểm phép neo cuộn bằng Playwright thay vì bằng số học thuần là đổi một bài kiểm mili-giây lấy một bài kiểm chục giây và giòn — và jsdom trả `scrollHeight`/`clientHeight` bằng 0 nên tầng T2 cũng không kiểm được nó.

### 2. Ma Trận Kiểm Thử Theo Bất Biến

#### 2.1 Bất biến nghiệp vụ `[INV-ASSISTANT-*]`

| Mã | Ca kiểm | Tầng | Đạt khi |
|---|---|:-:|---|
| `01` · `02` | Model đề xuất route ngoài danh mục ⇒ Host từ chối | T4 | Router **không** đổi; `client-results` mang `isError: true` kèm lý do đọc được; agent nói lại lý do đó |
| `03` | Người dùng mất quyền giữa phiên rồi AI xin điều hướng | T4 | Từ chối tại bước kiểm quyền, **không** phải tại bước đăng ký |
| `04` | Một `callId` nhận **đúng một** kết quả | T3 | Phát hai `assistant:client-action-result` cùng `callId` ⇒ chỉ một lượt `POST client-results` |
| `04` | Angular Host im lặng | T3 | Sau 30 giây ⇒ tự trả `isError: true`; run **không** treo ở `WaitingClient` |
| `05` | `approval.requested` giả ⇒ thẻ C4 | T2 | Hiện tên tool, tham số, hạn `expiresAt`, hai nút |
| `05` | `bindingValid: false` | T2 | Thẻ C4 chuyển `error`, nêu "tham số đã đổi sau khi duyệt" |
| `06` | Nhận `host:auth-revoked` | T3 | 0 luồng còn mở, 0 token trong bộ nhớ, hội thoại bị xóa, `disposeAll()` đã chạy |
| `07` | Quét mã nguồn | T1 | `grep -rn "api.openai\|anthropic\|generativelanguage" src/` rỗng |
| `08` | Thêm một plugin giả lập | T2 | `git diff --stat` cho thấy đúng **1** dòng sửa ngoài thư mục plugin mới |
| `09` | Gửi `PageContext` có `formSummary` lồng | T1 | `flattenContext()` trả `Record<string,string>` phẳng; `null` bị bỏ khóa; `selection` cắt ở 2.000 ký tự |
| `10` | Chuỗi sự kiện có 5 `$kind` bịa | T1 | 0 ngoại lệ; 0 nút sinh ra cho 5 sự kiện đó; các sự kiện hợp lệ vẫn chiếu đúng |
| `10` | `ui.widget` với `widgetKind` lạ | T2 | Render JSON thu gọn gập sẵn, không ném, không để trống chỗ |
| `11` | Quét thư mục plugin | T1 | Bảy lệnh `grep` của [`modules/01 §6.3`](modules/01-plugin-contract.md) đều rỗng |
| `12` · `13` | Quét toàn repo | T1 | `grep -rn "\.reference" src/ package.json tsconfig.json` rỗng; `grep -rn "@wb/" src/` rỗng |

#### 2.2 Bộ tách khung SSE — bốn ca đã trả giá để biết

> Bốn ca này là lý do `createSseFrameParser()` được port nguyên trạng thay vì viết lại ([`QĐ-ASSISTANT-017`](03-decisions.md), sai lệch **V6**). Cả bốn hỏng **im lặng** — không ngoại lệ, không log, chỉ dữ liệu sai.

| # | Ca | Đầu vào (chia chunk cố ý) | Đạt khi |
|:-:|---|---|---|
| 1 | **CR đứng cuối bộ đệm** | Chunk 1 kết thúc bằng `...data: xin ch\r`, chunk 2 mở đầu `\ndata: ào\n\n` | Ra **một** khung `data: "xin chào"`, không ra khung rỗng giữa chừng |
| 2 | **`data:` nhiều dòng** | `data: dòng 1\ndata: dòng 2\n\n` | `frame.data === "dòng 1\ndòng 2"` — đúng một `\n`, không thừa ở cuối |
| 3 | **`id:` ở khung không sinh sự kiện** | `id: 42\n\n` rồi `data: {}\n\n` | `lastEventId === "42"` sau khung đầu; khung đầu **không** sinh sự kiện |
| 4 | **`id:` chứa NUL** | `id: 4\u00002\n` | Bỏ **cả dòng** `id:`; `lastEventId` giữ giá trị trước đó |
| 5 | **Dòng nhịp tim** | `: heartbeat 2026-09-21T08:00:00Z\n\n` | 0 khung sinh ra, 0 ngoại lệ |
| 6 | **Khung chia ba chunk** | Một khung JSON 3 KB cắt làm ba | Ra đúng một khung, `data` nguyên vẹn |

#### 2.3 Phép chiếu ba tầng

| Ca | Tầng | Đạt khi |
|---|:-:|---|
| Chuỗi mẫu [`modules/02 §5.1`](modules/02-conversation-node-registry.md) | T1 | Ra đúng cây [`§5.2`](modules/02-conversation-node-registry.md): 1 lượt, 3 bước, `answer` là nút C2 cuối |
| `tool.executed` không có `tool.decided` trước | T1 | Mở nút mới đã hoàn tất, không mất thẻ |
| Hai `tool.executed` cùng `callId` | T1 | Lần sau ghi đè lần trước, **không** đẻ thẻ trùng |
| `model.delta` tới **sau** `model.responded` cùng bước | T1 | Bỏ qua — nút đã đóng, không "mọc đuôi" sau câu trả lời |
| Dãy 5 nút tra cứu liền nhau, `status: ok` | T1 | Nén thành 1 nút C16; `replacedNodeIds` giữ đủ 5 `id` |
| Dãy 2 nút tra cứu | T1 | **Không** nén |
| Dãy 3 nút, nút giữa `status: error` | T1 | **Không** nén — lỗi phải nhìn thấy ngay |
| `ui.widget` upsert ba lần cùng `widgetId` | T1 | Vị trí neo theo lần **đầu tiên**; widget không nhảy xuống cuối |
| Chiếu 500 sự kiện | T1 | ≤ **16 ms** (bench) |
| SSE trực tiếp và replay cùng dữ liệu | T1 | Hai đường vào cho ra **cùng một** cây lượt, so bằng deep-equal |

#### 2.4 Hệ khe cắm

| Ca | Tầng | Đạt khi |
|---|:-:|---|
| Plugin ném trong `activate()` | T2 | Các plugin còn lại vẫn kích hoạt đủ; ba sổ của plugin hỏng đã được gỡ; log nêu `id` + `version` |
| `targetViewId` trỏ view không tồn tại | T2 | Ném ngay lúc đăng ký, nêu tên plugin và tên view |
| Hai plugin cùng `widgetKind` có tiền tố | T2 | Ném `DuplicateContributionError`, nêu **cả hai** chủ sở hữu |
| Plugin không phải `assistant` chiếm `todo-list` | T2 | Ném — tên lõi không tiền tố chỉ `assistant` được đăng ký |
| `nodeType` đóng góp thiếu tiền tố | T1 | Ném, thông điệp nêu đúng khuôn `<plugin-id>:<tên>` |
| Lệnh đóng góp trùng lệnh dựng sẵn (`/clear`) | T1 | Ném — lệnh dựng sẵn không nhường tên |
| `available: false` mà thiếu `unavailableReason` | T1 | Ném — bảng gợi ý sẽ hiện dòng trống |
| `isEnabled()` trả `false` | T2 | **Không** chunk nào được tải (theo dõi `import()`) |
| Gỡ plugin | T2 | Disposer chạy **ngược** thứ tự đăng ký; 16 thẻ dựng sẵn **không** bị chạm |
| Thu hồi tới muộn sau khi tên đã sang chủ khác | T1 | **Không** cuỗm mất đăng ký của người kế nhiệm |
| Một thẻ ném khi render | T2 | `CardBoundary` chặn; phần còn lại của hội thoại vẫn cuộn và stream |

#### 2.5 Vòng đời & ngân sách

| Ca | Tầng | Đạt khi |
|---|:-:|---|
| Mount ⇄ dispose 10 lượt | T3 | 0 listener, 0 stream, 0 timer còn lại |
| Bấm Dừng giữa lượt stream | T3 | **Không** hiện thẻ lỗi — hủy không phải lỗi; socket đóng ngay |
| Rút mạng giữa lượt | T3 | `GET runs/{id}` + `events?after={seq}` dựng lại đủ; `model.queued` **không** quay lại |
| `!response.ok` | T3 | `onError` mang mã `x-error-code`; không ném ra ngoài |
| Khung JSON hỏng giữa luồng | T3 | Báo một lỗi khung, **đọc tiếp** khung sau |
| Đo bundle | T1 | Bundle khởi động ≤ **100 KB** gzip |
| Đo thời gian mount | T4 | `mountFlavor()` ➔ khung chat hiện ≤ **300 ms** |

#### 2.6 Trợ năng & giao diện

| Ca | Tầng | Đạt khi |
|---|:-:|---|
| Mở modal rồi bấm `Tab` liên tục | T2 | Focus không thoát khỏi modal (bẫy focus) |
| Bấm `Escape` trong modal | T4 | Modal đóng; bộ nghe gắn ở **Shadow Root**, không ở `document` |
| Mở modal | T4 | Guest phát `assistant:request-scroll-lock`; Guest **không** chạm `document.body.style` |
| `prefers-reduced-motion: reduce` | T2 | Tắt hiệu ứng gõ chữ và trượt ngăn kéo |
| Ở 400px chiều ngang | T4 | Ngăn kéo không tràn; bảng gợi ý không lọt ra ngoài viewport |
| Chế độ tối của Host | T4 | Token kế thừa xuyên Shadow; không mã màu cứng nào lộ ra |

### 3. Tiêu Chí Nghiệm Thu Theo Pha

| Pha | Cổng ra | Lệnh kiểm |
|:-:|---|---|
| **1** | Tầng chiếu và biên xanh | `npm run test -- store/projection sdk/headless bridge` |
| **2** | Khung chat nhìn được, bundle trong ngân sách | `npm run test` + `npm run build` rồi đọc báo cáo gzip |
| **3** | Thêm plugin sửa đúng 1 dòng | Kịch bản [`modules/01 §5.3`](modules/01-plugin-contract.md) + `git diff --stat` |
| **4** | Tám benchmark đạt | [`README.md §8`](README.md) |

### 4. Những Gì KHÔNG Kiểm Ở Feature Này

* **Chất lượng câu trả lời của model** — thuộc `LV.NetClaw`. Giao diện kiểm *chiếu đúng sự kiện*, không kiểm *model trả lời hay*.
* **Danh mục route của `AssistantActionCatalog`** — thuộc `Angular_Workspace/`; ở đây chỉ kiểm rằng từ chối được truyền đúng về agent.
* **Hiệu năng backend, hạn mức token, hàng đợi GPU** — thuộc backend.
* **Giá trị token giao diện** — thuộc [`multi-flavor/modules/02`](../multi-flavor-architecture/modules/02-ui-token-contract.md).

---

## PHẦN (B) — NHẬT KÝ CẠM BẪY TRIỂN KHAI THỰC TẾ

> [!IMPORTANT]
> **Phần này ghi SAU khi thi công thật**, mỗi dòng gồm ba cột: triệu chứng đã xảy ra ➔ vì sao nó lọt qua lint/typecheck/test ➔ cách kiểm để lần sau bắt được. Bàn giao feature mà mục này rỗng trong khi quá trình triển khai có sửa lỗi phát sinh là **vi phạm quy chuẩn**.

### 5. Cạm Bẫy Ghi Nhận Trong Giai Đoạn Đặc Tả

Ba mục dưới đây xảy ra ở **chặng đặc tả**, trước khi có dòng mã nào. Chúng được ghi vào đây vì cùng một cơ chế sẽ tái diễn ở chặng thi công nếu không ai biết.

| # | Triệu chứng đã xảy ra | Vì sao lọt qua | Cách kiểm để lần sau bắt được |
|:-:|---|---|---|
| **B1** | Đặc tả một bộ đọc SSE tự viết bằng phép tìm dấu ngắt khung thô sơ, bỏ sót bốn ca mà bản trong kho tham chiếu đã xử đúng — nặng nhất là ca **CR đứng cuối chunk** làm mất phần đuôi câu trả lời | Không cổng nào kiểm được **văn bản đặc tả**. Nguyên nhân gốc là một phản xạ: thấy tệp nguồn dài 1.388 dòng thì mặc định "viết mới cho gọn", mà không mở ra đọc | Trước khi xếp một tệp vào hạng C, **bắt buộc mở tệp nguồn và liệt kê những gì nó đã xử lý**. Ba điều kiện của [`modules/03 §2.3`](modules/03-workbench-assistant-port-map.md) phải trả lời được bằng dẫn chứng dải dòng, không bằng cảm tính |
| **B2** | `05-spec.md` khai `PageContext.formSummary` là object lồng, trong khi backend nhận `Dictionary<string,string>` phẳng | Tài liệu đặc tả không chạy, nên không có bước nào đối chiếu nó với hợp đồng backend. Lỗi này nếu lọt tới thi công sẽ hỏng **im lặng**: trường lồng bị bỏ, không có lỗi nào | Mọi hợp đồng dữ liệu đi qua dây phải trích dẫn đúng mục của [`AGENT_CHAT_API.md`](../../LV_Shell/src/NetClaw/docs/host-lv-shell/AGENT_CHAT_API.md). Ở tầng mã: một bài kiểm T1 khẳng định `flattenContext()` trả về `Record<string,string>` |
| **B3** | Sổ thẻ hội thoại đặt ra sáu tên linh kiện không có mã nguồn nào để port (`ErrorCard`, `ClientActionCard`, `ArtifactCard`…) | Tên nghe hợp lý nên không ai nghi ngờ. Hệ quả: lượt thi công đầu tiên sẽ phải tự viết sáu thẻ trong khi kho tham chiếu có sẵn 16 thẻ đã chạy | Mỗi mục trong sổ thẻ **bắt buộc** có cột "Nguồn port" trỏ tới một tệp thật. Không có nguồn thì phải biện minh, như ca "không có thẻ lỗi riêng" ở [`modules/02 §3.1`](modules/02-conversation-node-registry.md) |

### 6. Cạm Bẫy Ghi Nhận Trong Giai Đoạn Thi Công

*(Điền trong quá trình thi công. Giữ đúng ba cột: triệu chứng ➔ vì sao lọt qua ➔ cách kiểm.)*

| # | Triệu chứng đã xảy ra | Vì sao lọt qua | Cách kiểm để lần sau bắt được |
|:-:|---|---|---|
| — | *(chưa có — feature chưa vào thi công)* | | |

### 7. Ca Biên Dự Đoán Trước, Cần Xác Nhận Khi Thi Công

Bảy ca dưới đây được nhận diện từ mã tham chiếu và hợp đồng backend. Chúng **chưa** là cạm bẫy đã xảy ra; khi thi công chạm tới, chuyển kết quả thật xuống §6.

| # | Ca | Vì sao nghi ngờ |
|:-:|---|---|
| **1** | Nhịp tim 15 giây so với `ActivityTimeout` 100 giây của YARP và `requestTimeout` của IIS | Ba mốc thời gian ở ba tầng hạ tầng khác nhau; lệch một mốc là luồng đứt giữa chừng mà log server vẫn sạch |
| **2** | `exactOptionalPropertyTypes` của TypeScript strict | Mã tham chiếu phân biệt "không truyền prop" với "truyền `undefined`". Port mà bỏ phân biệt này thì typecheck đỏ hàng loạt ở nơi không liên quan |
| **3** | `createPortal` trong Shadow Root | Bốn linh kiện port về đều mặc định `document.body`; sót một cái là một overlay mất sạch CSS |
| **4** | Tailwind preflight rò ra `<head>` | Rò ra là **reset toàn bộ giao diện Angular**, không phải một lỗi cục bộ |
| **5** | Hai quy ước JSON trong cùng một luồng | Bộ đọc giả định một quy ước sẽ hỏng đúng ở frame cuối `run` — tức đúng lúc câu trả lời vừa xong và khó nghi ngờ nhất |
| **6** | Sáu kết nối mỗi domain của trình duyệt | Luồng chat ngắn hạn cộng kênh SSE nền tảng của Shell; quên `reader.cancel()` là cạn khe kết nối sau vài lượt |
| **7** | `keepAlive` của `IMainView` | Giữ cây React sống nghĩa là giữ cả timer và bộ nghe của view đó; một view `keepAlive` rò rỉ sẽ không lộ ra ở bài kiểm mount ⇄ dispose thông thường |
