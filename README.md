# HedgeDoc — Modular Document AI Application

Phân hệ ứng dụng tích hợp (Application Integration Layer) kết nối 3 khối trí tuệ nhân tạo tài liệu độc lập:
1. **Document Quality Gate**: Đo lường vật lý độ mờ, độ tương phản, độ phân giải, bóng đổ và ra quyết định phân luồng.
2. **Document OCR Engine**: Trích xuất cấu trúc văn bản kỹ thuật số nguyên bản và OCR hình ảnh qua mô hình thị giác ngôn ngữ.
3. **Document RAG Engine**: Phân đoạn nhận biết cấu trúc cha con, tìm kiếm lai (véc-tơ + từ khóa + RRF) và sinh câu trả lời có trích dẫn trang.

---

## 1. Cấu trúc thư mục

```text
HedgeDoc/
├── frontend/
│   ├── app.py                     # Ứng dụng giao diện Streamlit chính
│   ├── components.py              # Thẻ điểm chất lượng, xem cấu trúc OCR, suy luận, trích dẫn
│   └── styles.css                 # Giao diện tùy biến trực quan
├── services/
│   ├── __init__.py
│   ├── engine_loader.py           # Nạp mô-đun độc lập trong không gian tên biệt lập
│   ├── quality_gate_client.py     # Bộ điều hợp kết nối Quality Gate
│   ├── ocr_client.py              # Bộ điều hợp kết nối OCR Engine
│   └── rag_client.py              # Bộ điều hợp kết nối RAG Engine
├── workflows/
│   ├── __init__.py
│   └── document_pipeline.py       # Bộ điều phối luồng tích hợp hoàn chỉnh
├── configs/
│   └── app_config.py              # Nạp biến môi trường và thiết lập cấu hình
├── tests/
│   ├── __init__.py
│   ├── test_services.py           # Kiểm thử tự động 3 bộ điều hợp dịch vụ
│   └── test_orchestrator.py       # Kiểm thử tự động toàn bộ luồng tích hợp
├── run_app.py                     # Tệp khởi chạy nhanh ứng dụng
└── README.md
```

---

## 2. Quy trình xử lý tài liệu (Pipeline Workflow)

```text
[Tệp tải lên]
      │
      ▼
1. Document Quality Gate (Đo độ mờ, tương phản, DPI, bóng đổ)
      │
      ├──> [Bị từ chối] ──> Thông báo lý do & dừng quy trình
      │
      └──> [Đủ điều kiện / Cần tăng cường]
                  │
                  ▼
2. Document OCR Engine (Bóc tách kỹ thuật số hoặc mô hình thị giác ngôn ngữ)
                  │
                  ▼
          [Lược đồ chuẩn OCROutput]
                  │
                  ▼
3. Document RAG Engine (Phân đoạn cấu trúc cha con & lưu véc-tơ)
                  │
                  ▼
4. Giao diện trò chuyện (Tìm kiếm lai & tổng hợp câu trả lời có trích dẫn)
```

---

## 3. Hướng dẫn khởi chạy

### Chạy ứng dụng giao diện
```bash
python HedgeDoc/run_app.py
```
Hoặc:
```bash
streamlit run HedgeDoc/frontend/app.py
```

### Chạy kiểm thử tự động
```bash
pytest HedgeDoc/tests/ -v
```
