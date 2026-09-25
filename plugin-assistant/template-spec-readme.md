---
type: template
title: "Mẫu Tổng quan Đặc tả Tính năng (FSP Spec README)"
id: "TEMPLATE-SPEC-README"
status: template
tags: [template, feature-overview, intent-driven, fsp, okf]
---

# Feature: [Tên Feature] ([Vai trò cốt lõi])

Tệp đích `specs/<feature>/README.md`; luật phân vùng: [`specs/CLAUDE.md`](../../specs/CLAUDE.md). Mục không áp dụng thì bỏ, không để heading rỗng. Đây là tài liệu ý đồ (intent): tầm nhìn, tôn chỉ, nguyên lý, bất biến hệ thống; chi tiết kỹ thuật thuộc `05-spec.md`. Frontmatter:

```yaml
---
type: index
title: "Feature: [Tên Feature] ([Vai trò cốt lõi])"
id: "FSP-<FEATURE>-ROOT"
status: in_review
tags: [spec, <feature>, feature-overview, intent-driven, fsp, okf]
---
```

**Vị trí mã nguồn dự kiến**

| Layer | Đường dẫn | Trách nhiệm |
|---|---|---|
| Frontend | `apps/<framework>/src/.../<feature>/` | [...] |
| Backend | `apps/<backend>/...` | [...] |
| Shared | `packages/<pkg>/...` | [...] |

## 1. Tầm nhìn & định vị
- **Vấn đề thực tế**: [1..n bài toán, kèm số liệu/rủi ro]
- **Định vị giải pháp**: [một câu khẳng định giá trị cốt lõi]
- **Tôn chỉ thiết kế**: [1..n, ví dụ Air-Gapped First, Grounding over Fluency, Determinism]

## 2. Nguyên lý kiến trúc
- **[Nguyên lý]**: [...]
- **Fail-closed & fallback**: [hành xử khi thiếu dữ liệu / lỗi quyền; dự phòng; cảnh báo toàn vẹn]

## 3. Sơ đồ kiến trúc & quy trình
- [Mermaid phân tầng / flowchart / sequence — chỉ vẽ sơ đồ nào mang thông tin không diễn đạt được bằng bảng]

## 4. Danh mục công nghệ chốt
- **[Tầng]**: **[Công nghệ]** — [vai trò]; căn cứ khảo sát tại `01-research.md`

## 5. Đánh đổi kiến trúc

| Hạng mục | Chọn | Từ chối | Căn cứ |
|---|---|---|---|
| [...] | [...] | [...] | [...] |

## 6. Bất biến hệ thống
- Mã `[INV-<FEATURE>-NN]` định nghĩa một lần tại `05-spec.md` mục 1; ở đây chỉ trỏ link, không chép lại.

## 7. Non-goals & anti-patterns
- **Cố tình không làm**: [...]
- **Cấm**: [hành vi và lý do]

## 8. Miền kiểm chứng điển hình

| Miền | Thách thức | Thành quả |
|---|---|---|
| [...] | [...] | [...] |

## 9. Tham chiếu
- Tiến độ 6 chặng: `index.md` · `research/sources/` · `01-research.md` · `../CLAUDE.md`
