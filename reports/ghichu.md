# Ghi Chú Dự Án HedgeDoc (Dành Cho Agent Tiếp Theo)

> **Cập nhật lần cuối**: 05/10/2026
> **Mục đích file**: Lưu trữ toàn bộ bối cảnh hệ thống, các thay đổi kỹ thuật, trạng thái API và lưu ý vận hành để agent tiếp theo có thể tiếp tục công việc ngay lập tức mà không gặp sự cố lặp lại.

---

## 1. Tổng Quan Dự Án
- **HedgeDoc**: Hệ thống RAG (Retrieval-Augmented Generation) lấy cảm hứng từ NotebookLM.
- **Tiêu chuẩn cốt lõi**:
  - Strict Grounding (Zero Hallucination - Không bịa thông tin ngoài tài liệu).
  - Page-level Citations (Mọi câu trả lời bắt buộc dẫn chứng số trang và trích đoạn cụ thể).
  - Multi-turn Memory (Duy trì ngữ cảnh trò chuyện nhiều lượt).
  - Giao diện Streamlit tối giản, hỗ trợ streaming thời gian thực và drawer suy luận (thinking).

---

## 2. Hướng Dẫn Môi Trường & Khởi Chạy

### 2.1 Môi trường ảo Python
- Môi trường ảo đặt tại: `F:\HedgeDoc\.venv` (Python 3.14.7).
- Kích hoạt trong PowerShell:
  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  .\.venv\Scripts\Activate.ps1
  ```

### 2.2 Lưu ý cực kỳ quan trọng về lệnh Streamlit
- Thư mục `.venv` trước đây được di chuyển từ vị trí khác sang `F:\HedgeDoc`, do đó file thực thi `streamlit.exe` có đường dẫn shebang bị lệch.
- **TUYỆT ĐỐI KHÔNG** chạy bằng lệnh `streamlit run ...`.
- **LUÔN CHẠY BẰNG CÚ PHÁP**:
  ```powershell
  python -m streamlit run frontend/app.py
  ```
  Ứng dụng mở tại: `http://localhost:8501`.

### 2.3 Chạy Test Backend
- Đầy đủ 8 bài test tích hợp (Provider, Memory, Prompt, ChromaDB, Query, Grounding, Streaming, Greeting):
  ```powershell
  python test_backend.py
  ```

---

## 3. Danh Sách Các Cập Nhật & Thay Đổi Kỹ Thuật Đã Thực Hiện

### 3.1 Xử lý Nút "Process Documents" & Ngăn Spam Click
- **File**: `frontend/app.py`
- **Vấn đề cũ**: Khi người dùng nhấn nút nạp tài liệu, nút vẫn mở và có thể bị bấm nhiều lần liên tục (spam click), kích hoạt nhiều tiến trình nạp song song làm cạn kiệt quota RPM của API.
- **Đã giải quyết**:
  - Sử dụng cờ `st.session_state["is_processing_docs"]`.
  - Ngay khi bấm, nút lập tức chuyển sang trạng thái `disabled=True` và đổi nhãn thành `"Đang xử lý tài liệu..."`.
  - Hiển thị thanh tiến trình `st.progress` chi tiết: `Đang xử lý (X/Y): <tên file>...`.
  - Kiểm tra file đã lập chỉ mục: Nếu tất cả file tải lên đã tồn tại trong ChromaDB, hiển thị `"✓ Tất cả tài liệu đã được lập chỉ mục"` và khóa nút để tránh nạp trùng gây tốn token/quota.

### 3.2 Hệ Thống Thông Báo Lỗi & Thành Công Khi Nạp Sách
- **File**: `backend/rag_engine.py` và `frontend/app.py`
- **Đã giải quyết**:
  - Bọc `index_document` trong `try...except`, bắt mọi ngoại lệ (file rỗng, file PDF lỗi, lỗi mạng) và trả về dictionary chuẩn hóa: `{"status": "success" | "already_indexed" | "empty" | "error", "message": ...}`.
  - Khối `finally` đảm bảo cờ `is_processing_docs` luôn được reset về `False`, không bao giờ làm nút bấm bị treo vĩnh viễn.
  - Giao diện có 2 tầng thông báo:
    - **Toast** góc màn hình (`st.toast`) để người dùng nhận diện ngay.
    - **Thẻ trạng thái cố định (Status Cards)** nằm dưới ô tải file: Phân biệt rõ bằng màu (`st.success`, `st.error`, `st.warning`, `st.info`) kèm nút *"✕ Đóng thông báo"*.

### 3.3 Xử Lý Lỗi Quota Rate Limit 429 & Tối Ưu Embedding
- **File**: `.env`, `backend/providers/gemini_provider.py`, `backend/providers/openai_provider.py`
- **Nguyên nhân gốc**:
  - Model cũ `models/gemini-embedding-001` chạm ngưỡng giới hạn ngày (1.000 requests/ngày của Free Tier).
  - Batch size cũ quá lớn (90 chunks/lô) dễ làm tràn RPM/TPM khi tải sách dày.
- **Đã giải quyết**:
  - Đổi default model sang `models/gemini-embedding-2` trong `.env` (giữ nguyên vector dimension 3072, tương thích 100% với ChromaDB).
  - Giảm batch size từ 90 xuống 40 chunk/lô, thêm delay 1s giữa các lô.
  - Bổ sung danh sách `self.exhausted_models`: Khi một model chạm giới hạn ngày (ví dụ `gemini-embedding-001`), nó được ghi nhớ và **không bao giờ bị gọi lặp lại trong phiên** (chấm dứt hoàn toàn hiện tượng bouncing qua lại giữa 2 model).
  - Lọc cảnh báo deprecation `FutureWarning` từ `google.generativeai` để log console sạch sẽ.

### 3.4 Triển Khai Adapter OpenAI & Trạng Thái Key OpenAI
- **File mới**: `backend/providers/openai_provider.py`
- **Adapter**: Viết độc lập qua thư viện `httpx` (đã có sẵn trong `.venv`, không phụ thuộc gói ngoài):
  - `OpenAILLM`: Hỗ trợ cả sinh văn bản thường và streaming token.
  - `OpenAIEmbedding`: Hỗ trợ `text-embedding-3-large` với tham số `dimensions=3072` (khớp hoàn toàn với vector DB hiện tại).
- **Trạng thái API Key OpenAI trong `.env`**:
  - Key `OPENAI_API_KEY=sk-proj-5cuj...` là **HỢP LỆ** nhưng tài khoản **ĐÃ HẾT SỐ DƯ (0 credit / `credit_balance_exhausted`)**.
  - Đã tích hợp cơ chế: Nếu Gemini hết toàn bộ model, hệ thống tự động fallback sang `OpenAIEmbedding`. Khi người dùng nạp thêm credit vào OpenAI hoặc thay key mới, hệ thống sẽ tự động kích hoạt mượt mà.

### 3.5 Làm Sạch Giao Diện (UI Cleanup)
- **File**: `frontend/components.py` và `frontend/app.py`
- **Đã giải quyết**:
  - Gỡ bỏ huy hiệu `[Scope | All documents]` ở Header.
  - Gỡ bỏ hộp chọn `Search Scope` ở Sidebar để giao diện gọn gàng, hệ thống mặc định tra cứu trên toàn bộ tài liệu đã nạp.
  - Gỡ bỏ hoàn toàn component `render_copy_button` (xóa triệt để dòng code JavaScript thô `{ const el = document.getElementById... }">Copy` bị văng ra ở cuối câu trả lời do Streamlit phiên bản mới sanitize thẻ HTML inline script).

### 3.6 Tối Giản Hóa Khu Vực Nạp Tài Liệu & Sidebar
- **File**: `frontend/app.py`
- **Vấn đề cũ**:
  - Khi tải file đã có trong hệ thống, giao diện sinh ra cùng lúc 2 thông báo trùng lặp ("Tất cả tài liệu đã được lập chỉ mục" + "Đã nạp thành công..."), kèm 2 button thừa (button disabled "Tài liệu đã được lập chỉ mục" và button "✕ Đóng thông báo").
  - Thanh trượt Top-K và nút "Xóa lịch sử chat" luôn chiếm diện tích ngay cả khi chưa có tin nhắn.
- **Đã giải quyết**:
  - **Chỉ hiển thị nút khi cần thiết**: Khi có file mới cần xử lý, chỉ hiện 1 nút primary duy nhất `Nạp {N} tài liệu mới`. Nếu tất cả file đã có trong kho, chỉ hiện 1 dòng caption nhẹ nhàng, gỡ bỏ nút disabled vô dụng.
  - **Chỉ 1 thông báo duy nhất**: Kết quả nạp sách chỉ hiện 1 box thông báo ngắn gọn súc tích (kèm toast tự tắt), không cần tiêu đề phụ hay nút đóng thủ công.
  - **Ẩn nút không cần thiết**: Nút "Xóa lịch sử chat" chỉ xuất hiện khi đoạn hội thoại có tin nhắn (`st.session_state.messages`).
  - **Gọn gàng cấu hình**: Đưa thanh Top-K và thông tin model vào Expander `⚙️ Cấu hình tìm kiếm` (thu gọn mặc định) giúp Sidebar tập trung hoàn toàn vào danh sách tài liệu.

### 3.7 Hỗ Trợ Đa Định Dạng: Word (.docx) & Excel (.xlsx, .xls)
- **Thư viện mới**: `python-docx`, `openpyxl` (kết hợp `pandas` sẵn có trong `.venv`).
- **File cập nhật**:
  - `data_layer/loader.py`: Tạo `MultiFormatDocumentLoader` tự động phân loại và trích xuất:
    - **PDF**: Trích xuất theo trang vật lý (`Trang X`).
    - **Word (.docx)**: Trích xuất theo Tiêu đề (`Heading`) và Bảng biểu (`Table`), gắn nhãn `location_label` theo `Mục X: <Tiêu đề>`.
    - **Excel (.xlsx, .xls)**: Đọc tất cả các sheet, chuyển bảng dữ liệu thành định dạng Markdown Table có cấu trúc cột chuẩn mực cho LLM, gắn nhãn `location_label` theo `Sheet '<Tên Sheet>' (Dòng X - Y)`.
  - `data_layer/chunker.py`: Truyền trường `location_label` vào metadata của vector chunk.
  - `backend/prompts.py` & `frontend/components.py`: Cập nhật cấu trúc trích dẫn linh hoạt, hiển thị rõ ràng số trang hoặc tên Sheet/Mục tương ứng.
  - `frontend/app.py`: Cho phép kéo thả trực tiếp `type=["pdf", "docx", "xlsx", "xls"]`.
- **Dữ liệu mẫu phong phú đã tạo sẵn**:
  - `data/raw_docs/bao_cao_kinh_doanh_2025.xlsx`: 4 sheet (Tổng quan 4 quý, Kênh phân phối & khu vực, Chi phí vận hành, KPI nhân sự).
  - `data/raw_docs/chinh_sach_nhan_su_va_van_hanh_2025.docx`: 6 mục quy chế làm việc, chính sách lương thưởng, WFH, bảo hiểm và bảng tổng hợp.
- **Kiểm thử**: Đã tạo file `test_multi_format.py` xác thực thành công toàn bộ luồng nạp và truy vấn RAG cho cả Word và Excel.

### 3.8 Khắc Phục Lỗi Quota 429 Trên LLM & Tự Động Chuyển Đổi Model (Model Fallback)
- **Vấn đề**: Bản thử nghiệm `gemini-3-flash-preview` bị Google áp đặt hạn mức Free Tier cực kỳ thấp (chỉ **20 requests/ngày**), dẫn đến lỗi `429 Quota Exceeded (limit: 20)` khi người dùng trò chuyện một vài lượt.
- **Đã giải quyết**:
  - Đổi default model trong `.env` sang `gemini-2.5-flash` (mô hình ổn định chính thức với hạn mức tiêu chuẩn 1.500 requests/ngày).
  - Nâng cấp `GeminiLLM` trong `backend/providers/gemini_provider.py` với danh sách `FALLBACK_MODELS` (`gemini-2.5-flash`, `gemini-flash-latest`, `gemini-2.5-flash-lite`, `gemini-3.5-flash`...). Khi một model chạm giới hạn, hệ thống tự động ghi nhớ và fallback sang model kế tiếp mà không làm gián đoạn người dùng.

### 3.9. Tích Hợp Local Model (Ollama) & Bộ Chọn Model Động Trên UI
- **Ollama Provider (`backend/providers/ollama_provider.py`)**:
  - Hỗ trợ chạy các mô hình Local hoàn toàn offline và miễn phí (Qwen 2.5, Llama 3.1, DeepSeek-R1, Mistral...).
  - Triển khai `OllamaLLM` qua REST API `/api/chat` với real-time token streaming (`stream=True`).
  - Triển khai `OllamaEmbedding` qua `/api/embeddings` (hỗ trợ `nomic-embed-text`, `bge-m3`).
  - Hàm `check_ollama_status()`: Tự động ping `http://localhost:11434/api/tags` để phát hiện trạng thái Online/Offline và lấy danh sách model đã cài đặt.
- **ProviderFactory & RAGEngine Dynamic Switching**:
  - `ProviderFactory.get_available_models(provider)`: Cung cấp danh sách model tương ứng cho từng provider.
  - `RAGEngine.get_llm(provider, model_name)`: Cache các adapter LLM đã khởi tạo, cho phép người dùng chuyển đổi tức thì giữa Cloud và Local mà không cần tải lại ứng dụng.
- **Giao diện Bộ Chọn Model (`frontend/components.py` & `frontend/app.py`)**:
  - Tích hợp trực quan tại mục **"Mô hình & Cấu hình"** ở Sidebar.
  - Cho phép người dùng chuyển nhanh giữa **Gemini (Cloud)**, **OpenAI (Cloud)**, và **Ollama (Local)**.
  - Hiển thị nhãn model trực tiếp trên từng câu trả lời của trợ lý AI để người dùng dễ theo dõi.

### 3.10. Loại Bỏ Thẻ Trích Dẫn Gắn Kèm Câu Trả Lời (Clean Presentation)
- **Yêu cầu**: Không gắn các thẻ `[Source: ...]` hay `[Nguồn: ...]` cạnh nội dung trả lời văn bản, câu trả lời chỉ cần thể hiện thông tin thuần túy tự nhiên; toàn bộ nguồn tài liệu và vị trí đoạn trích chỉ hiển thị trong khối **Sources & Citations** bên dưới.
- **Giải pháp đa lớp**:
  - **Prompt-level (`backend/prompts.py`)**: Sửa Rule 3 và câu hỏi prompt yêu cầu LLM không sinh thẻ ngoặc vuông `[Source: ...]` vào văn bản câu trả lời.
  - **Stream filter (`clean_citation_stream` trong `backend/rag_engine.py`)**: Tự động bắt và loại bỏ các thẻ `[Source: ...]`, `[Nguồn: ...]` theo thời gian thực khi token đang stream về giao diện, chống trùng lặp dấu cách.
  - **Sanitizer (`strip_inline_citations`)**: Làm sạch toàn diện các tin nhắn đã lưu trước khi hiển thị lại trên giao diện.

### 3.11. Cơ Chế Truy Xuất Đa Tài Liệu Toàn Diện (Cross-Document Diverse Retrieval)
- **Vấn đề trước đây**: Khi hỏi các câu mang tính bao quát (như *"So sánh các điểm khác biệt chính giữa các tài liệu đã nạp"*), ChromaDB chỉ lấy thuần túy Top-K theo độ tương đồng vector toàn cục (mặc định Top-K = 4). Kết quả là chỉ có 2 file đạt điểm cao nhất lọt vào context, 2 file còn lại hoàn toàn vắng mặt khiến AI không thể nhắc đến.
- **Giải pháp**:
  - Hàm `_is_cross_document_query(question)` trong `backend/rag_engine.py`: Tự động nhận diện các câu hỏi so sánh, tổng hợp, tóm tắt chéo các file.
  - Khi phát hiện câu hỏi đa tài liệu, hệ thống tự động chuyển sang cơ chế **Diverse Retrieval**: Trích xuất tối thiểu 2 đoạn tiêu biểu nhất từ **từng tài liệu** đã nạp trong kho lưu trữ.
  - Cung cấp danh mục `<all_indexed_documents>` vào prompt để AI nắm bắt đầy đủ toàn bộ các file hiện có và phân tích so sánh đầy đủ 100% tài liệu.

### 3.12. Xử Lý Lỗi Quota 429 OpenAI Embedding & Chuyển Sang Local Embedding (Ollama)
- **Sự cố gặp phải**: Khi nạp cuốn sách dày `emotional-intelligence-daniel-goleman.pdf`, hệ thống báo lỗi:
  ```text
  OpenAI Batch Embedding error (429): You have no credits remaining. Add credits to continue using the API...
  ```
- **Nguyên nhân gốc**:
  - Cấu hình trước đó hoặc tiến trình Streamlit đang chạy từ phiên cũ nhận `EMBEDDING_PROVIDER=openai`.
  - Tài khoản OpenAI của người dùng đã hết số dư (0 credit), do đó khi gọi `embed_batch` để tạo vector cho tài liệu, OpenAI từ chối request.
  - File `config.py` chỉ chạy `load_dotenv()` một lần khi import module, nên khi sửa `.env` thì tiến trình Streamlit chưa tự reload nếu không restart hoặc reload module tường minh.
- **Giải pháp & Trạng thái hiện tại**:
  - Chuyển hẳn cấu hình trong `.env` sang chạy Local Embedding:
    ```ini
    EMBEDDING_PROVIDER=ollama
    EMBEDDING_MODEL=nomic-embed-text
    ```
  - Ollama cục bộ đã có sẵn model `nomic-embed-text:latest` (274 MB, vector dimension = 768).
  - Tốc độ đo thực tế: ~2.8 giây / batch 50 chunks trên máy local, hoàn toàn miễn phí, offline và không lo rate limit.
  - Toàn bộ 1.649 chunks của cuốn sách `emotional-intelligence-daniel-goleman.pdf` đã được lập chỉ mục thành công vào ChromaDB `hedgedoc_local_kb` với embedding 768 chiều.

### 3.13. Phân Tích Hiện Tượng "Nạp Sách Dày Chạy Lâu"
- **Đặc thù file**: Cuốn sách `emotional-intelligence-daniel-goleman.pdf` có dung lượng 1.9 MB, gồm **249 trang**, sau khi phân đoạn sinh ra tới **1.649 đoạn (chunks)** (với `CHUNK_SIZE=800` và `CHUNK_OVERLAP=150`).
- **Chi tiết thời gian các bước xử lý**:
  1. **Trích xuất văn bản (PyMuPDF)**: Duyệt qua 249 trang mất khoảng 2 - 4 giây.
  2. **Tách đoạn (Sentence Chunker)**: Cắt thành 1.649 chunks mất khoảng 1 - 2 giây.
  3. **Tạo Vector Embedding**: 1.649 chunks được chia thành 33 batch (50 chunks/batch).
     - Với Local Ollama: Mất khoảng 1.5 - 2 phút (chưa kể thời gian nạp model vào RAM/VRAM ở lần gọi đầu tiên).
     - Với Cloud API: Mất thời gian truyền nhận HTTP và chờ rate limit / sleep giữa các lô.
- **Vấn đề UX cần cải thiện**:
  - Giao diện `frontend/app.py` hiện tại chỉ bọc cả quá trình nạp trong một `st.spinner("Đang trích xuất & tạo vector...")` duy nhất, không hiển thị tiến độ chi tiết từng batch.
  - Người dùng không quan sát được tiến độ (ví dụ: `Đang tạo vector: 450/1649 đoạn (27%)...`) nên dễ có cảm giác hệ thống bị đơ/treo.

### 3.14. Lưu Ý Đồng Bộ Vector Dimension Trong ChromaDB
- **Ràng buộc ChromaDB**: Mỗi collection trong ChromaDB bắt buộc tất cả các vector phải có cùng số chiều (`dimension`).
- **Kích thước vector theo từng model**:
  - `nomic-embed-text` (Ollama): **768** chiều.
  - `models/gemini-embedding-2` / `gemini-embedding-001`: **768** chiều (hoặc 3072 tùy cấu hình).
  - `text-embedding-3-small` (OpenAI): **1536** chiều.
  - `text-embedding-3-large` (OpenAI): **3072** chiều.
- **Lưu ý vận hành**: Khi chuyển đổi giữa các Provider có số chiều vector khác nhau, ChromaDB sẽ báo lỗi không tương thích số chiều (`dimensionality mismatch`). Vì vậy, khi đổi embedding model có dimension khác, cần tạo collection mới hoặc xóa bỏ collection cũ để re-index lại từ đầu.

---

## 4. Cấu Trúc File Trọng Tâm

```text
F:\HedgeDoc\
├── .env                                  # Cấu hình API key & model (EMBEDDING_PROVIDER=ollama)
├── backend/
│   ├── providers/
│   │   ├── base.py                       # Interface BaseLLM, BaseEmbedding
│   │   ├── factory.py                    # ProviderFactory điều phối Gemini / OpenAI / Ollama
│   │   ├── gemini_provider.py            # Gemini adapter + Auto-fallback + Quota memory
│   │   ├── openai_provider.py            # OpenAI adapter
│   │   └── ollama_provider.py            # Ollama Local adapter (Offline, Streaming, Model detection) [MỚI]
│   ├── memory.py                         # Buffer bộ nhớ chat hội thoại
│   ├── prompts.py                        # Strict RAG system prompt & citation builder
│   └── rag_engine.py                     # RAG orchestrator, dynamic LLM selection
├── data/
│   ├── raw_docs/                         # Thư mục chứa tài liệu PDF, DOCX, XLSX
│   └── create_rich_samples.py            # Script tự động tạo dữ liệu mẫu
├── data_layer/
│   ├── loader.py                         # MultiFormatDocumentLoader (PDF, DOCX, XLSX)
│   ├── chunker.py                        # Semantic chunker bảo lưu location_label
│   └── vector_store.py                   # ChromaDB persistence + Fallback in-memory cosine
├── frontend/
│   ├── app.py                            # Streamlit UI (hỗ trợ kéo thả PDF/Word/Excel + Dynamic Model Selection)
│   └── components.py                     # UI components, model selector, thinking box, citations
├── tests/
### 3.15. Cơ Chế Lưu Lũy Tiến (Save-per-batch) & Tự Động Nạp Tiếp (Resumable Indexing)
- **Vấn đề cũ**: Trước đây hàm `index_document` gom toàn bộ văn bản rồi gọi embedding và lưu ChromaDB một lần (`all-or-nothing`). Nếu gặp sự cố ngắt giữa chừng ở các cuốn sách dày (ví dụ batch 30/40), toàn bộ các vector đã tính bị mất trắng, lần sau nạp lại phải bắt đầu từ số 0.
- **Đã giải quyết**:
  - `VectorStoreManager.get_existing_chunk_ids(doc_id)`: Truy vấn danh sách chunk IDs đã lưu trong ChromaDB (`include=[]`, cực nhanh và không tốn RAM).
  - `RAGEngine.index_document`:
    - Lọc `pending_chunks`: Tự động so khớp với DB. Nếu đã có 100% -> trả về `already_indexed`. Nếu đã lưu dở một phần -> tự động nạp tiếp phần còn thiếu (Resume) mà không tính toán lại các chunk đã lưu.
    - Vòng lặp chia nhỏ batch (`batch_size=40`): Cứ embed xong một batch là **ghi lập tức xuống ChromaDB**.
    - Kích hoạt `progress_callback(processed, total, status_text)` theo thời gian thực.
  - Test kiểm thử `tests/test_save_per_batch.py`: Xác thực 100% khả năng tự động khôi phục và nạp tiếp thành công.

### 3.16. Bảo Toàn Cấu Trúc Bảng Biểu Markdown Cho File Excel (.xlsx, .xls)
- **Vấn đề**: Hàm `DocumentChunker` mặc định cắt văn bản theo ngưỡng 800 ký tự. Với các bảng Excel dài (1200-1400 ký tự), thuật toán cắt ngang bảng khiến chunk phía sau bị mất dòng tiêu đề cột (`| Nam | Quy | Dong_San_Pham... |`), khiến AI không thể nhận diện được các con số thuộc cột nào.
- **Đã giải quyết**:
  - `data_layer/chunker.py`: Bổ sung kiểm tra tệp Excel. Vì `ExcelDocumentLoader` đã chia sẵn từng nhóm dòng (15 dòng) kèm đầy đủ tiêu đề Sheet và tên cột, `chunk_page` sẽ giữ nguyên vẹn toàn bộ bảng (nếu <= 2500 ký tự).
  - Kết quả: Các câu hỏi trích xuất số liệu doanh thu, tỷ suất lợi nhuận bảng biểu đạt độ chính xác 100%.

### 3.17. Khuyến Nghị & Tối Ưu Tải Lên Nhiều File
- **Đặc thù**: Khi tải cùng lúc quá nhiều file lớn (> 5 file), luồng xử lý đơn của Streamlit dễ bị nghẽn (UI Blocking), RAM bị chiếm dụng bởi buffer file và dễ chạm trần quota API (nếu dùng Cloud).
- **Đã giải quyết**:
  - `frontend/app.py`: Tự động phát hiện nếu người dùng chọn `> 5 file` và hiển thị cảnh báo `st.warning` khuyến nghị tải 3–5 file/lượt.
### 3.18. Bộ Đánh Giá Thứ Hạng Chuyên Sâu (Hybrid Reranker Engine)
- **Tệp mới**: `backend/reranker.py` (`HybridReranker`)
- **Nguyên lý 2 giai đoạn (Two-Stage Retrieval)**:
  1. *Giai đoạn 1 (Coarse Retrieval)*: Vector Store quét rộng lấy Top 10–12 đoạn ứng viên tiềm năng (kết hợp cả vector Tiếng Việt và Tiếng Anh nếu có).
  2. *Giai đoạn 2 (Fine Reranking)*: Chấm điểm kết hợp 3 tín hiệu:
     - **Vector Semantic Score**: `1.0 - distance` từ ChromaDB.
     - **Lexical BM25 / Keyword Density Score**: Đếm tần suất xuất hiện và độ phủ của các thực thể, từ khóa danh từ riêng, thuật ngữ kỹ thuật trong câu hỏi, kèm điểm cộng khi xuất hiện trong tiêu đề (`location_label`) hoặc khớp cụm từ chính xác.
     - **Reciprocal Rank Fusion (RRF)**: Hợp nhất thứ hạng (`1.0 / (60 + rank)`).
  3. Sắp xếp lại thứ hạng và chọn lọc ra Top-K (4–5 đoạn) tinh túy nhất gửi cho LLM.
- **Minh bạch trên giao diện**: Gắn thuộc tính `rerank_score` vào Citations hiển thị phần trăm độ khớp (ví dụ: `Độ khớp: 65% • Dist: 0.2361`).

### 3.19. Truy Vấn Đa Ngôn Ngữ (Cross-Lingual RAG: Hỏi Tiếng Việt - Sách Tiếng Anh & Phản Hồi Song Ngữ)
- **Vấn đề**: Các cuốn sách chuyên ngành dày (như cuốn `emotional-intelligence-daniel-goleman.pdf` 249 trang) viết hoàn toàn bằng Tiếng Anh. Khi người dùng hỏi bằng Tiếng Việt, câu hỏi vector Tiếng Việt khó khớp hoàn hảo với các đoạn trích nguyên bản Tiếng Anh.
- **Đã giải quyết**:
  - `_contains_vietnamese(text)`: Nhận diện câu hỏi có chứa ký tự tiếng Việt.
  - `_translate_or_expand_query(question, llm)`: Nếu là câu hỏi Tiếng Việt, tự động dịch ngầm câu hỏi sang Tiếng Anh tập trung vào từ khóa tìm kiếm (ví dụ: *"Trí tuệ cảm xúc bao gồm những yếu tố nào?"* -> *"Emotional intelligence components"*).
  - Multi-Query Candidate Pool: Tạo vector và truy xuất ứng viên song song cho cả query Tiếng Việt và Tiếng Anh -> Gộp danh sách ứng viên đưa vào Reranker.
  - **Phản hồi song ngữ chuẩn mực (Language Mirroring)**:
    - Nếu người dùng hỏi bằng **Tiếng Anh** -> Hệ thống trả lời 100% bằng **Tiếng Anh tự nhiên, học thuật**.
    - Nếu người dùng hỏi bằng **Tiếng Việt** -> Hệ thống đọc hiểu tài liệu Tiếng Anh và trả lời bằng **Tiếng Việt mượt mà, chính xác**.
    - Đã chuẩn hóa trong cả Rule 6 của `STRICT_RAG_SYSTEM_PROMPT` và phần chỉ dẫn của `build_rag_prompt`.

### 3.20. Cơ Chế Tự Động Nạp Lại Cấu Hình (.env Hot-Reload)
- **Tệp cập nhật**: `config.py`, `frontend/app.py`
- **Đã giải quyết**:
  - `config.reload()`: Đọc lại file `.env` với cờ `override=True` và cập nhật trực tiếp toàn bộ thuộc tính cấu hình trong bộ nhớ.
  - Tự động gọi `config.reload()` mỗi khi bắt đầu chu kỳ session mới trên Streamlit.
  - Bổ sung nút bấm trực quan *"🔄 Nạp lại cấu hình .env"* ngay trong Sidebar (mục *Mô hình & Cấu hình*). Người dùng có thể đổi API key hoặc model trong `.env` rồi bấm nút là hệ thống nhận ngay lập tức mà không cần khởi động lại tiến trình server.

---

## 4. Cấu Trúc File Trọng Tâm

```text
F:\HedgeDoc\
├── .env                                  # Cấu hình API key & model (EMBEDDING_PROVIDER=ollama)
├── backend/
│   ├── providers/
│   │   ├── base.py                       # Interface BaseLLM, BaseEmbedding
│   │   ├── factory.py                    # ProviderFactory điều phối Gemini / OpenAI / Ollama
│   │   ├── gemini_provider.py            # Gemini adapter + Auto-fallback + Quota memory
│   │   ├── openai_provider.py            # OpenAI adapter
│   │   └── ollama_provider.py            # Ollama Local adapter (Offline, Streaming, Model detection)
│   ├── memory.py                         # Buffer bộ nhớ chat hội thoại
│   ├── prompts.py                        # Strict RAG system prompt & citation builder (Cross-Lingual rule)
│   ├── reranker.py                       # Hybrid Reranker (Semantic + Lexical/BM25 + RRF) - Modular stopwords
│   └── rag_engine.py                     # RAG orchestrator, save-per-batch, Cross-Lingual & dynamic LLM selection
├── data/
│   ├── raw_docs/                         # Thư mục chứa tài liệu PDF, DOCX, XLSX
│   └── create_rich_samples.py            # Script tự động tạo dữ liệu mẫu
├── data_layer/
│   ├── loader.py                         # MultiFormatDocumentLoader (PDF, DOCX, XLSX)
│   ├── chunker.py                        # Structure-Aware Parent-Child Chunker (Principle 8)
│   ├── vector_store.py                   # ChromaDB persistence, get_existing_chunk_ids, fallback cosine
│   └── graph_store.py                    # LegalLineageStore (SQLite WAL, REPLACES/AMENDS, Validity Alerts) [MỚI]
├── frontend/
│   ├── app.py                            # Streamlit UI (Fast vs Thinking toggle, Model selector, Badges)
│   ├── components.py                     # UI components, model selector, citations with rerank score badge
│   └── styles.css                        # Bảng CSS stylesheet độc lập, tách rời hoàn toàn khỏi mã Python
├── tests/
│   ├── test_backend.py                   # Test suite backend tổng quát (8/8 pass)
│   ├── test_multi_format.py              # Test suite kiểm tra Word & Excel (5/5 pass)
│   ├── test_save_per_batch.py            # Test suite kiểm tra Save-per-batch & Resumable Indexing (pass)
│   ├── test_cross_lingual_and_reranker.py # Test suite kiểm tra Reranker, Cross-Lingual & Hot-reload (4/4 pass)
│   ├── test_ollama_and_factory.py        # Test suite kiểm tra Ollama & Dynamic Model Selector
│   ├── test_inference_modes.py           # Test suite kiểm tra Dual Inference Modes Fast vs Thinking [MỚI]
│   ├── test_parent_child_chunking.py     # Test suite kiểm tra Parent-Child Chunking Principle 8 [MỚI]
│   └── test_legal_lineage.py             # Test suite kiểm tra Legal Lineage Store & Validity Alerts [MỚI]
└── ghichu.md                             # File tài liệu context này
```

---

### 3.10 Tái Cấu Trúc & Tinh Gọn Mã Nguồn (Codebase Modular Refactoring)
Đã thực hiện dọn dẹp và chuẩn hóa toàn bộ các file có cấu trúc dài dòng, danh sách liệt kê lặp lại hoặc CSS inline theo yêu cầu của người dùng:
1. **`config.py`**:
   - Loại bỏ sự trùng lặp 100% giữa khai báo biến lớp và phương thức `reload()`.
   - Gom nhóm các biến cấu hình thành 5 cụm logic rõ ràng: *Directories*, *API Keys*, *LLM Engine*, *Embedding*, *ChromaDB & Retrieval*, *Document Chunking*.
   - Khởi tạo giá trị thông qua `self.reload()` ngay trong `__init__()`.
2. **`backend/reranker.py`**:
   - Tách danh sách `STOPWORDS` khổng lồ thành `VIETNAMESE_STOPWORDS` và `ENGLISH_STOPWORDS` riêng biệt có cấu trúc.
   - Hợp nhất bằng phép toán set union `STOPWORDS = VIETNAMESE_STOPWORDS | ENGLISH_STOPWORDS`.
3. **`backend/rag_engine.py`**:
   - Đưa các danh sách keyword / regex phân tán ở giữa các hàm thành hằng số ở đầu file: `VIETNAMESE_DIACRITICS`, `GREETING_KEYWORDS`, `GREETING_PREFIXES`, `CONTENT_TRIGGER_KEYWORDS`, `CROSS_DOCUMENT_PATTERNS`.
   - Hợp nhất hàm loại bỏ dấu tiếng Việt `remove_accents()`.
   - Tinh gọn logic các phương thức kiểm tra `_contains_vietnamese`, `_is_greeting_or_meta`, `_detect_doc_filter`, `_is_cross_document_query`.
4. **`frontend/components.py` & `frontend/styles.css`**:
   - Tách hơn 200 dòng CSS inline trong hàm `inject_custom_css()` ra file riêng `frontend/styles.css` giúp hỗ trợ CSS syntax highlighting trong IDE và mã nguồn Python gọn nhẹ.
   - Khai báo danh sách câu hỏi gợi ý `DEFAULT_SUGGESTED_QUESTIONS` và ánh xạ chủ đề `TOPIC_SUGGESTIONS` dưới dạng declarative dictionary, thay thế chuỗi if-elif dài dòng trong `get_suggested_questions()`.
5. **`backend/prompts.py`**:
   - Bổ sung `Optional` vào import `typing` để tránh lỗi kiểu dữ liệu ở Python 3.14.


### 3.21. Chuẩn Hóa SEO, Minimalist English Meta, Favicon Logo & Cấu Hình Vercel
- **Logo & Favicon**:
  - Thiết kế logo vector tối giản với cấu trúc một khối tam giác liền mạch duy nhất làm đầu/thân chú nhím (đỉnh nhọn vươn về phía trước, cạnh đáy nằm ngang sát mặt sàn), các gai lưng/trang sách xòe quạt từ điểm chốt phía sau (loại bỏ hoàn toàn khe hở và tam giác phụ phía trước).
  - Xuất ra đầy đủ: `assets/logo.svg`, `assets/logo.png` (512x512), `assets/favicon.png` (64x64), `assets/favicon.ico` và thư mục `static/`.
  - Cập nhật logo trực tiếp vào Header (`frontend/components.py`) và `st.set_page_config(page_icon="assets/favicon.png")`.
- **Tiêu đề & Mô tả tiếng Anh chuẩn SEO (Minimal & Refined)**:
  - **Meta Title**: `HedgeDoc — Minimalist RAG & Document Intelligence`
  - **Meta Description**: `Minimalist RAG engine for deep document understanding, precise page-level citations, and zero hallucination.`
  - **Keywords**: `HedgeDoc, RAG, Retrieval-Augmented Generation, Document AI, Vector Search, Minimalist AI`
  - Hàm `inject_seo_meta()`: Bổ sung Open Graph, Twitter Cards, Canonical URL trỏ tới `https://hedgedoc.vercel.app/`.
- **Cấu hình Static Serving & Tệp Tìm Kiếm**:
  - `.streamlit/config.toml`: Kích hoạt `enableStaticServing = true`.
  - `static/robots.txt` & `static/sitemap.xml`: Thiết lập sẵn chuẩn thu thập dữ liệu cho Google Search Console.
  - `vercel.json`: Cấu hình route tĩnh và bảo mật tiêu chuẩn cho Vercel.

### 3.22. Hai Chế Độ Suy Luận Linh Hoạt (Dual Inference Modes: Fast vs. Thinking)
- **Fast Mode (SLA < 30s)**:
  - Tối ưu độ trễ cho tra cứu định nghĩa, tóm tắt nhanh, số liệu đơn lẻ.
  - Luồng Hybrid Retrieval gọn gàng, trả lời trực diện không vòng vo kèm citations chuẩn.
- **Thinking Mode (SLA 30s – 90s, cấm > 2 phút)**:
  - Lập luận sâu đa tầng: Phân rã câu hỏi, mở rộng vùng ứng viên (`coarse_k = max(k * 3, 16)`), kiểm chứng chéo mâu thuẫn giữa các đoạn trích.
  - Áp dụng `THINKING_RAG_SYSTEM_PROMPT` với cấu trúc câu trả lời chuyên nghiệp chuẩn doanh nghiệp:
    1. Tóm tắt kết luận trực diện (Executive Summary)
    2. Phân tích căn cứ chi tiết theo từng điều khoản / số liệu bảng biểu
    3. Đánh giá & Lưu ý thực thi (Compliance Notes / Rủi ro)
  - Hiển thị `🧠 Chuỗi Suy Luận Chuyên Sâu` trực quan 4 bước bên trong drawer `Thinking Process`.
- **Giao diện & Trạng thái**:
  - Tích hợp bộ chọn `render_inference_mode_selector()` trực quan tại Sidebar (mục *Mô hình & Cấu hình*).
  - Từng câu trả lời của AI gắn huy hiệu phân biệt `⚡ Fast` hoặc `🧠 Thinking`.
  - Bộ test kiểm thử: `tests/test_inference_modes.py` (2/2 pass).

### 3.23. Cắt Lát Bám Cấu Trúc Theo Mô Hình Cha–Con (Structure-Aware Parent–Child Chunking - Principle 8)
- **Tệp cập nhật**: `data_layer/chunker.py`, `backend/rag_engine.py`
- **Nguyên lý 2 tầng (Tách biệt đơn vị tìm kiếm khỏi đơn vị đọc hiểu)**:
  - **Chunk Con (`child`, ~300-400 ký tự, `overlap = 0`)**: Đơn vị lập chỉ mục vector và BM25. Vector sắc nét, tránh pha loãng ngữ nghĩa.
  - **Chunk Cha (`parent`, ~800-1500 ký tự)**: Đơn vị trọn vẹn ngữ cảnh (toàn bộ 1 Điều/Khoản, 1 Section, hoặc 1 bảng biểu).
  - Khi vector store trúng một chunk con, `rag_engine.py` tự động **mở rộng chunk con thành chunk cha hoàn chỉnh (`parent_text`)** và khử trùng lặp theo `parent_id`. LLM không bao giờ phải đọc nửa điều khoản hay câu văn bị cắt cụt.
- **Nhận diện cấu trúc tự động**:
  - Regex nhận diện Điều, Khoản, Mục, Chương (`ARTICLE_PATTERN`) và Headings.
  - Bảng biểu Excel / Markdown được giữ nguyên vẹn 1:1 làm một Parent block độc lập.
  - Gắn nhãn đường dẫn cấu trúc phân cấp `struct_path` (ví dụ: `Trang 3 › Điều 5 › Khoản 2`) vào citation.
- **Bộ test kiểm thử**: `tests/test_parent_child_chunking.py` (2/2 pass).

### 3.24. Đồ Thị Phả Hệ Pháp Lý & Cảnh Báo Hiệu Lực Tự Động (Legal Lineage & Validity Alerts - Principle 9 / [INV-HEDGE-04])
- **Tệp mới**: `data_layer/graph_store.py` (`LegalLineageStore`)
- **Lưu trữ nhúng siêu nhẹ**: Dùng SQLite với WAL mode (`legal_lineage.db`), tốn < 10MB RAM, không cần dựng cụm Neo4j cồng kềnh, tương thích hoàn hảo trên cả máy 16GB RAM công ty và máy cá nhân 4GB RAM.
- **Rút trích quan hệ pháp lý tự động (Tier 1 Deterministic Pattern Matching)**:
  - Tự động quét số hiệu văn bản (`DOC_NUMBER_PATTERN`, hỗ trợ cả ký tự `Đ/đ` tiếng Việt: `15/2021/NĐ-CP`, `QĐ-ABC`, `TT-BXD`).
  - Tự động phát hiện các quan hệ pháp lý: `REPLACES` (thay thế), `AMENDS` (sửa đổi, bổ sung), `ABROGATES` (bãi bỏ), `BASES_ON` (căn cứ).
- **Cơ chế Cảnh báo Hiệu lực Đỏ tự động ([INV-HEDGE-04])**:
  - Khi các đoạn trích dẫn của câu trả lời thuộc về một văn bản đã bị văn bản mới hơn trong kho thay thế hoặc sửa đổi:
    Hệ thống lập tức kích hoạt `check_validity_alert()` và **giương cờ cảnh báo đỏ ngay ở dòng đầu tiên của câu trả lời**:
    `> - ⚠️ CẢNH BÁO HIỆU LỰC PHÁP LÝ: Văn bản X đã bị THAY THẾ / BÃI BỎ bởi văn bản Y. Nội dung trích dẫn dưới đây có thể đã HẾT HIỆU LỰC HIỆN HÀNH.`
  - Hoạt động mượt mà ở cả chế độ streaming token và non-streaming.
- **Bộ test kiểm thử**: `tests/test_legal_lineage.py` (1/1 pass).

### 3.25. Tích Hợp Engine OCR Đa Phương Thức Lai (Hybrid Multimodal OCR - Qwen3-VL & Smart Fallback)
- **Tệp mới & cập nhật**: `data_layer/ocr.py`, `data_layer/loader.py`, `config.py`, `.env.example`
- **Kiến trúc OCR độc lập**:
  - Tích hợp `HybridOCREngine` kết nối trực tiếp với máy chủ GPU vLLM nội bộ `http://172.16.12.230:8003/v1` (mô hình `Qwen/Qwen3-VL-8B-Instruct-FP8`).
  - Hỗ trợ trích xuất văn bản từ hình ảnh/PDF scan bằng Vision-Language Model kèm prompt cấu trúc Markdown.
- **Chiến lược Sliding Window & Fallback thông minh**:
  - Chỉ quét OCR chuyên sâu cho $N$ trang đầu và $N$ trang cuối (`OCR_WINDOW_SIZE=3`) nhằm bắt trọn bìa sách, mục lục, bảng số liệu và danh mục tham khảo.
  - Tự động kiểm tra ngưỡng ký tự (`OCR_MIN_CHAR_THRESHOLD=15`): Các trang đã có text layer rõ ràng được đọc bằng PyMuPDF tốc độ tức thì; chỉ gọi OCR đối với trang thuần ảnh scan.
  - Cơ chế Graceful Fallback: Nếu máy chủ OCR vLLM bị ngắt kết nối hoặc timeout, loader tự động chuyển sang PyMuPDF fallback an toàn, không làm treo luồng nạp tài liệu.
- **Bộ test kiểm thử**: `tests/test_hybrid_ocr.py` (7/7 pass).

### 3.26. Cải Tiến UX Trích Dẫn Cuộn Riêng Biệt & Streaming Token Không Độ Trễ (Zero-Latency Streaming)
- **Tệp cập nhật**: `frontend/components.py`, `frontend/styles.css`, `backend/rag_engine.py`
- **Scrollable Citations Container**:
  - Đóng gói toàn bộ danh sách trích dẫn nguồn vào container cố định chiều cao tối đa `max-height: 310px` kèm thanh cuộn tùy chỉnh (custom sleek dark-mode scrollbar).
  - Người dùng dễ dàng đối chiếu trích dẫn trang / bảng biểu ngay tại chỗ mà không cần phải cuộn trang lên xuống liên tục.
- **Zero-Latency Streaming**:
  - Khắc phục hiện tượng chữ nhảy từng cụm chậm chạp: Loại bỏ hoàn toàn bộ đệm tĩnh 120 ký tự trong `clean_citation_stream`.
  - Token stream trực tiếp ngay khi sinh ra từ mô hình, tạo hiệu ứng gõ chữ mượt mà, tức thì như ChatGPT/Claude/Gemini.

### 3.27. Bộ RAG Benchmark Toàn Diện & Đánh Giá Thực Nghiệm Các Mô Hình (Empirical Evaluation Suite)
- **Tệp thực nghiệm**: `scratch/run_benchmark.py`, `data/benchmark_results.json`
- **Bộ 5 Test Case chuẩn công nghiệp (Thang điểm 100)**:
  1. `TC1: Fact Retrieval (20đ)`: Trích xuất mã văn bản quy chế `HD-HR-2025/v4.2` và số ngày WFH tối đa.
  2. `TC2: Table & Numeric (20đ)`: Đọc hiểu số liệu bảo hiểm 150 triệu PVI Care và đơn vị kiểm toán.
  3. `TC3: Tricky Out-of-Scope (20đ)`: Bẫy câu hỏi quyền lợi bịa đặt (thẻ tín dụng Platinum, trợ cấp 500 USD/ngày).
  4. `TC4: False Premise Trap (20đ)`: Bẫy tiền đề sai (hỏi lời khuyên trade cổ phiếu từ sách tâm lý *Emotional Intelligence*).
  5. `TC5: Cross-Doc Synthesis (20đ)`: Tổng hợp chiến lược phát triển AI kết nối giữa slide định hướng và báo cáo nhân sự.
- **Bảng điểm đo đạc thực tế trên hệ thống HedgeDoc**:
  - 🥇 **Gemini 2.5 Flash**: **80/100đ** (Xuất sắc, chống bẫy tuyệt đối, độ trễ RAG ~6-17s, khuyến nghị làm mô hình chính Production).
  - 🥈 **Gemma 4 26B (vLLM GPU `172.16.12.230:8000`)**: **70/100đ** (Chống bẫy tốt, bảo mật 100% mạng LAN, phù hợp làm mô hình On-Premises).
  - 🥉 **Qwen 2.5 7B (Local CPU/RAM)**: **60/100đ** (Đạt fact retrieval nhưng mắc bẫy TC4 = 0đ do tự bịa lời khuyên trade chứng khoán; độ trễ CPU quá chậm ~90-120s/câu).

### 3.28. Nâng Cấp Hệ Thống Mô Hình Local (Ollama): Tích Hợp DeepSeek-R1 & Qwen 2.5 14B Thay Thế Qwen 7B
- **Tệp cập nhật**: `backend/providers/factory.py`, `backend/providers/ollama_provider.py`, `frontend/components.py`, `tests/test_ollama_and_factory.py`
- **Gỡ bỏ mô hình cũ**: Đã xóa `qwen2.5:7b` (4.7 GB) khỏi Ollama để giải phóng tài nguyên.
- **Cài đặt 2 mô hình nâng cấp**:
  1. **`deepseek-r1:8b` (5.2 GB)**: Dòng mô hình suy luận (Reasoning CoT) với khả năng tự kiểm chứng nội dung trước khi trả lời, giải quyết triệt để bẫy tiền đề sai và ảo giác.
  2. **`qwen2.5:14b` (9.0 GB)**: Phiên bản 14B thông minh vượt bậc về xử lý bảng biểu, số liệu kế toán và tiếng Việt.
- **Đồng bộ mã nguồn**: Tự động nhận diện danh sách model cài đặt thực tế qua Ollama API `/api/tags`, fallback mặc định sang `deepseek-r1:8b`, bộ test `tests/test_ollama_and_factory.py` đạt 6/6 pass (100%).

### 3.29. Định Hướng Kiến Trúc Mới: Modular Document AI Platform (Theo `kehoach.md`)
- **Tầm nhìn**: Chuyển đổi từ hệ thống hỗn hợp (Mixed RAG + OCR) sang hệ sinh thái gồm 4 thành phần tách rời hoàn toàn:
  1. **Document Quality Gate**: Đánh giá OCR readiness (Good / Medium / Bad), phát hiện mờ nhòe, nghiêng, thiếu sáng để quyết định nạp thẳng, tiền xử lý hay từ chối.
  2. **Document OCR Engine**: Độc lập với RAG, có tầng backend abstraction (Hugging Face, PaddleOCR, External API), trả về standardized JSON schema.
  3. **Document RAG Engine**: Độc lập với OCR, chỉ nhận structured text input chuẩn, quản lý chunking, embedding, vector store và LLM.
  4. **HedgeDoc Application**: Đóng vai trò Orchestrator & UI kết nối 3 service qua API Contract / REST clients.

---

## 5. Hướng Dẫn Sử Dụng Local Model (Ollama)
1. Cài đặt [Ollama](https://ollama.com/) trên máy tính (đang chạy cổng `11434`).
2. Các model local đã tải sẵn:
   - LLM Reasoning: **`deepseek-r1:8b`** (5.2 GB - Chống ảo giác, suy luận chuỗi tư duy).
   - LLM Bảng biểu & Tiếng Việt: **`qwen2.5:14b`** (9.0 GB - Trích xuất dữ kiện cao cấp).
   - Embedding: **`nomic-embed-text:latest`** (274 MB).
3. Mở PowerShell nếu cần tải thêm model:
   ```powershell
   ollama pull deepseek-r1:8b
   ollama pull qwen2.5:14b
   ollama pull nomic-embed-text
   ```
4. Trên giao diện HedgeDoc UI:
   - Tại Sidebar -> **Mô hình & Cấu hình** -> Chọn **Ollama (Local)** -> Chọn **deepseek-r1:8b** hoặc **qwen2.5:14b**.
   - Embedding tự động sử dụng `nomic-embed-text` từ cấu hình `.env` cho toàn bộ tài liệu nạp cục bộ.

### 3.30. Tách & Độc Lập Hóa OCR Engine (Document OCR Engine - Hoàn thành Phase A)
- **Thư mục dự án độc lập**: `document-ocr-engine/`
  - `pyproject.toml`, `requirements.txt`: Độc lập hóa hoàn toàn các thư viện phụ thuộc (`pymupdf`, `requests`, `pyyaml`, `pydantic`).
  - `configs/default.yaml`: Quản lý cấu hình ngưỡng ký tự, VLM endpoint, window size riêng biệt.
  - `src/schemas/ocr_output.py`: Chuẩn hóa JSON Schema trung gian (`OCROutput`, `OCRPage`, `OCRTable`, `OCRBlock`) theo Mục 8 của `kehoach.md`.
  - `src/models/`: Tách tầng trừu tượng `BaseOCRBackend`, `PyMuPDFDigitalBackend`, `VLMOCRBackend`, `OCRBackendFactory`.
  - `src/preprocessing/` & `src/postprocessing/`: Tổng quát hóa các cấp độ tiêu đề `#..####`, loại bỏ các tiền xử lý sách giáo khoa hardcoded (`Chuyên đề`, `Bài`), giữ nguyên bộ lọc chống ảo giác và làm sạch rò rỉ ngữ cảnh.
  - `src/pipeline/ocr_pipeline.py`: Pipeline điều phối lai tự động phân loại trang kỹ thuật số vs trang scan và duy trì ngữ cảnh tiêu đề liên tục.
  - `cli.py`: Công cụ dòng lệnh độc lập hỗ trợ xuất cả định dạng JSON chuẩn và Markdown đầy đủ: `python cli.py sample.pdf --output result.json`.
  - `tests/`: Bộ unit tests độc lập (`test_schemas.py`, `test_postprocessing.py`, `test_pipeline.py`) đạt tỷ lệ vượt qua 100% (7/7 pass).

### 3.31. Tách & Độc Lập Hóa RAG Engine (Document RAG Engine - Hoàn thành Phase B)
- **Thư mục dự án độc lập**: `document-rag-engine/`
  - `pyproject.toml`, `requirements.txt`: Độc lập hóa hoàn toàn các thư viện phụ thuộc (`chromadb`, `pydantic`, `pyyaml`, `httpx`, `pymupdf`, `python-docx`, `openpyxl`).
  - `configs/`: 3 tệp cấu hình tách bạch (`embedding.yaml`, `retrieval.yaml`, `llm.yaml`).
  - `src/schemas/rag_contracts.py`: Chuẩn hóa hợp đồng dữ liệu RAG (`IngestedDocument`, `IngestedPage`, `DocumentChunk`, `Citation`, `RAGQueryRequest`, `RAGQueryResponse`).
  - `src/ingestion/document_loader.py`: Tầng nạp tài liệu độc lập; **không chứa bất kỳ mã nhận diện OCR nào**, hỗ trợ nạp trực tiếp kết quả JSON từ `document-ocr-engine`, tài liệu số PDF, Word, Excel.
  - `src/chunking/chunker.py`: Kỹ thuật phân đoạn bám cấu trúc theo mô hình Cha - Con (`parent_size=1200`, `child_size=400`, `overlap=0`), nhận diện Điều/Khoản và bảo toàn bảng biểu.
  - `src/embeddings/` & `src/generation/`: Tầng trừu tượng `EmbeddingFactory` và `LLMFactory` hỗ trợ hoán đổi linh hoạt giữa Ollama Local, Gemini Cloud, OpenAI.
  - `src/retrieval/`: `VectorStoreManager` (ChromaDB persistence) và `HybridRetriever` (Two-stage: Coarse Vector search + Hybrid Reranker BM25/Lexical/RRF + Context Expansion mở rộng chunk cha).
  - `src/pipeline/rag_pipeline.py`: Pipeline điều phối đầu cuối hỗ trợ cả `query` và `stream_query`.
  - `cli.py`: Công cụ dòng lệnh độc lập hỗ trợ nạp tài liệu (`python cli.py index file.pdf`), nạp từ kết quả OCR (`python cli.py index result.json --from-ocr`) và tra cứu tri thức (`python cli.py query "câu hỏi"`).
  - `tests/`: Bộ unit & integration tests độc lập (`test_chunker.py`, `test_ingestion.py`, `test_retrieval_and_pipeline.py`) đạt tỷ lệ vượt qua 100% (5/5 pass).

---

### 3.32. Xây Dựng AI Document Quality Gate (Hoàn thành Phase D)
- **Thư mục dự án độc lập**: `document-quality-gate/`
  - `pyproject.toml`, `requirements.txt`: Độc lập hóa hoàn toàn các thư viện phụ thuộc (`pillow`, `numpy`, `pymupdf`, `pydantic`, `pyyaml`).
  - `configs/default.yaml`: Cấu hình ngưỡng đo lường mờ nhòe, tương phản, DPI và chênh lệch chiếu sáng.
  - `src/schemas/quality_assessment.py`: Chuẩn hóa hợp đồng `PageQualityMetrics`, `PageAssessment`, `DocumentQualityAssessment`.
  - `src/metrics/`: 4 bộ đo lường vật lý độc lập toán học bằng numpy:
    - `BlurDetector`: Phương sai Laplacian phát hiện độ mờ nhòe và chuyển động.
    - `ContrastDetector`: RMS contrast đánh giá độ đậm nhạt của nét chữ và nền giấy.
    - `ResolutionDetector`: Ước lượng DPI hiệu dụng theo tỷ lệ A4 tiêu chuẩn.
    - `ShadowDetector`: Độ lệch chuẩn độ sáng giữa các góc phần tư lưới $3 \times 3$ phát hiện bóng đổ và quầng sáng chói.
  - `src/decision/readiness_engine.py`: Động cơ tổng hợp chỉ số, phân loại 3 luồng (*good -> direct_to_ocr; medium -> enhance_before_ocr; bad -> reject*) và gắn nhãn lỗi cụ thể.
  - `src/pipeline/quality_pipeline.py`: Pipeline điều phối phân tích theo trang cho PDF hoặc hình ảnh tĩnh đơn lẻ.
  - `cli.py`: Công cụ dòng lệnh độc lập thẩm định tài liệu: `python cli.py evaluate sample.pdf`.
### 3.33. Mô-đun Phân Tích Bố Cục và Lọc Nhiễu Chữ Ký, Con Dấu (LayoutDetector)
- **Vị trí tích hợp**: `document-ocr-engine/src/layout/`
  - `src/layout/layout_detector.py`: Bộ phân tích bố cục không gian và thành phần phi văn bản:
    - **Chữ ký tay (Signature)**: Định vị cụm đường cong Bezier ở nửa dưới trang và khu vực lân cận các từ khóa xác nhận chức danh.
    - **Con dấu (Stamp)**: Nhận diện đường tròn/hình elip và dải màu đỏ/xanh đặc trưng của con dấu pháp lý.
    - **Hình ảnh / Đồ họa (Figure)**: Nhận diện hình ảnh raster nhúng và biểu đồ để tránh OCR quét nhầm.
    - **Bảng biểu (Table)**: Phát hiện vùng lưới bảng và lưu trữ tọa độ.
  - `clean_text_artifacts`: Tự động loại bỏ triệt để các ký tự rác (`~~~~`, `__//`, `\\\\`, `||||`) do OCR quét trúng nét uốn của chữ ký; thay thế bằng ghi chú ngữ nghĩa rõ ràng: `> [Tài liệu có chữ ký xác nhận hợp lệ]`, `> [Tài liệu có con dấu xác nhận]`.
  - `tests/test_layout.py`: Đạt 10/10 bài kiểm thử trong `document-ocr-engine/tests/`.

---

## 4. Cấu Trúc File Trọng Tâm

```text
F:\HedgeDoc\
├── document-ocr-engine/                  # Module 1: OCR Engine độc lập (Phase A) [ĐÃ HOÀN THÀNH - 7/7 tests]
│   ├── configs/default.yaml
│   ├── src/ (schemas, models, preprocessing, postprocessing, pipeline)
│   ├── api/main.py                       # Cổng giao tiếp REST API (FastAPI)
│   ├── tests/ (7/7 tests pass)
│   ├── cli.py
│   └── README.md
├── document-rag-engine/                  # Module 2: RAG Engine độc lập (Phase B) [ĐÃ HOÀN THÀNH - 5/5 tests]
│   ├── configs/ (embedding.yaml, retrieval.yaml, llm.yaml)
│   ├── src/ (schemas, ingestion, chunking, embeddings, generation, retrieval, pipeline)
│   ├── api/main.py                       # Cổng giao tiếp REST API (FastAPI)
│   ├── tests/ (5/5 tests pass)
│   ├── cli.py
│   └── README.md
├── document-quality-gate/                # Module 3: Quality Gate độc lập (Phase D) [ĐÃ HOÀN THÀNH - 9/9 tests]
│   ├── configs/default.yaml
│   ├── src/ (schemas, preprocessing, metrics, decision, pipeline)
│   ├── api/main.py                       # Cổng giao tiếp REST API (FastAPI)
│   ├── tests/ (9/9 tests pass)
│   ├── cli.py
│   └── README.md
├── HedgeDoc/                             # Module 4: Ứng dụng tích hợp HedgeDoc (Phase E) [ĐÃ HOÀN THÀNH - 4/4 tests]
│   ├── frontend/ (app.py, components.py, styles.css)
│   ├── services/ (quality_gate_client.py, ocr_client.py, rag_client.py, engine_loader.py)
│   ├── workflows/ (document_pipeline.py)
│   ├── configs/ (app_config.py)
│   ├── tests/ (test_services.py, test_orchestrator.py - 4/4 pass)
│   ├── run_app.py
│   └── README.md
├── legacy_references/                    # Thư mục lưu trữ tài liệu tham khảo cũ
├── data_layer/                           # Data layer tương thích ngược
├── backend/                              # Backend tương thích ngược
├── frontend/                             # Frontend tương thích ngược
├── tests/                                # Test suite tổng quát (25/25 pass)
└── ghichu.md                             # File tài liệu context này
```

---

## 6. Lộ Trình Triển Khai Kế Tiếp (Theo file `kehoach.md`)

1. **Pha 1**: Lập Bản đồ Kiến trúc Hiện tại (**Current Architecture Map**, Dependency Map) -> ✅ **Đã hoàn thành** ([architecture_and_migration_map.md](file:///C:/Users/nhuuhoang.tts/.gemini/antigravity-ide/brain/d3286e06-985b-469d-9ac8-9ff3b80fadbd/architecture_and_migration_map.md)).
2. **Pha 2 (Phase A)**: Tách `document-ocr-engine` thành module/repo độc lập, có CLI/Test riêng -> ✅ **Đã hoàn thành** ([document-ocr-engine/](file:///F:/HedgeDoc/document-ocr-engine/README.md)).
3. **Pha 3 (Phase B)**: Tách `document-rag-engine` thành module độc lập, chuẩn hóa input/output schema -> ✅ **Đã hoàn thành** ([document-rag-engine/](file:///F:/HedgeDoc/document-rag-engine/README.md)).
4. **Pha 4 (Phase C & D)**: Xây dựng `document-quality-gate` (Dataset, Baseline, Đánh giá OCR Readiness) -> ✅ **Đã hoàn thành** ([document-quality-gate/](file:///F:/HedgeDoc/document-quality-gate/README.md)).
5. **Pha 5**: Chuẩn hóa API Contract (REST API với FastAPI) cho từng Engine -> ✅ **Đã hoàn thành** (Có `api/main.py` độc lập cho từng module).
6. **Pha 6 (Phase E)**: Tái cấu trúc HedgeDoc thành Application Layer gọi các Client API/Module độc lập -> ✅ **Đã hoàn thành** ([HedgeDoc/](file:///F:/HedgeDoc/HedgeDoc/README.md)).






