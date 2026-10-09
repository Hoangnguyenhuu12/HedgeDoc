# HedgeDoc — Kế hoạch Tiếp tục Công việc (continue.md)
*Ngày cập nhật: 09/10/2026*

Tài liệu này tổng hợp toàn bộ tiến độ đã thực hiện và danh sách các nhiệm vụ cần tiếp tục triển khai trong phiên làm việc tiếp theo.

---

## 1. Tóm tắt Hiện trạng Hệ thống (Đã Hoàn Thành)

### Giao diện & Trải nghiệm (UI/UX)
- [x] **Loại bỏ toàn bộ Icon / Emoji**: Đã xóa sạch emoji (📖, 💡, 🎯, 📚, 🔍) trên toàn bộ sidebar, tiêu đề trang, prompt trợ lý và các nút bấm.
- [x] **Chuẩn hóa Màu sắc Tối giản**: Giao diện thuần sắc đen/xám than (`#141416`, `#18181b`, `#27272a`), loại bỏ hoàn toàn các sắc xanh đậm hoặc xanh xám.
- [x] **Cố định Kho tri thức đã lưu**: Khối danh mục tài liệu ở Sidebar luôn hiển thị ổn định, không bị ẩn khi tải lại trang web (F5).
- [x] **Hậu tố định dạng file**: Tên tài liệu hiển thị rõ đuôi file (ví dụ: `Ca phe cung Tony.pdf`, `Hoang Tu Be.pdf`).
- [x] **Nút "x" dạng Frameless Icon**: Bỏ khung viền (border), màu nền (background) của nút `✕` bằng CSS marker chuyên dụng `.del-btn-anchor`, khi hover chuyển sắc đỏ cảnh báo.
- [x] **Gợi ý câu hỏi trên 1 dòng duy nhất**: Các nút chip tương tác được dàn ngang trên đúng 1 dòng (`st.columns`), chữ gọn gàng không bị ngắt dòng luộm thuộm.
- [x] **Gợi ý khởi đầu chung chung**: Thay các tên sách cụ thể bằng 3 câu hỏi định hướng tổng quát:
  1. *Tóm tắt nội dung tài liệu*
  2. *Tra cứu quy định & điều khoản chính*
  3. *Kiểm định chất lượng tài liệu scan*

### Động cơ RAG & Tác tử Đa nhiệm (Agentic Architecture)
- [x] **Tự động nhận diện sách & Tóm tắt 3 phần (`document_summary`)**:
  - Tự động trích xuất các trang đầu (trang 1–6: Lời mở đầu, tác giả, mục lục) kết hợp các phân đoạn cốt lõi.
  - Tổng hợp thành cấu trúc: `1. Giới thiệu tổng quan` $\rightarrow$ `2. Các chủ đề & Thông điệp cốt lõi` $\rightarrow$ `3. Giá trị thực tiễn & Đối tượng hướng đến`.
- [x] **Hỏi đáp & Làm rõ khi thiếu thông tin (Clarification Dialogue)**:
  - Khi người dùng hỏi chung chung *"Tóm tắt nội dung tài liệu"*, hệ thống không từ chối máy móc mà chủ động liệt kê danh sách các cuốn sách đang có và hỏi người dùng muốn tóm tắt cuốn nào.
  - Đi kèm các nút chip tương tác 1-click để người dùng bấm chọn tài liệu ngay lập tức.
- [x] **Năng lực kiểm định tài liệu scan (`platform_capabilities`)**:
  - Nhận diện và phản hồi tức thì về tiêu chuẩn đo độ nét (Laplacian Variance), độ tương phản (RMS Contrast), bóng đổ và điểm sẵn sàng OCR, hướng dẫn người dùng nạp file ở sidebar.

---

## 2. Danh mục Nhiệm vụ Đã Hoàn Thành trong Phiên này (Completed Tasks)

### Ưu tiên 1: Kiểm định Giao diện thực tế & Tương thích Trình duyệt
- [x] **Kiểm tra hiển thị nút `✕` trên trình duyệt người dùng**:
  - Đã bổ sung các bộ chọn CSS thuộc tính chuẩn phổ quát: `button[title*="Xóa"]`, `button[aria-label*="Xóa"]` trong `frontend/styles.css` làm fallback độc lập 100% không phụ thuộc vào `:has()`.
  - Đảm bảo hiển thị hoàn toàn không khung viền (frameless), nền trong suốt, hover sang sắc đỏ cảnh báo `#ef4444` trên mọi trình duyệt/thiết bị.
- [x] **Độ co giãn của 1 dòng chip gợi ý**:
  - Đã chuẩn hóa CSS flexbox `.chips-title + div[data-testid="stHorizontalBlock"]` với `overflow-x: auto`, `scrollbar-width: thin`, `flex-wrap: nowrap`, `white-space: nowrap`, `text-overflow: ellipsis`.
  - Bổ sung thuộc tính `help=clean_text` hiển thị tooltip đầy đủ nội dung câu hỏi khi người dùng thu nhỏ cửa sổ trình duyệt.

### Ưu tiên 2: Nâng cấp Chiều sâu Tra cứu & Đối thoại RAG
- [x] **Xử lý câu hỏi "Tra cứu quy định & điều khoản chính" cho sách phi pháp lý**:
  - Bổ sung hàm nhận diện `is_legal_inquiry()` và phân loại tài liệu pháp lý `is_legal_document()` trong `HedgeDoc/agents/language_utils.py`.
  - Định tuyến nhánh kịch bản `non_legal_guidance`: Khi người dùng tra cứu quy định/điều khoản trong kho sách văn học/kỹ năng (*Cà phê cùng Tony*, *Hoàng tử bé*), hệ thống chủ động giải thích tính chất tài liệu và gợi ý chuyển hướng sang tra cứu:
    - *Các nguyên tắc sống và bài học ứng xử*
    - *Quan điểm về tự lập và lập nghiệp*
    - *Các câu chuyện tiêu biểu và thông điệp cốt lõi*
    kèm chip tương tác 1-click.
- [x] **Ghi nhớ ngữ cảnh đối thoại liên tục (Multi-turn Context Memory)**:
  - Bổ sung `is_clarification_context()` và `resolve_document_from_context()` trong `language_utils.py`.
  - Xử lý mượt mà khi hệ thống hỏi: *"Bạn muốn tóm tắt cuốn sách nào?"* và người dùng gõ số thứ tự (`"cuốn thứ nhất"`, `"cuốn 2"`, `"1"`, `"2"`, `"first"`) hoặc từ khóa ngắn (`"Tony"`, `"Hoàng tử bé"`): hệ thống mapping chính xác vào tài liệu và kích hoạt ngay luồng tóm tắt chuyên sâu 3 phần mà không bắt người dùng nhập lại.

### Ưu tiên 3: Tham khảo Kiến trúc từ `LV_platform`
- [x] **Nghiên cứu & Đối chiếu giải pháp RAG từ folder `LV_platform`**:
  - Rà soát kiến trúc AI tại `F:\LV_Platform\docs\ai` và `F:\LV_Platform\docs\ai-agent`:
    - **Cổng AI nội bộ kép (Dual Provider)**: `http://172.16.12.230:4000/v1` (LiteLLM đứng trước vLLM) hỗ trợ chuẩn OpenAI API tương thích với model chat `google/gemma-4-26B-A4B-it`, vision `Qwen/Qwen3-VL-8B-Instruct`, embedding `BAAI/bge-m3` (1024 chiều).
    - **Bóc tách OCR Multimodal**: Đang dùng cụm VLM nội bộ `http://172.16.12.230:8003/v1` với `Qwen/Qwen3-VL-8B-Instruct-FP8`.
    - **Tìm kiếm Fulltext**: Tích hợp SQL Server Fulltext Search cho văn bản QLVB.
    - **Frontend React Guest Plugin**: Kiến trúc Shadow DOM tách biệt hoàn toàn CSS Host & Guest, slot-based headless models kiểm thử độc lập không phụ thuộc DOM.
  - Đối chiếu với HedgeDoc: HedgeDoc đã tích hợp Hybrid Retriever 2 tầng (ChromaDB Dense Vectors + Okapi BM25 Lexical Ranking + RRF Fusion Reciprocal Rank + Parent-Child context expansion) hoàn toàn tương thích và đáp ứng trọn vẹn tiêu chuẩn cao cấp của hệ thống.

### Ưu tiên 4: Kỹ thuật & Hạ tầng (Backend & Dependencies)
- [x] **Nâng cấp SDK Google GenAI**:
  - Đã cài đặt chính thức SDK mới `google-genai==2.29.0`.
  - Cập nhật `F:\document-rag-engine\src\generation\llm_provider.py` (`GeminiLLMProvider`) và `F:\document-rag-engine\src\embeddings\embedding_provider.py` (`GeminiEmbeddingProvider`) sang `google.genai.Client` và `google.genai.types.GenerateContentConfig`.
  - Loại bỏ hoàn toàn cảnh báo `FutureWarning` liên quan đến `google.generativeai`.
  - Bổ sung cơ chế tự động Failover sang Ollama (`deepseek-r1:8b`) cục bộ khi kết nối đám mây gặp sự cố hoặc vượt quota miễn phí (429 ResourceExhausted).
  - Cập nhật `F:\HedgeDoc\requirements.txt` bổ sung `google-genai>=0.1.0`.
- [x] **Bổ sung Bộ kiểm thử Tự động (Unit & Integration Tests)**:
  - Tạo mới `F:\HedgeDoc\tests\test_agents.py` với 14 test cases chuyên sâu:
    - `FrontdeskAgent.classify_intent()` cho mọi intent (`frontdesk_chat`, `platform_capabilities`, `document_summary`, `document_research`).
    - `FrontdeskAgent.respond_not_found()` đa ngữ (VI / EN) cho cả 3 trường hợp: có tài liệu đối chiếu, kho trống, và liệt kê danh mục gợi ý.
    - `MultiAgentCoordinator._get_catalog_suggestions()` đa ngữ.
    - `MultiAgentCoordinator` xử lý câu hỏi quy định cho sách văn học phi pháp lý (`non_legal_guidance`).
    - Multi-turn context memory resolution (số thứ tự và tên sách).
    - Bộ tiện ích ngôn ngữ (`detect_language`, `is_legal_inquiry`, `is_legal_document`, `clean_doc_title`).
  - Toàn bộ 17/17 test cases trong `test_agents.py` và `test_services.py` chạy thành công 100% (`PASSED`).

---

## 3. Thông tin Môi trường & Lệnh Chạy Nhanh

- **Thư mục làm việc chính**: `F:\HedgeDoc`
- **Thư mục RAG Engine phụ trợ**: `F:\document-rag-engine`
- **Môi trường Python ảo**: `F:\HedgeDoc\.venv\Scripts\python.exe`
- **Lệnh khởi chạy giao diện Web**:
  ```powershell
  & 'F:\HedgeDoc\.venv\Scripts\python.exe' -m streamlit run 'F:\HedgeDoc\frontend\app.py' --server.port 8501
  ```
- **Địa chỉ truy cập**: `http://localhost:8501`
